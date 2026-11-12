"""Картаға белгілеу: келісім, валидация, дөңгелектеу, база құлағандағы мінез."""
from fastapi.testclient import TestClient


def case(**kw):
    base = {"disease": "leaf_rust", "confidence": 0.91, "lat": 51.18345, "lon": 71.44678,
            "consent": True, "source": "web"}
    base.update(kw)
    return base


def test_no_consent_stores_nothing(client, predictor):
    assert client.post("/api/cases", json=case(consent=False)).status_code == 204
    assert client.get("/api/map").json()["features"] == []


def test_case_is_stored_with_rounded_coords(client, predictor):
    assert client.post("/api/cases", json=case()).status_code == 201
    f = client.get("/api/map?lang=ru").json()["features"]
    assert len(f) == 1
    assert f[0]["geometry"]["coordinates"] == [71.45, 51.18]
    assert f[0]["properties"]["name"] == "Бурая (листовая) ржавчина"


def test_invalid_lat_is_422(client, predictor):
    assert client.post("/api/cases", json=case(lat=123)).status_code == 422


def test_unknown_disease_is_422(client, predictor):
    assert client.post("/api/cases", json=case(disease="cancer")).status_code == 422


def test_map_filter_and_stats(client, predictor):
    client.post("/api/cases", json=case())
    client.post("/api/cases", json=case(disease="stripe_rust"))
    assert len(client.get("/api/map?disease=stripe_rust").json()["features"]) == 1
    stats = {s["id"]: s["count"] for s in client.get("/api/stats").json()}
    assert stats == {"leaf_rust": 1, "stripe_rust": 1}


def test_db_down_map_503_but_predict_works(monkeypatch, predictor):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x:x@127.0.0.1:1/x")
    from app.main import create_app
    from conftest import TEST_DATA
    with TestClient(create_app()) as c:
        r = c.get("/api/map")
        assert r.status_code == 503 and r.json()["detail"]["message"]
        f = next(TEST_DATA.glob("powdery_mildew/*.jpg"))
        assert c.post("/api/predict", files={"file": (f.name, f.read_bytes(), "image/jpeg")}).status_code == 200


def test_ask_endpoint(client, predictor):
    r = client.post("/api/ask", json={"question": "ақ ұнтақ жапырақта", "lang": "kk"})
    assert r.status_code == 200 and r.json()["context"][0]["class_id"] == "powdery_mildew"
    assert client.post("/api/ask", json={"question": "", "lang": "kk"}).status_code == 422


def test_nan_is_422_not_500(client, predictor):
    r = client.post("/api/cases", content=b'{"disease":"leaf_rust","confidence":NaN,"lat":1,"lon":1,"consent":true}',
                    headers={"content-type": "application/json"})
    assert r.status_code == 422
    assert "input" not in r.text  # енгізілген мән кері қайтарылмайды
