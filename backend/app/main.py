"""EginAI HTTP API (FastAPI) + веб-қосымшаның статикасы.

Маршруттар:
  POST /api/predict   — фото → диагноз, CAM, кеңес
  POST /api/ask       — еркін сұрақ → білім базасы (+LLM) жауабы
  POST /api/cases     — келісіммен картаға белгілеу
  GET  /api/map       — соңғы N күннің ошақтары (GeoJSON)
  GET  /api/stats     — аурулар бойынша статистика
  GET  /api/classes   — класс тізімі мен атаулары
  GET  /api/health
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from . import advice
from .db import Case, init_db, make_session_factory
from .inference import MAX_BYTES, ImageError, Predictor

log = logging.getLogger("eginai")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

ROOT = Path(__file__).resolve().parent
MODEL_DIR = Path(os.environ.get("EGINAI_MODEL_DIR", ROOT / "model"))
WEB_DIST = Path(os.environ.get("EGINAI_WEB_DIST", ROOT.parents[1] / "web" / "dist"))
Lang = Literal["kk", "ru"]

ERRORS = {
    "not_image": {"kk": "Бұл сурет емес. JPG, PNG немесе WebP фото жіберіңіз.",
                  "ru": "Это не изображение. Отправьте фото в формате JPG, PNG или WebP."},
    "bad_image": {"kk": "Сурет бүлінген, ашылмады. Қайта түсіріп көріңіз.",
                  "ru": "Файл изображения повреждён. Попробуйте сделать снимок заново."},
    "too_large": {"kk": "Файл тым үлкен (ең көбі 10 МБ).",
                  "ru": "Файл слишком большой (максимум 10 МБ)."},
    "db_down": {"kk": "Карта уақытша қолжетімсіз.", "ru": "Карта временно недоступна."},
    "rate": {"kk": "Сұраныс тым көп, бір минуттан кейін қайталаңыз.",
             "ru": "Слишком много запросов, повторите через минуту."},
}
STATUS = {"not_image": 415, "bad_image": 422, "too_large": 413}


def err(code: str, lang: str, status: int) -> HTTPException:
    return HTTPException(status, {"code": code, "message": ERRORS[code].get(lang, ERRORS[code]["ru"])})


class RateLimiter:
    """IP бойынша қарапайым шектеу (бір процесс үшін жеткілікті)."""

    def __init__(self, per_minute: int):
        self.per_minute, self.hits = per_minute, defaultdict(deque)

    def ok(self, key: str) -> bool:
        now, q = time.monotonic(), self.hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True


class CaseIn(BaseModel):
    disease: str
    confidence: float = Field(ge=0, le=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    consent: bool
    source: Literal["web", "bot", "demo"] = "web"


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    lang: Lang = "kk"
    class_id: str | None = None


def create_app() -> FastAPI:
    state: dict = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state["predictor"] = Predictor(MODEL_DIR)
        state["db"] = make_session_factory()
        try:
            init_db(state["db"])
            log.info("database ready")
        except SQLAlchemyError as e:  # база жоқ болса да диагностика жұмыс істейді
            log.warning("database unavailable at start: %s", type(e).__name__)
        log.info("EginAI ready: %d classes", len(state["predictor"].labels))
        yield

    app = FastAPI(title="EginAI", version="1.0.0", lifespan=lifespan,
                  description="Бидай ауруларын фото бойынша анықтау")
    limiter = RateLimiter(int(os.environ.get("EGINAI_RATE_PER_MIN", "60")))

    def client_key(request: Request) -> str:
        return request.client.host if request.client else "?"

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/model-info")
    def model_info():
        """Тест жиынындағы метрикалар (ml/evaluate.py жазады) — «Жоба туралы» беті үшін."""
        f = MODEL_DIR / "metrics.json"
        if not f.exists():
            raise HTTPException(404, {"code": "no_metrics", "message": "metrics.json not found"})
        import json
        m = json.loads(f.read_text(encoding="utf-8"))
        return {k: m[k] for k in ("accuracy", "macro_f1", "n_test", "cpu_ms_per_image_median", "labels")}

    @app.get("/api/classes")
    def classes(lang: Lang = "kk"):
        p: Predictor = state["predictor"]
        return [{"id": c, "name": advice.name(c, lang), "severity": advice.disease(c)["severity"]}
                for c in p.labels]

    @app.post("/api/predict")
    async def predict(request: Request, file: UploadFile = File(...), lang: Lang = "kk"):
        if not limiter.ok(client_key(request)):
            raise err("rate", lang, 429)
        data = await file.read(MAX_BYTES + 1)
        try:
            pred = state["predictor"].predict(data)
        except ImageError as e:
            raise err(e.code, lang, STATUS[e.code]) from None
        top_id = pred.top[0][0]
        return {
            "top": [{"id": c, "name": advice.name(c, lang), "prob": round(p, 4)} for c, p in pred.top],
            "unsure": pred.unsure,
            "reason": pred.reason,
            "cam": f"data:image/jpeg;base64,{pred.cam_jpeg_b64}" if pred.cam_jpeg_b64 else None,
            "affected_pct": pred.affected_pct,
            "advice": None if pred.reason == "not_plant" else advice.advise(top_id, lang),
            "ms": pred.ms,
        }

    @app.post("/api/ask")
    def ask(body: AskIn, request: Request):
        if not limiter.ok(client_key(request)):
            raise err("rate", body.lang, 429)
        return advice.answer(body.question, body.lang, body.class_id)

    @app.post("/api/cases", status_code=201)
    def add_case(body: CaseIn):
        if not body.consent:
            return Response(status_code=204)  # келісім жоқ — ештеңе сақталмайды
        if body.disease not in state["predictor"].labels:
            raise HTTPException(422, {"code": "unknown_disease", "message": body.disease})
        try:
            with state["db"]() as s, s.begin():
                c = Case(disease=body.disease, confidence=round(body.confidence, 3),
                         lat=round(body.lat, 2), lon=round(body.lon, 2), source=body.source)
                s.add(c)
                s.flush()
                return {"id": c.id}
        except SQLAlchemyError:
            raise err("db_down", "ru", 503) from None

    @app.get("/api/map")
    def map_points(days: int = Query(30, ge=1, le=365), disease: str | None = None, lang: Lang = "kk"):
        since = datetime.now(timezone.utc) - timedelta(days=days)
        q = select(Case).where(Case.created_at >= since).order_by(Case.created_at.desc()).limit(5000)
        if disease:
            q = q.where(Case.disease == disease)
        try:
            with state["db"]() as s:
                rows = s.scalars(q).all()
        except SQLAlchemyError:
            raise err("db_down", lang, 503) from None
        return {"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
            "properties": {"disease": r.disease, "name": advice.name(r.disease, lang),
                           "confidence": r.confidence, "date": r.created_at.date().isoformat()},
        } for r in rows]}

    @app.get("/api/stats")
    def stats(days: int = Query(30, ge=1, le=365), lang: Lang = "kk"):
        since = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            with state["db"]() as s:
                rows = s.execute(select(Case.disease, func.count()).where(Case.created_at >= since)
                                 .group_by(Case.disease)).all()
        except SQLAlchemyError:
            raise err("db_down", lang, 503) from None
        return [{"id": d, "name": advice.name(d, lang), "count": n} for d, n in rows]

    # Веб-қосымша (жиналған болса)
    if (WEB_DIST / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            f = (WEB_DIST / path).resolve()
            if path and f.is_file() and WEB_DIST.resolve() in f.parents:
                return FileResponse(f)
            return FileResponse(WEB_DIST / "index.html")

    return app


app = create_app()
