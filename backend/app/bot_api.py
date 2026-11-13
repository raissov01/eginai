"""Telegram-бот үшін ішкі API: аудандағы ошақ туралы ескерту және алқап бойынша тарих.

Барлық маршрут `X-Bot-Key` тақырыбын талап етеді (= BOT_API_KEY ортасы). Кілт
қойылмаса — маршруттар өшірулі (403): chat_id — жеке дерек, ашық болмауы керек.

* Жазылым: chat_id + орын (~1 км-ге дөңгелектенеді) + радиус. Курсор = жазылу
  сәтіндегі соңғы ошақтың id-сі, сондықтан ескі ошақтар хабарланбайды.
* `POST /alerts/poll` — әр жазылымға курсордан кейінгі, радиус ішіндегі ауру
  ошақтарын қайтарып, курсорды жылжытады (бір рет жеткізу; бот 5 мин сайын шақырады).
* Тарих: бот диагнозы (фотосыз) + фермер берген алқап атауы; CSV экспорт.
"""
from __future__ import annotations

import csv
import hmac
import io
import math
import os
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError

from . import advice
from .db import BotDiagnosis, Case, Subscription

Lang = Literal["kk", "ru"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


class SubIn(BaseModel):
    chat_id: str = Field(min_length=1, max_length=32)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_km: float = Field(gt=0, le=200)
    lang: Lang = "kk"


class DiagIn(BaseModel):
    chat_id: str = Field(min_length=1, max_length=32)
    disease: str
    confidence: float = Field(ge=0, le=1)
    field: str | None = Field(default=None, max_length=60)


TZ = ZoneInfo(os.environ.get("EGINAI_TZ", "Asia/Almaty"))


def _local(dt: datetime) -> str:
    """Базадағы уақыт UTC (SQLite-та белдеусіз келеді) → фермердің жергілікті уақыты."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ).isoformat(timespec="minutes")[:16]


def _safe_cell(v: str) -> str:
    """CSV-инъекциядан қорғаныс: Excel формула ретінде оқымасын."""
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def make_router(state: dict) -> APIRouter:
    r = APIRouter(prefix="/api/bot", include_in_schema=False)

    def check(key: str | None):
        want = os.environ.get("BOT_API_KEY", "")
        if not want or not key or not hmac.compare_digest(key, want):
            raise HTTPException(403, {"code": "forbidden", "message": "bot key required"})

    def db():
        return state["db"]()

    def db_down():
        return HTTPException(503, {"code": "db_down", "message": "database unavailable"})

    def labels() -> list[str]:
        return state["predictor"].labels

    @r.put("/subscriptions")
    def subscribe(body: SubIn, x_bot_key: str | None = Header(None)):
        check(x_bot_key)
        try:
            with db() as s, s.begin():
                cursor = s.scalar(select(func.max(Case.id))) or 0
                sub = s.scalar(select(Subscription).where(Subscription.chat_id == body.chat_id))
                if sub is None:
                    sub = Subscription(chat_id=body.chat_id, last_case_id=cursor)
                    s.add(sub)
                sub.lat, sub.lon = round(body.lat, 2), round(body.lon, 2)
                sub.radius_km, sub.lang = body.radius_km, body.lang
                s.flush()
                return {"chat_id": sub.chat_id, "lat": sub.lat, "lon": sub.lon, "radius_km": sub.radius_km}
        except SQLAlchemyError:
            raise db_down() from None

    @r.delete("/subscriptions/{chat_id}", status_code=204)
    def unsubscribe(chat_id: str, x_bot_key: str | None = Header(None)):
        check(x_bot_key)
        try:
            with db() as s, s.begin():
                s.execute(delete(Subscription).where(Subscription.chat_id == chat_id))
        except SQLAlchemyError:
            raise db_down() from None
        return Response(status_code=204)

    @r.post("/alerts/poll")
    def poll(x_bot_key: str | None = Header(None)):
        check(x_bot_key)
        out = []
        try:
            with db() as s, s.begin():
                subs = s.scalars(select(Subscription)).all()
                if not subs:
                    return []
                since = min(x.last_case_id for x in subs)
                cases = s.scalars(select(Case).where(Case.id > since).order_by(Case.id)).all()
                if not cases:
                    return []
                top = cases[-1].id
                for sub in subs:
                    hits = []
                    for c in cases:
                        if c.id <= sub.last_case_id or advice.disease(c.disease)["severity"] == "none":
                            continue
                        d = haversine_km(sub.lat, sub.lon, c.lat, c.lon)
                        if d <= sub.radius_km:
                            hits.append({"disease": c.disease, "name": advice.name(c.disease, sub.lang),
                                         "severity": advice.disease(c.disease)["severity"],
                                         "distance_km": round(d, 1), "date": _local(c.created_at)[:10]})
                    sub.last_case_id = top
                    if hits:
                        out.append({"chat_id": sub.chat_id, "lang": sub.lang, "radius_km": sub.radius_km,
                                    "cases": hits})
        except SQLAlchemyError:
            raise db_down() from None
        return out

    @r.post("/history", status_code=201)
    def add_history(body: DiagIn, x_bot_key: str | None = Header(None)):
        check(x_bot_key)
        if body.disease not in labels():
            raise HTTPException(422, {"code": "unknown_disease", "message": body.disease})
        try:
            with db() as s, s.begin():
                d = BotDiagnosis(chat_id=body.chat_id, disease=body.disease,
                                 confidence=round(body.confidence, 3),
                                 field=(body.field or "").strip() or None)
                s.add(d)
                s.flush()
                return {"id": d.id}
        except SQLAlchemyError:
            raise db_down() from None

    def rows(chat_id: str, field: str | None, lang: str) -> list[dict]:
        q = select(BotDiagnosis).where(BotDiagnosis.chat_id == chat_id)
        if field:
            q = q.where(BotDiagnosis.field == field)
        try:
            with db() as s:
                items = s.scalars(q.order_by(BotDiagnosis.id.desc()).limit(1000)).all()
        except SQLAlchemyError:
            raise db_down() from None
        return [{"date": _local(x.created_at), "field": x.field, "disease": x.disease,
                 "name": advice.name(x.disease, lang), "confidence": x.confidence} for x in items]

    @r.get("/history/{chat_id}.csv")
    def history_csv(chat_id: str, field: str | None = None, lang: Lang = "kk",
                    x_bot_key: str | None = Header(None)):
        check(x_bot_key)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["date", "field", "disease_id", "disease", "confidence"])
        for x in rows(chat_id, field, lang):
            w.writerow([x["date"], _safe_cell(x["field"] or ""), x["disease"], x["name"], x["confidence"]])
        return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="eginai-history.csv"'})

    @r.get("/history/{chat_id}")
    def history(chat_id: str, field: str | None = None, lang: Lang = "kk",
                x_bot_key: str | None = Header(None)):
        check(x_bot_key)
        return rows(chat_id, field, lang)

    @r.get("/fields/{chat_id}")
    def fields(chat_id: str, x_bot_key: str | None = Header(None)):
        check(x_bot_key)
        try:
            with db() as s:
                return [f for f in s.scalars(select(BotDiagnosis.field).where(
                    BotDiagnosis.chat_id == chat_id, BotDiagnosis.field.is_not(None)).distinct()).all()]
        except SQLAlchemyError:
            raise db_down() from None

    @r.delete("/history/{chat_id}", status_code=204)
    def clear_history(chat_id: str, x_bot_key: str | None = Header(None)):
        check(x_bot_key)
        try:
            with db() as s, s.begin():
                s.execute(delete(BotDiagnosis).where(BotDiagnosis.chat_id == chat_id))
        except SQLAlchemyError:
            raise db_down() from None
        return Response(status_code=204)

    return r
