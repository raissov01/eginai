"""EginAI HTTP API (FastAPI) + веб-қосымшаның статикасы.

Маршруттар:
  POST /api/predict   — 1–3 фото → диагноз, CAM, кеңес
  POST /api/ask       — еркін сұрақ → білім базасы (+LLM) жауабы
  POST /api/cases     — келісіммен картаға белгілеу
  GET  /api/map       — соңғы N күннің ошақтары (GeoJSON)
  GET  /api/stats     — аурулар бойынша статистика
  GET  /api/classes   — класс тізімі мен атаулары
  POST /api/feedback  — «диагноз дұрыс па?» (фотосыз)
  GET  /api/feedback/stats — нақты өрістегі дәлдік
  GET  /api/advice/{id} — бір ауру бойынша кеңес (анықтағыштан)
  GET  /api/symptom-key — офлайн белгілер анықтағышы
  GET  /api/weather   — бүрку терезелері + аурулардың ауа райы тәуекелі (Open-Meteo)
  /api/bot/*          — бот үшін ішкі API (ескерту, тарих), X-Bot-Key
  GET  /api/open/cases(.csv) — ашық деректер: апта × 0,5° ұяшық × ауру
  GET  /api/offline/bundle, /api/offline/model.onnx — интернетсіз режим (браузерде ONNX)
  GET  /api/health
"""
from __future__ import annotations

import csv
import io
import logging
import math
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from . import advice, bot_api, weather
from .db import Case, Feedback, init_db, make_session_factory
from .inference import MAX_BYTES, ImageError, Predictor

log = logging.getLogger("eginai")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

ROOT = Path(__file__).resolve().parent
MODEL_DIR = Path(os.environ.get("EGINAI_MODEL_DIR", ROOT / "model"))
WEB_DIST = Path(os.environ.get("EGINAI_WEB_DIST", ROOT.parents[1] / "web" / "dist"))
Lang = Literal["kk", "ru"]
CELL = 0.5  # ашық деректер торы, градус (~55 × 35 км): жеке алқапты анықтауға болмайды

