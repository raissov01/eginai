"""EginAI Telegram-боты (aiogram 3). Backend API-дың жұқа клиенті.

    BOT_TOKEN=... API_URL=http://api:8000 PUBLIC_URL=https://... python -m bot.main

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
from aiogram.filters import CommandStart
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove)

from .texts import T, format_result

log = logging.getLogger("eginai.bot")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8000")

# Жадта ғана: пайдаланушы тілі және соңғы диагноз (базаға жазылмайды)
LANG: dict[int, str] = {}
LAST: dict[int, dict] = {}

dp = Dispatcher()
http = httpx.AsyncClient(base_url=API_URL, timeout=30)


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
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t["more"], callback_data="more")]] + (
        [] if res["unsure"] else [[InlineKeyboardButton(text=t["to_map"], callback_data="map")]]))
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
    await c.message.answer(t["consent"], reply_markup=kb)
    await c.answer()


@dp.message(F.location)
async def on_location(m: Message):
    uid = m.from_user.id
    t = T[lang_of(uid)]
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


@dp.message(F.text.in_({T["kk"]["cancel"], T["ru"]["cancel"]}))
async def cancel(m: Message):
    await m.answer(T[lang_of(m.from_user.id)]["cancelled"], reply_markup=ReplyKeyboardRemove())


@dp.message(F.text)
async def on_text(m: Message):
    """Еркін сұрақ → /api/ask (соңғы диагноз контекст ретінде)."""
    uid = m.from_user.id
    lang = lang_of(uid, m.from_user.language_code)
    q = (m.text or "").strip()[:500]
    if len(q) < 2:
        await m.answer(T[lang]["ask_hint"])
        return
    try:
        r = await http.post("/api/ask", json={"question": q, "lang": lang,
                                              "class_id": LAST.get(uid, {}).get("disease")})
        r.raise_for_status()
        await m.answer(escape(r.json()["answer"]))
    except httpx.HTTPError:
        await m.answer(T[lang]["error"])


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    token = os.environ.get("BOT_TOKEN")
    if not token:
        log.warning("BOT_TOKEN not set — Telegram bot disabled (web app still works).")
        sys.exit(0)
    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    log.info("EginAI bot started, API=%s", API_URL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
