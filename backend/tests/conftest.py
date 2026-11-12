"""Ортақ фикстуралар: нақты ONNX модель және SQLite базасы бар тест клиенті."""
from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "backend" / "app" / "model"
TEST_DATA = ROOT / "data" / "cls" / "test"

# Тесттер Postgres-сіз жүреді: әр сессияға бөлек SQLite файлы
os.environ.setdefault("DATABASE_URL", "sqlite:///" + str(Path(__file__).parent / ".test.db"))
os.environ.pop("ANTHROPIC_API_KEY", None)  # тесттер LLM-сіз, детерминистік


def jpeg_bytes(img: Image.Image, quality: int = 90) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


@pytest.fixture(scope="session")
def predictor():
    if not (MODEL_DIR / "eginai.onnx").exists():
        pytest.skip("модель әлі экспортталмаған (python -m ml.export_onnx)")
    from app.inference import Predictor
    return Predictor(MODEL_DIR)


@pytest.fixture()
def client():
    db = Path(os.environ["DATABASE_URL"].removeprefix("sqlite:///"))
    db.unlink(missing_ok=True)
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app()) as c:
        yield c
    db.unlink(missing_ok=True)