ERRORS = {
    "not_image": {"kk": "Бұл сурет емес. JPG, PNG немесе WebP фото жіберіңіз.",
                  "ru": "Это не изображение. Отправьте фото в формате JPG, PNG или WebP."},
    "bad_image": {"kk": "Сурет бүлінген, ашылмады. Қайта түсіріп көріңіз.",
                  "ru": "Файл изображения повреждён. Попробуйте сделать снимок заново."},
    "too_large": {"kk": "Файл тым үлкен (ең көбі 10 МБ).",
                  "ru": "Файл слишком большой (максимум 10 МБ)."},
    "db_down": {"kk": "Карта уақытша қолжетімсіз.", "ru": "Карта временно недоступна."},
    "weather_down": {"kk": "Ауа райы қызметі уақытша қолжетімсіз.",
                     "ru": "Сервис погоды временно недоступен."},
    "too_many_files": {"kk": "Ең көбі 3 фото жіберуге болады.", "ru": "Можно отправить не больше 3 фото."},
    "no_file": {"kk": "Фото жіберілмеді.", "ru": "Фото не отправлено."},
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


class FeedbackIn(BaseModel):
    predicted: str
    confidence: float = Field(ge=0, le=1)
    correct: bool
    actual: str | None = None
    source: Literal["web", "bot", "demo"] = "web"

    @model_validator(mode="after")
    def actual_only_when_wrong(self):
        if self.correct and self.actual is not None:
            raise ValueError("actual is only for wrong diagnoses")
        return self


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

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Енгізілген мәнді кері қайтармаймыз: NaN JSON-ға сериализацияланбайды (500 болатын),
        # ал үлкен мәтінді қайта жіберу — артық трафик.
        errs = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", ""), "type": e.get("type", "")} for e in exc.errors()]
        return JSONResponse({"detail": errs}, status_code=422)

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

    @app.get("/api/offline/bundle")
    def offline_bundle():
        """Интернетсіз режимге бәрі бір файлда: кластар, CAM салмақтары, кеңестер, анықтағыш."""
        p: Predictor = state["predictor"]
        return {
            "version": f"{(MODEL_DIR / 'eginai.onnx').stat().st_mtime_ns}",
            "labels": p.labels,
            "classifier_w": p.w.round(5).tolist(),
            "thresholds": {"min_conf": p.min_conf, "min_plant": p.min_plant, "min_texture": p.min_texture},
            "temperature": p.temperature,
            "names": {lg: {c: advice.name(c, lg) for c in p.labels} for lg in ("kk", "ru")},
            "advice": {lg: {c: advice.advise(c, lg) for c in p.labels} for lg in ("kk", "ru")},
            "key": {lg: advice.symptom_key(lg) for lg in ("kk", "ru")},
        }

    @app.get("/api/offline/model.onnx")
    def offline_model():
        return FileResponse(MODEL_DIR / "eginai.onnx", media_type="application/octet-stream",
                            headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/api/classes")
    def classes(lang: Lang = "kk"):
        p: Predictor = state["predictor"]
        return [{"id": c, "name": advice.name(c, lang), "severity": advice.disease(c)["severity"]}
                for c in p.labels]

    @app.post("/api/predict")
    async def predict(request: Request, file: UploadFile | None = File(None),
                      files: list[UploadFile] | None = File(None), lang: Lang = "kk"):
        """Бір фото (`file`) немесе бір өсімдіктің 1–3 фотосы (`files`: жақыннан + жалпы көрініс)."""
        if not limiter.ok(client_key(request)):
            raise err("rate", lang, 429)
        ups = ([file] if file else []) + (files or [])
        if not ups:
            raise err("no_file", lang, 422)
        if len(ups) > 3:
            raise err("too_many_files", lang, 422)
        datas = [await u.read(MAX_BYTES + 1) for u in ups]
        try:
            pred = state["predictor"].predict_many(datas)
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
            "n_images": len(ups), "n_used": pred.n_used,
            "ms": pred.ms,
        }

    @app.get("/api/weather")
    def weather_report(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180),
                       lang: Lang = "kk"):
        try:
            return weather.report(lat, lon, lang)
        except weather.WeatherUnavailable:
            raise err("weather_down", lang, 503) from None

    @app.get("/api/advice/{class_id}")
    def advice_for(class_id: str, lang: Lang = "kk"):
        if class_id not in state["predictor"].labels:
            raise HTTPException(404, {"code": "unknown_disease", "message": class_id})
        return advice.advise(class_id, lang)

    @app.get("/api/symptom-key")
    def symptom_key(lang: Lang = "kk"):
        return advice.symptom_key(lang)

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

    @app.post("/api/feedback", status_code=201)
    def add_feedback(body: FeedbackIn):
        labels = state["predictor"].labels
        if body.predicted not in labels or (body.actual is not None and body.actual not in labels):
            raise HTTPException(422, {"code": "unknown_disease", "message": body.actual or body.predicted})
        try:
            with state["db"]() as s, s.begin():
                f = Feedback(predicted=body.predicted, confidence=round(body.confidence, 3),
                             correct=body.correct, actual=body.actual, source=body.source)
                s.add(f)
                s.flush()
                return {"id": f.id}
        except SQLAlchemyError:
            raise err("db_down", "ru", 503) from None

    @app.get("/api/feedback/stats")
    def feedback_stats(days: int = Query(365, ge=1, le=3650), lang: Lang = "kk"):
        since = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            with state["db"]() as s:
                rows = s.execute(select(Feedback.predicted, Feedback.correct, Feedback.actual)
                                 .where(Feedback.created_at >= since)).all()
        except SQLAlchemyError:
            raise err("db_down", lang, 503) from None
        per: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        conf: dict[tuple[str, str], int] = defaultdict(int)
        for p, ok, actual in rows:
            per[p][0] += 1
            per[p][1] += ok
            if not ok and actual:
                conf[(p, actual)] += 1
        n = len(rows)
        return {
            "n": n, "accuracy": round(sum(v[1] for v in per.values()) / n, 4) if n else None,
            "per_class": sorted(({"id": c, "name": advice.name(c, lang), "n": v[0],
                                  "accuracy": round(v[1] / v[0], 4)} for c, v in per.items()),
                                key=lambda x: -x["n"]),
            "confusions": [{"predicted": p, "actual": a, "n": k}
                           for (p, a), k in sorted(conf.items(), key=lambda x: -x[1])],
        }

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

    def open_rows(days: int, lang: str) -> list[dict]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            with state["db"]() as s:
                rows = s.execute(select(Case.created_at, Case.lat, Case.lon, Case.disease)
                                 .where(Case.created_at >= since)).all()
        except SQLAlchemyError:
            raise err("db_down", lang, 503) from None
        agg: dict[tuple, int] = defaultdict(int)
        for ts, lat, lon, d in rows:
            if advice.disease(d)["severity"] == "none":
                continue
            y, w, _ = ts.isocalendar()
            agg[(f"{y}-W{w:02d}", math.floor(lat / CELL) * CELL, math.floor(lon / CELL) * CELL, d)] += 1
        return [{"week": k[0], "cell_lat": k[1], "cell_lon": k[2], "disease": k[3],
                 "name": advice.name(k[3], lang), "count": n} for k, n in sorted(agg.items())]

    @app.get("/api/open/cases")
    def open_cases(days: int = Query(90, ge=1, le=730), lang: Lang = "kk"):
        """Ашық деректер: апта × 0,5° тор ұяшығы × ауру. Сау жағдайлар кірмейді."""
        return {"license": "CC BY 4.0 (EginAI)", "cell_deg": CELL, "days": days, "rows": open_rows(days, lang)}

    @app.get("/api/open/cases.csv")
    def open_cases_csv(days: int = Query(90, ge=1, le=730), lang: Lang = "kk"):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["week", "cell_lat", "cell_lon", "disease", "name", "count"])
        for r in open_rows(days, lang):
            w.writerow([r["week"], r["cell_lat"], r["cell_lon"], r["disease"], r["name"], r["count"]])
        return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="eginai-open-cases.csv"'})

    app.include_router(bot_api.make_router(state))

    # Веб-қосымша (жиналған болса)
    if (WEB_DIST / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path == "api" or path.startswith("api/"):
                raise HTTPException(404, {"code": "not_found", "message": "Unknown API route"})
            f = (WEB_DIST / path).resolve()
            if path and f.is_file() and WEB_DIST.resolve() in f.parents:
                return FileResponse(f)
            return FileResponse(WEB_DIST / "index.html")

    return app


app = create_app()
