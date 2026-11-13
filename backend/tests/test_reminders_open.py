"""Қайта тексеру еске салғышы (бот) және ашық деректер (апта × тор ұяшығы × ауру)."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

import pytest

KEY = {"X-Bot-Key": "test-bot-key"}


@pytest.fixture(autouse=True)
def bot_key(monkeypatch):
    monkeypatch.setenv("BOT_API_KEY", "test-bot-key")


def remind(client, days=7, chat="9", disease="leaf_rust", field="Алқап 1"):
    return client.post("/api/bot/reminders", headers=KEY,
                       json={"chat_id": chat, "disease": disease, "days": days, "field": field, "lang": "ru"})


def due(client, now=None):
    r = client.post("/api/bot/reminders/due", headers=KEY, params={"now": now.isoformat()} if now else None)
    assert r.status_code == 200
    return r.json()


def test_reminder_fires_once_after_due_date(client, predictor):
    assert remind(client).status_code == 201
    now = datetime.now(timezone.utc)
    assert due(client, now) == []
    d = due(client, now + timedelta(days=7, minutes=1))
    assert len(d) == 1 and d[0]["chat_id"] == "9" and d[0]["name"] == "Бурая (листовая) ржавчина"
    assert d[0]["field"] == "Алқап 1" and d[0]["lang"] == "ru"
    assert due(client, now + timedelta(days=8)) == []


@pytest.mark.parametrize("days", [0, 31])
def test_reminder_days_range(client, predictor, days):
    assert remind(client, days=days).status_code == 422


def test_reminder_unknown_disease(client, predictor):
    assert remind(client, disease="cancer").status_code == 422


def test_reminders_need_key(client, predictor):
    assert client.post("/api/bot/reminders/due").status_code == 403


# --- Ашық деректер ----------------------------------------------------------------

def case(client, lat, lon, disease="stripe_rust"):
    assert client.post("/api/cases", json={"disease": disease, "confidence": 0.9, "lat": lat, "lon": lon,
                                           "consent": True, "source": "web"}).status_code == 201


def test_open_data_aggregates_by_week_cell_disease(client, predictor):
    case(client, 51.18, 71.45)
    case(client, 51.30, 71.40)                           # сол 0,5° ұяшық
    case(client, 51.18, 71.45, disease="leaf_rust")
    case(client, 53.28, 69.39)                           # басқа ұяшық
    case(client, 51.18, 71.45, disease="healthy_leaf")   # сау — ошақ емес, кірмейді
    j = client.get("/api/open/cases?days=30&lang=ru").json()
    rows = {(r["cell_lat"], r["cell_lon"], r["disease"]): r for r in j["rows"]}
    assert rows[(51.0, 71.0, "stripe_rust")]["count"] == 2
    assert rows[(51.0, 71.0, "leaf_rust")]["count"] == 1
    assert rows[(53.0, 69.0, "stripe_rust")]["count"] == 1
    assert all(r["disease"] != "healthy_leaf" for r in j["rows"])
    assert j["cell_deg"] == 0.5 and j["license"].startswith("CC BY")
    assert rows[(51.0, 71.0, "stripe_rust")]["week"].count("-W") == 1


def test_open_data_csv(client, predictor):
    case(client, 51.18, 71.45)
    r = client.get("/api/open/cases.csv?days=30")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    t = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert t[0] == ["week", "cell_lat", "cell_lon", "disease", "name", "count"] and len(t) == 2
