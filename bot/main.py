"""EginAI Telegram-боты (aiogram 3). Backend API-дың жұқа клиенті.

    BOT_TOKEN=... API_URL=http://api:8000 PUBLIC_URL=https://... BOT_API_KEY=... python -m bot.main

Командалар: /alerts (ауданымдағы ошақ туралы ескерту), /stop_alerts, /field <алқап>,
/history (соңғы диагноздар + CSV), /clear_history. Ескертулер 5 мин сайын тексеріледі.

BOT_TOKEN болмаса — хабарлама жазып, 0 кодымен шығады (docker compose-та
бот міндетті емес).
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import sys
from html import escape

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (BotCommand, BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove)

from . import stt
from .texts import T, format_alert, format_history, format_reminder, format_result

log = logging.getLogger("eginai.bot")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8000")

BOT_API_KEY = os.environ.get("BOT_API_KEY", "")
POLL_SECONDS = int(os.environ.get("ALERT_POLL_SECONDS", "300"))

# Жадта ғана: тіл, соңғы диагноз, таңдалған алқап, орын не үшін сұралғаны
LANG: dict[int, str] = {}
LAST: dict[int, dict] = {}
FIELD: dict[int, str] = {}
PENDING_LOC: dict[int, tuple[str, float]] = {}   # uid → ("map", 0) | ("alerts", радиус_км)

dp = Dispatcher()
http = httpx.AsyncClient(base_url=API_URL, timeout=30, headers={"X-Bot-Key": BOT_API_KEY})


def lang_of(uid: int, fallback: str | None = None) -> str:
    return LANG.get(uid) or ("ru" if (fallback or "").startswith("ru") else "kk")


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Қазақша", callback_data="lang:kk"),
        InlineKeyboardButton(text="Русский", callback_data="lang:ru")]])


@dp.message(CommandStart())
async def start(m: Message):
    await m.answer(T["kk"]["choose_lang"], reply_markup=lang_kb())


@dp.callback_query(F.data.startswith("lang:"))
async def set_lang(c: CallbackQuery):
    lang = c.data.split(":")[1]
    LANG[c.from_user.id] = lang
    await c.message.edit_text(T[lang]["start"])
    await c.answer()


async def diagnose(m: Message, file_id: str):
    uid = m.from_user.id
    lang = lang_of(uid, m.from_user.language_code)
    t = T[lang]
    wait = await m.answer(t["analyzing"])
    try:
        f = await m.bot.get_file(file_id)
        data = await m.bot.download_file(f.file_path)
        r = await http.post(f"/api/predict?lang={lang}", files={"file": ("photo.jpg", data.read(), "image/jpeg")})
        if r.status_code >= 400:
            msg = r.json().get("detail", {}).get("message") if r.headers.get("content-type", "").startswith("application/json") else None
            await wait.edit_text(msg or t["error"])
            return
        res = r.json()
    except (httpx.HTTPError, OSError) as e:
        log.warning("predict failed: %s", e)
        await wait.edit_text(t["error"])
        return
    await wait.delete()

    main, adv = format_result(res, lang)
    if adv is None:  # өсімдік емес
        await m.answer(main)
        return
    LAST[uid] = {"disease": res["top"][0]["id"], "confidence": res["top"][0]["prob"], "advice": res["advice"]}
    try:  # тарих — қосымша мүмкіндік, қатесі диагнозды бұзбайды
        await http.post("/api/bot/history", json={"chat_id": str(m.chat.id), "disease": LAST[uid]["disease"],
                                                  "confidence": LAST[uid]["confidence"], "field": FIELD.get(uid)})
    except httpx.HTTPError as e:
        log.warning("history save failed: %s", e)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t["more"], callback_data="more")]] + (
        [] if res["unsure"] else [[InlineKeyboardButton(text=t["to_map"], callback_data="map")]]) + (
        [[InlineKeyboardButton(text=t["remind_btn"], callback_data="rem:7")]]
        if BOT_API_KEY and res["advice"]["severity"] != "none" else []))
    if res.get("cam"):
        jpg = base64.b64decode(res["cam"].split(",", 1)[1])
        await m.answer_photo(BufferedInputFile(jpg, "eginai.jpg"), caption=main)
    else:
        await m.answer(main)
    await m.answer(adv, reply_markup=kb)


@dp.message(F.photo)
async def on_photo(m: Message):
    await diagnose(m, m.photo[-1].file_id)


@dp.message(F.document & F.document.mime_type.startswith("image/"))
async def on_image_doc(m: Message):
    await diagnose(m, m.document.file_id)


@dp.callback_query(F.data == "more")
async def more(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    last = LAST.get(c.from_user.id)
    if not last:
        await c.answer(T[lang]["need_diag"], show_alert=True)
        return
    a = last["advice"]
    await c.message.answer(T[lang]["more_text"].format(
        symptoms=escape(a["symptoms"]), prevention=escape(a["prevention"]), similar=escape(a["similar"])))
    await c.answer()


@dp.callback_query(F.data == "map")
async def ask_location(c: CallbackQuery):
    t = T[lang_of(c.from_user.id)]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[
        [KeyboardButton(text=t["send_loc"], request_location=True)], [KeyboardButton(text=t["cancel"])]])
    PENDING_LOC[c.from_user.id] = ("map", 0)
    await c.message.answer(t["consent"], reply_markup=kb)
    await c.answer()


@dp.message(F.location)
async def on_location(m: Message):
    uid = m.from_user.id
    t = T[lang_of(uid)]
    purpose, radius = PENDING_LOC.pop(uid, ("map", 0))
    if purpose == "alerts":
        try:
            r = await http.put("/api/bot/subscriptions", json={
                "chat_id": str(m.chat.id), "lat": m.location.latitude, "lon": m.location.longitude,
                "radius_km": radius, "lang": lang_of(uid)})
            ok = r.status_code == 200
        except httpx.HTTPError:
            ok = False
        await m.answer(t["alerts_on"].format(r=round(radius)) if ok else t["error"], reply_markup=ReplyKeyboardRemove())
        return
    last = LAST.get(uid)
    if not last:
        await m.answer(t["need_diag"], reply_markup=ReplyKeyboardRemove())
        return
    try:
        r = await http.post("/api/cases", json={
            "disease": last["disease"], "confidence": last["confidence"], "lat": m.location.latitude,
            "lon": m.location.longitude, "consent": True, "source": "bot"})
        ok = r.status_code == 201
    except httpx.HTTPError:
        ok = False
    await m.answer(t["added"].format(url=f"{PUBLIC_URL}/#map") if ok else t["error"], reply_markup=ReplyKeyboardRemove())


@dp.callback_query(F.data.startswith("rem:"))
async def set_reminder(c: CallbackQuery):
    uid = c.from_user.id
    lang = lang_of(uid)
    last = LAST.get(uid)
    if not last:
        await c.answer(T[lang]["need_diag"], show_alert=True)
        return
    try:
        r = await http.post("/api/bot/reminders", json={
            "chat_id": str(c.message.chat.id), "disease": last["disease"], "days": int(c.data.split(":")[1]),
            "field": FIELD.get(uid), "lang": lang})
        ok = r.status_code == 201
    except httpx.HTTPError:
        ok = False
    await c.answer(T[lang]["remind_set"] if ok else T[lang]["error"], show_alert=not ok)


@dp.message(Command("alerts"))
async def alerts(m: Message):
    t = T[lang_of(m.from_user.id, m.from_user.language_code)]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"{r} км", callback_data=f"alr:{r}") for r in (10, 30, 50)]])
    await m.answer(t["alerts_intro"], reply_markup=kb)


@dp.callback_query(F.data.startswith("alr:"))
async def alerts_radius(c: CallbackQuery):
    t = T[lang_of(c.from_user.id)]
    PENDING_LOC[c.from_user.id] = ("alerts", float(c.data.split(":")[1]))
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[
        [KeyboardButton(text=t["send_loc"], request_location=True)], [KeyboardButton(text=t["cancel"])]])
    await c.message.answer(t["alerts_loc"], reply_markup=kb)
    await c.answer()


@dp.message(Command("stop_alerts"))
async def stop_alerts(m: Message):
    t = T[lang_of(m.from_user.id, m.from_user.language_code)]
    try:
        r = await http.delete(f"/api/bot/subscriptions/{m.chat.id}")
        ok = r.status_code == 204
    except httpx.HTTPError:
        ok = False
    await m.answer(t["alerts_off"] if ok else t["error"])


@dp.message(Command("field"))
async def set_field(m: Message, command: CommandObject):
    uid = m.from_user.id
    t = T[lang_of(uid, m.from_user.language_code)]
    name = (command.args or "").strip()[:60]
    if name:
        FIELD[uid] = name
        await m.answer(t["field_set"].format(f=escape(name)))
    else:
        await m.answer(t["field_now"].format(f=escape(FIELD[uid])) if uid in FIELD else t["field_off"])


@dp.message(Command("history"))
async def history(m: Message, command: CommandObject):
    lang = lang_of(m.from_user.id, m.from_user.language_code)
    field = (command.args or "").strip() or None
    params = {"lang": lang, **({"field": field} if field else {})}
    try:
        r = await http.get(f"/api/bot/history/{m.chat.id}", params=params)
        r.raise_for_status()
        rows = r.json()
        await m.answer(format_history(rows, lang))
        if rows:
            c = await http.get(f"/api/bot/history/{m.chat.id}.csv", params=params)
            c.raise_for_status()
            await m.answer_document(BufferedInputFile(c.content, "eginai-history.csv"), caption=T[lang]["history_file"])
    except httpx.HTTPError:
        await m.answer(T[lang]["error"])


@dp.message(Command("clear_history"))
async def clear_history(m: Message):
    t = T[lang_of(m.from_user.id, m.from_user.language_code)]
    try:
        ok = (await http.delete(f"/api/bot/history/{m.chat.id}")).status_code == 204
    except httpx.HTTPError:
        ok = False
    await m.answer(t["history_cleared"] if ok else t["error"])


async def alert_loop(bot: Bot) -> None:
    """5 мин сайын: жаңа ошақтар → жазылғандарға; мерзімі жеткен «қайта тексеру» еске салғыштары."""
    while True:
        try:
            r = await http.post("/api/bot/alerts/poll")
            r.raise_for_status()
            for a in r.json():
                try:
                    await bot.send_message(int(a["chat_id"]), format_alert(a))
                except TelegramForbiddenError:  # ботты бұғаттаған — жазылымды өшіреміз
                    await http.delete(f"/api/bot/subscriptions/{a['chat_id']}")
            r = await http.post("/api/bot/reminders/due")
            r.raise_for_status()
            for rem in r.json():
                try:
                    await bot.send_message(int(rem["chat_id"]), format_reminder(rem))
                except TelegramForbiddenError:
                    pass
        except Exception as e:  # цикл ешқашан тоқтамауы керек
            log.warning("alert poll failed: %s", e)
        await asyncio.sleep(POLL_SECONDS)


@dp.message(F.text.in_({T["kk"]["cancel"], T["ru"]["cancel"]}))
async def cancel(m: Message):
    PENDING_LOC.pop(m.from_user.id, None)
    await m.answer(T[lang_of(m.from_user.id)]["cancelled"], reply_markup=ReplyKeyboardRemove())


async def answer_question(m: Message, q: str, lang: str):
    try:
        r = await http.post("/api/ask", json={"question": q[:500], "lang": lang,
                                              "class_id": LAST.get(m.from_user.id, {}).get("disease")})
        r.raise_for_status()
        await m.answer(escape(r.json()["answer"]))
    except httpx.HTTPError:
        await m.answer(T[lang]["error"])


@dp.message(F.voice)
async def on_voice(m: Message):
    """Дауыстық сұрақ → Vosk (kk/ru) → /api/ask."""
    lang = lang_of(m.from_user.id, m.from_user.language_code)
    t = T[lang]
    if not stt.available(lang):
        await m.answer(t["voice_off"])
        return
    if (m.voice.duration or 0) > stt.MAX_SECONDS:
        await m.answer(t["voice_long"])
        return
    f = await m.bot.get_file(m.voice.file_id)
    data = (await m.bot.download_file(f.file_path)).read()
    try:
        q = await asyncio.to_thread(stt.transcribe, data, lang)
    except Exception as e:  # ffmpeg/vosk қатесі — пайдаланушыға түсінікті жауап
        log.warning("stt failed: %s", e)
        q = ""
    if len(q) < 2:
        await m.answer(t["voice_empty"])
        return
    await m.answer(t["voice_heard"].format(q=escape(q)))
    await answer_question(m, q, lang)


@dp.message(F.text)
async def on_text(m: Message):
    """Еркін сұрақ → /api/ask (соңғы диагноз контекст ретінде)."""
    lang = lang_of(m.from_user.id, m.from_user.language_code)
    q = (m.text or "").strip()
    if len(q) < 2:
        await m.answer(T[lang]["ask_hint"])
        return
    await answer_question(m, q, lang)

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    token = os.environ.get("BOT_TOKEN")
    if not token:
        log.warning("BOT_TOKEN not set — Telegram bot disabled (web app still works).")
        sys.exit(0)
    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    if not BOT_API_KEY:
        log.warning("BOT_API_KEY not set — alerts and history are disabled.")
    await bot.set_my_commands([
        BotCommand(command="alerts", description="Ауданымдағы ошақ туралы ескерту / Оповещения"),
        BotCommand(command="field", description="Алқап атауы / Название поля"),
        BotCommand(command="history", description="Диагноз тарихы + CSV / История"),
        BotCommand(command="stop_alerts", description="Ескертуді өшіру / Отключить"),
    ])
    log.info("EginAI bot started, API=%s", API_URL)
    poller = asyncio.create_task(alert_loop(bot)) if BOT_API_KEY else None
    try:
        await dp.start_polling(bot)
    finally:
        if poller:
            poller.cancel()


if __name__ == "__main__":
    asyncio.run(main())
