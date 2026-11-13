"""Ауа райы модулі: бүрку терезелері, аурулар тәуекелі (таза функциялар) және /api/weather."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app import weather as w

T0 = datetime(2026, 6, 10, 0, 0)


def hours(n: int, **const) -> dict:
    """n сағаттық жасанды болжам; барлық айнымалылар тұрақты (const-пен өзгертіледі)."""
    base = {"temperature_2m": 18.0, "relative_humidity_2m": 60.0, "precipitation": 0.0,
            "wind_speed_10m": 3.0}
    base.update(const)
    return {"time": [(T0 + timedelta(hours=i)).isoformat(timespec="minutes") for i in range(n)],
            **{k: [v] * n for k, v in base.items()}}


def setv(h: dict, key: str, idx, value) -> dict:
    for i in idx:
        h[key][i] = value
    return h


# --- Бүрку терезелері -------------------------------------------------------

def test_good_weather_is_one_long_window():
    wins = w.spray_windows(hours(72), now=T0)
    assert len(wins) == 1 and wins[0]["hours"] >= 60


def test_strong_wind_and_rain_split_windows():
    h = hours(24)
    setv(h, "wind_speed_10m", range(8, 12), 7.0)        # 08–11 қатты жел
    setv(h, "precipitation", [18], 2.0)                 # 18:00 жаңбыр → 15–18 жарамсыз (3 сағ құрғақ керек)
    wins = w.spray_windows(h, now=T0)
    spans = [(x["start"][11:16], x["end"][11:16]) for x in wins]
    assert spans[0] == ("00:00", "08:00")
    assert spans[1][0] == "12:00" and spans[1][1] <= "15:00"
    assert all(not (s <= "18:00" < e) for s, e in spans)


def test_calm_air_is_not_a_window():
    # <1 м/с — температуралық инверсия қаупі, тамшылар ұшып кетеді
    assert w.spray_windows(hours(24, wind_speed_10m=0.5), now=T0) == []


def test_cold_or_hot_is_not_a_window():
    assert w.spray_windows(hours(24, temperature_2m=3.0), now=T0) == []
    assert w.spray_windows(hours(24, temperature_2m=31.0), now=T0) == []


def test_short_gaps_are_not_windows():
    h = hours(24, wind_speed_10m=7.0)
    setv(h, "wind_speed_10m", [5], 3.0)                 # бір ғана жақсы сағат
    assert w.spray_windows(h, now=T0) == []


def test_only_next_72_hours_after_now():
    wins = w.spray_windows(hours(24 * 7), now=T0 + timedelta(hours=10))
    assert wins[0]["start"] >= (T0 + timedelta(hours=10)).isoformat(timespec="minutes")
    assert wins[-1]["end"] <= (T0 + timedelta(hours=10 + 72)).isoformat(timespec="minutes")


# --- Аурулар тәуекелі -------------------------------------------------------

def level(h: dict, disease: str) -> str:
    return {r["id"]: r for r in w.disease_risk(h, lang="ru")}[disease]["level"]


def test_dry_warm_week_is_low_risk_for_rusts_and_fhb():
    h = hours(24 * 7, relative_humidity_2m=45.0)
    for d in ("leaf_rust", "stripe_rust", "fusarium_head_blight", "glume_blotch"):
        assert level(h, d) == "low"


def test_cool_dew_nights_raise_stripe_rust():
    h = hours(24 * 7)
    for day in range(7):                                # әр түн 22:00–05:00: шық, 10 °C
        idx = [day * 24 + i for i in range(22, 30) if day * 24 + i < 24 * 7]
        setv(h, "relative_humidity_2m", idx, 96.0)
        setv(h, "temperature_2m", idx, 10.0)
    assert level(h, "stripe_rust") == "high"
    assert level(h, "leaf_rust") == "low"               # 10 °C қоңыр тат үшін салқын


def test_warm_wet_nights_raise_leaf_rust():
    h = hours(24 * 7)
    for day in range(3):
        idx = [day * 24 + i for i in range(0, 8)]
        setv(h, "relative_humidity_2m", idx, 95.0)
        setv(h, "temperature_2m", idx, 19.0)
    assert level(h, "leaf_rust") in ("moderate", "high")


def test_long_humid_period_raises_fhb():
    h = hours(24 * 7, relative_humidity_2m=93.0, temperature_2m=22.0)
    assert level(h, "fusarium_head_blight") == "high"


def test_healthy_classes_have_no_risk_entry_and_reasons_are_localized():
    rs = w.disease_risk(hours(24 * 7), lang="kk")
    ids = {r["id"] for r in rs}
    assert "healthy_leaf" not in ids and "leaf_rust" in ids
    assert all(r["reason"] and r["name"] for r in rs)


def test_winter_is_out_of_season():
    h = hours(24 * 7, temperature_2m=-5.0, relative_humidity_2m=95.0)
    assert w.in_season(h) is False
    assert all(r["level"] == "low" for r in w.disease_risk(h, lang="ru"))


# --- API ---------------------------------------------------------------------

def test_weather_endpoint(client, monkeypatch):
    monkeypatch.setattr(w, "fetch_hourly", lambda lat, lon: hours(24 * 10))
    monkeypatch.setattr(w, "now_local", lambda offset_s=0: T0 + timedelta(hours=3 * 24))
    r = client.get("/api/weather?lat=51.2&lon=71.4&lang=kk")
    assert r.status_code == 200
    j = r.json()
    assert j["in_season"] is True and j["spray_windows"] and len(j["risk"]) == 5
    assert "Open-Meteo" in j["source"]


def test_weather_endpoint_upstream_down(client, monkeypatch):
    def boom(lat, lon):
        raise w.WeatherUnavailable("x")
    monkeypatch.setattr(w, "fetch_hourly", boom)
    r = client.get("/api/weather?lat=51.2&lon=71.4&lang=ru")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "weather_down"


@pytest.mark.parametrize("q", ["lat=91&lon=0", "lat=0&lon=200", "lat=abc&lon=1", "lon=1"])
def test_weather_endpoint_validates_coords(client, q):
    assert client.get(f"/api/weather?{q}").status_code == 422
