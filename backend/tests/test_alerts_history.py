"""Бот API: аудандағы ошақ туралы ескерту (жазылым → poll) және алқап бойынша диагноз тарихы."""
from __future__ import annotations

import csv
import io

import pytest

from app.bot_api import haversine_km

KEY = {"X-Bot-Key": "test-bot-key"}
ASTANA = (51.17, 71.43)


@pytest.fixture(autouse=True)
def bot_key(monkeypatch):
    monkeypatch.setenv("BOT_API_KEY", "test-bot-key")


def sub(client, chat="100", lat=ASTANA[0], lon=ASTANA[1], radius=30, lang="ru"):
    return client.put("/api/bot/subscriptions", headers=KEY,
                      json={"chat_id": chat, "lat": lat, "lon": lon, "radius_km": radius, "lang": lang})


def case(client, lat, lon, disease="stripe_rust"):
    r = client.post("/api/cases", json={"disease": disease, "confidence": 0.9, "lat": lat, "lon": lon,
                                        "consent": True, "source": "web"})
    assert r.status_code == 201


def poll(client):
    r = client.post("/api/bot/alerts/poll", headers=KEY)
    assert r.status_code == 200
    return {a["chat_id"]: a for a in r.json()}


def test_haversine():
    assert abs(haversine_km(51.17, 71.43, 51.17, 71.43)) < 1e-9
    assert 265 < haversine_km(51.17, 71.43, 53.28, 69.39) < 280      # Астана → Көкшетау, түзу ≈ 273 км


def test_requires_key(client, predictor):
    assert client.post("/api/bot/alerts/poll").status_code == 403
    assert client.post("/api/bot/alerts/poll", headers={"X-Bot-Key": "wrong"}).status_code == 403


def test_disabled_without_configured_key(client, predictor, monkeypatch):
    monkeypatch.delenv("BOT_API_KEY")
    assert client.post("/api/bot/alerts/poll", headers=KEY).status_code == 403


def test_only_new_nearby_disease_cases_are_alerted_once(client, predictor):
    case(client, 51.18, 71.45)                       # жазылымға дейінгі ошақ — хабарланбайды
    assert sub(client).status_code == 200
    assert poll(client) == {}
    case(client, 51.20, 71.50)                       # ~6 км — хабарланады
    case(client, 53.28, 69.39)                       # Көкшетау, ~273 км — радиустан тыс
    case(client, 51.19, 71.44, disease="healthy_leaf")  # сау — ошақ емес
    a = poll(client)
    assert list(a) == ["100"]
    cs = a["100"]["cases"]
    assert len(cs) == 1 and cs[0]["name"] == "Жёлтая (полосатая) ржавчина" and 5 < cs[0]["distance_km"] < 8
    assert a["100"]["lang"] == "ru"
    assert poll(client) == {}                        # екінші рет жіберілмейді


def test_resubscribe_updates_and_unsubscribe_deletes(client, predictor):
    sub(client, radius=10)
    sub(client, radius=50, lang="kk")                # сол чат — жаңарады, екінші жазба емес
    case(client, 51.45, 71.43)                       # ~31 км
    a = poll(client)
    assert a["100"]["lang"] == "kk" and len(a["100"]["cases"]) == 1
    assert client.delete("/api/bot/subscriptions/100", headers=KEY).status_code == 204
    case(client, 51.20, 71.50)
    assert poll(client) == {}


@pytest.mark.parametrize("body", [
    {"chat_id": "1", "lat": 95, "lon": 1, "radius_km": 30},
    {"chat_id": "1", "lat": 51, "lon": 71, "radius_km": 0},
    {"chat_id": "1", "lat": 51, "lon": 71, "radius_km": 500},
    {"chat_id": "", "lat": 51, "lon": 71, "radius_km": 30},
])
def test_subscription_validation(client, predictor, body):
    assert client.put("/api/bot/subscriptions", headers=KEY, json=body).status_code == 422


def test_subscription_coords_are_rounded(client, predictor):
    j = sub(client, lat=51.123456, lon=71.987654).json()
    assert j["lat"] == 51.12 and j["lon"] == 71.99


# --- Тарих ---------------------------------------------------------------------

def add(client, chat="7", disease="leaf_rust", field=None, conf=0.9):
    return client.post("/api/bot/history", headers=KEY,
                       json={"chat_id": chat, "disease": disease, "confidence": conf, "field": field})


def test_history_by_field_and_csv(client, predictor):
    add(client, field="Алқап 3")
    add(client, disease="stripe_rust", field="Алқап 3")
    add(client, disease="healthy_leaf", field="Солтүстік")
    add(client, chat="8")                            # басқа чат көрінбейді
    r = client.get("/api/bot/history/7?lang=ru", headers=KEY)
    rows = r.json()
    assert len(rows) == 3 and rows[0]["name"] == "Здоровый лист"    # жаңасы бірінші
    assert {x["field"] for x in rows} == {"Алқап 3", "Солтүстік"}
    only = client.get("/api/bot/history/7?field=Алқап 3", headers=KEY).json()
    assert len(only) == 2
    c = client.get("/api/bot/history/7.csv?lang=kk", headers=KEY)
    assert c.status_code == 200 and c.headers["content-type"].startswith("text/csv")
    assert c.content.startswith(b"\xef\xbb\xbf")                    # Excel үшін BOM
    table = list(csv.reader(io.StringIO(c.content.decode("utf-8-sig"))))
    assert table[0] == ["date", "field", "disease_id", "disease", "confidence"]
    assert len(table) == 4 and "Қоңыр тат" in {r[3] for r in table}


def test_history_csv_is_formula_safe(client, predictor):
    add(client, field="=HYPERLINK(\"x\")")
    c = client.get("/api/bot/history/7.csv", headers=KEY).content.decode("utf-8-sig")
    assert "'=HYPERLINK" in c


def test_history_validation_and_delete(client, predictor):
    assert add(client, disease="cancer").status_code == 422
    assert add(client, field="x" * 61).status_code == 422
    add(client)
    assert client.delete("/api/bot/history/7", headers=KEY).status_code == 204
    assert client.get("/api/bot/history/7", headers=KEY).json() == []


def test_history_dates_are_local_time():
    from datetime import datetime
    from app.bot_api import _local
    assert _local(datetime(2026, 6, 10, 20, 30)) == "2026-06-11T01:30"   # UTC → Алматы (UTC+5)
