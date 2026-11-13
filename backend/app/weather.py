"""Ауа райы: бүрку терезелері және аурулардың ауа райы бойынша тәуекелі.

Деректер: Open-Meteo Forecast API (кілтсіз, CC BY 4.0; тегін тариф — коммерциялық
емес қолданыс үшін). Сағаттық айнымалылар: температура, салыстырмалы ылғалдылық,
жауын-шашын, 10 м биіктіктегі жел (м/с). Уақыт — алқаптың жергілікті уақыты.

Ережелер — ОРИЕНТИР, агрономның шешімін алмастырмайды:

* Бүрку сағаты жарамды, егер жел 1–4,5 м/с (тынық ауада инверсия, қатты желде
  тамшы ұшып кетеді), температура 8–25 °C, осы сағатта және келесі 3 сағатта
  жаңбыр жоқ. Терезе — қатарынан ≥ 2 жарамды сағат, келесі 72 сағат ішінде.
* «Ылғал сағат» = RH ≥ 90 % (жапырақтағы шықтың жанама белгісі) немесе жауын ≥ 0,2 мм.
  - сары тат: ≥ 6 сағат қатарынан ылғал, 5–15 °C (салқын шықты түндер);
  - қоңыр тат: ≥ 6 сағат қатарынан ылғал, 15–25 °C;
  - масақ қабыршағының септориозы: ≥ 12 сағат қатарынан ылғал, 15–27 °C;
    (тат/септориоз: 0 оқиға — төмен, 1–2 — орташа, ≥ 3 — жоғары)
  - фузариоз: RH ≥ 90 % және 15–30 °C сағаттарының қосындысы (≥ 20 — орташа,
    ≥ 48 — жоғары); тек масақтану–гүлдену кезінде маңызды;
  - ақұнтақ: 15–22 °C, RH ≥ 70 %, жаңбырсыз сағаттар (≥ 15 — орташа, ≥ 40 — жоғары).
  Негізі: Roelfs et al. 1992 (CIMMYT, «Rust diseases of wheat»: шық ұзақтығы
  мен температура), De Wolf et al. 2003 (фузариоз: RH ≥ 90 % ұзақтығы).
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from . import advice

API = "https://api.open-meteo.com/v1/forecast"
VARS = ("temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m")
SOURCE = "Open-Meteo (CC BY 4.0)"
CACHE_S = 30 * 60
_cache: dict[tuple[float, float], tuple[float, dict]] = {}


class WeatherUnavailable(RuntimeError):
    pass


def fetch_hourly(lat: float, lon: float) -> dict:
    """3 күн бұрын + 7 күн алға, сағат сайын. 30 минутқа кэштеледі (~1 км дәлдікпен)."""
    key = (round(lat, 2), round(lon, 2))
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_S:
        return hit[1]
    q = urllib.parse.urlencode({"latitude": key[0], "longitude": key[1], "hourly": ",".join(VARS),
                                "past_days": 3, "forecast_days": 7, "timezone": "auto",
                                "wind_speed_unit": "ms"})
    try:
        with urllib.request.urlopen(f"{API}?{q}", timeout=8) as r:
            j = json.loads(r.read())
        h = j["hourly"]
        h["utc_offset_seconds"] = int(j.get("utc_offset_seconds", 0))
    except Exception as e:  # желі, таймаут, формат — бәрі бір қате
        raise WeatherUnavailable(type(e).__name__) from None
    _cache[key] = (time.monotonic(), h)
    return h


def now_local(offset_s: int = 0) -> datetime:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_s)).replace(tzinfo=None)


def _rows(h: dict) -> list[dict]:
    n = len(h["time"])
    return [{"t": datetime.fromisoformat(h["time"][i]),
             **{v: (h[v][i] if h[v][i] is not None else 0.0) for v in VARS}} for i in range(n)]


# --- Бүрку терезелері -------------------------------------------------------

def _spray_ok(rows: list[dict], i: int) -> bool:
    r = rows[i]
    if not (1.0 <= r["wind_speed_10m"] <= 4.5 and 8.0 <= r["temperature_2m"] <= 25.0):
        return False
    return all(x["precipitation"] < 0.1 for x in rows[i:i + 4])


def spray_windows(h: dict, now: datetime, horizon_h: int = 72, min_len: int = 2) -> list[dict]:
    rows = _rows(h)
    end = now + timedelta(hours=horizon_h)
    start_hour = now.replace(minute=0, second=0, microsecond=0)
    out, run = [], []

    def close():
        if len(run) >= min_len:
            a, b = rows[run[0]]["t"], rows[run[-1]]["t"] + timedelta(hours=1)
            out.append({"start": a.isoformat(timespec="minutes"), "end": b.isoformat(timespec="minutes"),
                        "hours": len(run),
                        "wind_max": round(max(rows[i]["wind_speed_10m"] for i in run), 1),
                        "t_min": round(min(rows[i]["temperature_2m"] for i in run)),
                        "t_max": round(max(rows[i]["temperature_2m"] for i in run))})

    for i, r in enumerate(rows):
        if r["t"] < start_hour or r["t"] + timedelta(hours=1) > end:
            continue
        if _spray_ok(rows, i):
            run.append(i)
        else:
            close()
            run = []
    close()
    return out


# --- Аурулар тәуекелі -------------------------------------------------------

def in_season(h: dict) -> bool:
    """Вегетация: тәуліктік орташа температура кемінде бір күні ≥ 5 °C."""
    t = h["temperature_2m"]
    days = [t[i:i + 24] for i in range(0, len(t), 24)]
    return any(sum(x or 0 for x in d) / len(d) >= 5.0 for d in days if d)


def _wet(r: dict) -> bool:
    return r["relative_humidity_2m"] >= 90 or r["precipitation"] >= 0.2


def _events(rows: list[dict], t_lo: float, t_hi: float, min_hours: int) -> int:
    n = run = 0
    for r in rows + [{"relative_humidity_2m": 0, "precipitation": 0, "temperature_2m": -99}]:
        if _wet(r) and t_lo <= r["temperature_2m"] <= t_hi:
            run += 1
        else:
            n += run >= min_hours
            run = 0
    return n


RULES = {  # id → (тип, параметрлер, орташа шегі, жоғары шегі)
    "stripe_rust": ("events", (5, 15, 6), 1, 3),
    "leaf_rust": ("events", (15, 25, 6), 1, 3),
    "glume_blotch": ("events", (15, 27, 12), 1, 3),
    "fusarium_head_blight": ("humid_hours", (15, 30), 20, 48),
    "powdery_mildew": ("mildew_hours", (15, 22), 15, 40),
}

TEXT = {
    "events": {"kk": "Инфекцияға қолайлы ылғал кезең: {n} рет ({lo}–{hi} °C, ≥ {m} сағ.)",
               "ru": "Благоприятных для заражения влажных периодов: {n} ({lo}–{hi} °C, ≥ {m} ч)"},
    "humid_hours": {"kk": "Ылғалдылық ≥ 90 % және {lo}–{hi} °C: {n} сағат. Масақтану–гүлдену кезінде маңызды",
                    "ru": "Влажность ≥ 90 % при {lo}–{hi} °C: {n} ч. Важно в фазу колошения–цветения"},
    "mildew_hours": {"kk": "Жылы ({lo}–{hi} °C), ылғалды, жаңбырсыз сағаттар: {n}",
                     "ru": "Тёплых ({lo}–{hi} °C) влажных часов без дождя: {n}"},
    "off": {"kk": "Вегетациядан тыс (суық): ауру дамымайды",
            "ru": "Вне вегетации (холодно): болезнь не развивается"},
}


def disease_risk(h: dict, lang: str = "ru") -> list[dict]:
    rows = _rows(h)
    season = in_season(h)
    out = []
    for cid, (kind, p, mid, hi) in RULES.items():
        if not season:
            n, reason = 0, TEXT["off"][lang]
        elif kind == "events":
            n = _events(rows, *p)
            reason = TEXT[kind][lang].format(n=n, lo=p[0], hi=p[1], m=p[2])
        elif kind == "humid_hours":
            n = sum(r["relative_humidity_2m"] >= 90 and p[0] <= r["temperature_2m"] <= p[1] for r in rows)
            reason = TEXT[kind][lang].format(n=n, lo=p[0], hi=p[1])
        else:
            n = sum(p[0] <= r["temperature_2m"] <= p[1] and r["relative_humidity_2m"] >= 70
                    and r["precipitation"] < 0.2 for r in rows)
            reason = TEXT[kind][lang].format(n=n, lo=p[0], hi=p[1])
        level = "high" if n >= hi else "moderate" if n >= mid else "low"
        out.append({"id": cid, "name": advice.name(cid, lang), "level": level, "score": int(n),
                    "reason": reason})
    order = {"high": 0, "moderate": 1, "low": 2}
    return sorted(out, key=lambda r: (order[r["level"]], -r["score"]))


def current(h: dict, now: datetime) -> dict | None:
    """Ағымдағы сағаттың ауа райы (бүрку журналына автоматты жазу үшін)."""
    key = now.replace(minute=0, second=0, microsecond=0).isoformat(timespec="minutes")
    if key not in h["time"]:
        return None
    i = h["time"].index(key)
    return {"time": key, **{v: h[v][i] for v in VARS}}


def report(lat: float, lon: float, lang: str) -> dict:
    h = fetch_hourly(lat, lon)
    now = now_local(h.get("utc_offset_seconds", 0))
    return {"source": SOURCE, "updated": now.isoformat(timespec="minutes"),
            "current": current(h, now), "in_season": in_season(h), "spray_windows": spray_windows(h, now),
            "risk": disease_risk(h, lang)}
