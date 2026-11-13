"""Бір өсімдіктің бірнеше фотосы (жақыннан + жалпы көрініс) → біріктірілген диагноз."""
from __future__ import annotations

import pytest
from PIL import Image

from conftest import TEST_DATA, jpeg_bytes


def imgs(cls: str, n: int) -> list[bytes]:
    fs = sorted((TEST_DATA / cls).glob("*.jpg"))[:n]
    if len(fs) < n:
        pytest.skip("тест суреттері жоқ")
    return [f.read_bytes() for f in fs]


def test_predict_many_averages_probabilities(predictor):
    a, b = imgs("leaf_rust", 2)
    pa, pb = predictor.predict(a, with_cam=False), predictor.predict(b, with_cam=False)
    m = predictor.predict_many([a, b], with_cam=False)
    exp = (pa.probs + pb.probs) / 2
    assert m.top[0][0] == predictor.labels[int(exp.argmax())]
    assert abs(m.top[0][1] - float(exp.max())) < 1e-5
    assert m.n_used == 2


def test_not_plant_photos_are_ignored_in_the_average(predictor):
    a = imgs("stripe_rust", 1)[0]
    wall = jpeg_bytes(Image.new("RGB", (400, 400), (200, 200, 205)))
    one = predictor.predict(a, with_cam=False)
    both = predictor.predict_many([a, wall], with_cam=False)
    assert both.n_used == 1 and both.top == one.top and not both.reason == "not_plant"


def test_all_not_plant_is_not_plant(predictor):
    wall = jpeg_bytes(Image.new("RGB", (400, 400), (200, 200, 205)))
    assert predictor.predict_many([wall, wall], with_cam=False).reason == "not_plant"


def test_api_accepts_up_to_three_files(client, predictor):
    a, b, c = imgs("powdery_mildew", 3)
    files = [("files", (f"{i}.jpg", x, "image/jpeg")) for i, x in enumerate((a, b, c))]
    r = client.post("/api/predict?lang=ru", files=files)
    assert r.status_code == 200
    j = r.json()
    assert j["n_images"] == 3 and j["n_used"] == 3 and j["cam"]


def test_api_rejects_four_files(client, predictor):
    a = imgs("powdery_mildew", 1)[0]
    files = [("files", (f"{i}.jpg", a, "image/jpeg")) for i in range(4)]
    r = client.post("/api/predict", files=files)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "too_many_files"


def test_api_requires_a_file(client, predictor):
    assert client.post("/api/predict").status_code == 422


def test_single_file_field_still_works(client, predictor):
    a = imgs("leaf_rust", 1)[0]
    r = client.post("/api/predict", files={"file": ("a.jpg", a, "image/jpeg")})
    assert r.status_code == 200 and r.json()["n_images"] == 1


def test_one_bad_file_fails_the_request(client, predictor):
    a = imgs("leaf_rust", 1)[0]
    files = [("files", ("a.jpg", a, "image/jpeg")), ("files", ("b.txt", b"hello", "text/plain"))]
    r = client.post("/api/predict", files=files)
    assert r.status_code == 415
