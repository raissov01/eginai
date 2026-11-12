"""/api/predict және Predictor: дұрыс жауап, қате енгізу, өнімділік."""
from __future__ import annotations

import random
import time

import pytest
from PIL import Image

from conftest import TEST_DATA, jpeg_bytes


def test_corrupted_image_is_422(client, predictor):
    r = client.post("/api/predict", files={"file": ("a.jpg", b"\xff\xd8\xff\xe0broken", "image/jpeg")})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "bad_image"


def test_text_file_is_415(client, predictor):
    r = client.post("/api/predict", files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 415
    body = r.json()["detail"]
    assert body["code"] == "not_image" and body["message"]  # пайдаланушыға түсінікті мәтін


def test_too_large_is_413(client, predictor):
    r = client.post("/api/predict", files={"file": ("a.jpg", b"0" * (10 * 1024 * 1024 + 1), "image/jpeg")})
    assert r.status_code == 413


def test_message_language_follows_lang(client, predictor):
    kk = client.post("/api/predict?lang=kk", files={"file": ("a.txt", b"x", "text/plain")}).json()
    ru = client.post("/api/predict?lang=ru", files={"file": ("a.txt", b"x", "text/plain")}).json()
    assert kk["detail"]["message"] != ru["detail"]["message"]


def test_huge_image_is_fast(client, predictor):
    img = Image.new("RGB", (8000, 6000), (60, 130, 50))
    data = jpeg_bytes(img, quality=70)
    t0 = time.perf_counter()
    r = client.post("/api/predict", files={"file": ("big.jpg", data, "image/jpeg")})
    assert r.status_code == 200
    assert time.perf_counter() - t0 < 5.0


@pytest.mark.parametrize("color", [(128, 128, 128), (20, 40, 200), (250, 250, 250)])
def test_not_a_plant_is_unsure(predictor, color):
    # Сұр қабырға, көк аспан, ақ парақ — модель сенімді диагноз бермеуі керек
    r = predictor.predict(jpeg_bytes(Image.new("RGB", (640, 480), color)))
    assert r.unsure is True


def test_real_test_images_mostly_correct(predictor):
    if not TEST_DATA.exists():
        pytest.skip("data/cls/test жоқ")
    rng = random.Random(0)
    ok = total = 0
    for cls in predictor.labels:
        files = sorted((TEST_DATA / cls).glob("*.jpg"))
        for f in rng.sample(files, min(5, len(files))):
            r = predictor.predict(f.read_bytes(), with_cam=False)
            ok += r.top[0][0] == cls
            total += 1
    assert ok / total >= 0.8


def test_response_shape(client, predictor):
    f = next(TEST_DATA.glob("leaf_rust/*.jpg"))
    r = client.post("/api/predict?lang=ru", files={"file": (f.name, f.read_bytes(), "image/jpeg")})
    assert r.status_code == 200
    j = r.json()
    assert len(j["top"]) == 3
    assert abs(sum(t["prob"] for t in j["top"])) <= 1.0001
    assert j["top"][0]["name"]  # орысша атауы бар
    assert j["cam"].startswith("data:image/jpeg;base64,")
    assert 0 <= j["affected_pct"] <= 100
    assert j["advice"]["title"]
    assert j["ms"] > 0


def test_uniform_green_is_unsure(predictor):
    # Біртұтас жасыл кадр (жабық объектив, жасыл қабырға) — ойдан диагноз қоймау керек
    r = predictor.predict(jpeg_bytes(Image.new("RGB", (640, 480), (40, 130, 40))))
    assert r.unsure and r.reason == "not_plant"


def test_one_pixel_image(client, predictor):
    import io
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), (0, 128, 0)).save(buf, "PNG")
    r = client.post("/api/predict", files={"file": ("a.png", buf.getvalue(), "image/png")})
    assert r.status_code == 200 and r.json()["unsure"] is True
