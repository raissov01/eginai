"""EginAI дрон модулінің есептері (2-кезең тұжырымдамасы).

Барлық сан — болжамды мысал үшін; параметрлерді нақты шаруашылық
деректерімен ауыстыруға болады. Формулалар:

* Камера қамту ауданы: W = 2·h·tan(FOVh/2), H = 2·h·tan(FOVv/2);
  GSD = W / кадр ені (пиксель).
* Маршрут («ары-бері»): жолақтар арасы = W·(1 − бүйірлік қабаттасу);
  уақыт = аудан / (жолақ арасы · жылдамдық) + бұрылыстар қоры.
* Өнімділік: Y (г/м²) = масақ/м² × дән/масақ × МДМ/1000; 1 г/м² = 0,1 ц/га.
* Шығын = ошақ ауданы × өнімділік × шығын үлесі.
* Нүктелік шашырату = ошақ ауданы × (1 + буфер).

Биіктіктер өлшеммен таңдалған (2026-11-14):
* Масақ санау: детектор (GWHD-да үйретілген, ml/heads_metrics.json) GSD ≤ ~0,1 см/пиксельде
  қатесі ~6–8 %, 0,16 см-де 18 %, 0,24 см-де 43 %. Біздің камерамен бұл ≤ ~3–4 м биіктік,
  сондықтан 25 м-ден масақ саналмайды: ошақтарда дрон нүктелерде 3 м-ге түсіп түсіреді (іріктеме).
* Жапырақ ауруы: классификаторға зақым аймағы кадрда ~200 px керек (ml/cls_resolution.json),
  бұл дрон камерасының мүмкіндігінен тыс — диагнозды агроном GPS нүктесінде телефонмен қояды.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# 4/3" 20 Мп RGB камера, 24 мм эквивалент (ауыл шаруашылығы дрондарының кең таралған түрі)
FOV_H_DEG, FOV_V_DEG, IMG_W_PX = 73.7, 53.1, 5280


def coverage(altitude_m: float) -> dict:
    w = 2 * altitude_m * math.tan(math.radians(FOV_H_DEG / 2))
    h = 2 * altitude_m * math.tan(math.radians(FOV_V_DEG / 2))
    return {"footprint_w_m": w, "footprint_h_m": h, "gsd_cm": w / IMG_W_PX * 100}


def flight_plan(area_ha: float, altitude_m: float, side_overlap: float = 0.7,
                speed_ms: float | None = None, turn_reserve: float = 0.2,
                battery_min: float = 40) -> dict:
    """«Ары-бері» маршрутының уақыты мен ұшу саны."""
    c = coverage(altitude_m)
    spacing = c["footprint_w_m"] * (1 - side_overlap)
    speed = speed_ms or (10 if altitude_m >= 60 else 5)  # төменде кадр бұлдырамауы үшін баяу
    hours = area_ha * 10_000 / (spacing * speed) / 3600 * (1 + turn_reserve)
    return {**c, "line_spacing_m": spacing, "speed_ms": speed, "hours": hours,
            "flights": math.ceil(hours * 60 / battery_min)}


HEAD_ALT_M = 3.0        # масақ санау биіктігі (GSD ≈ 0,085 см/пиксель)
SAMPLES_PER_HA = 2      # ошақтағы іріктеме нүктелері, га сайын
SEC_PER_SAMPLE = 25     # түсу + ілініп тұру + түсіру + көтерілу + келесі нүктеге ұшу


def sampling_plan(area_ha: float) -> dict:
    """Ошақтарда масақ санау: толық жабу емес, нүктелік іріктеме (3 м биіктік)."""
    n = math.ceil(area_ha * SAMPLES_PER_HA)
    return {"samples": n, "hours": n * SEC_PER_SAMPLE / 3600, "gsd_cm": coverage(HEAD_ALT_M)["gsd_cm"]}


def yield_cph(heads_m2: float, grains_per_head: float, tkw_g: float) -> float:
    """Өнімділік, ц/га."""
    return heads_m2 * grains_per_head * tkw_g / 1000 * 0.1


@dataclass
class FieldScenario:
    area_ha: float = 500            # алқап ауданы
    heads_m2: float = 300           # масақ санау нәтижесі (дрон, 25 м)
    grains_per_head: float = 22
    tkw_g: float = 32               # мың дәннің массасы
    hotspot_share: float = 0.06     # ошақ үлесі (шолу ұшуынан)
    loss_share: float = 0.15        # өңделмесе ошақтағы шығын үлесі (қоңыр тат, ауыр жағдай)
    buffer: float = 0.5             # шашырату буфері
    price_tg_t: float = 90_000      # бидай бағасы, ₸/т (болжам)
    fungicide_tg_ha: float = 10_000 # препарат + жұмыс, ₸/га (болжам)


def report(s: FieldScenario) -> dict:
    y = yield_cph(s.heads_m2, s.grains_per_head, s.tkw_g)
    hot = s.area_ha * s.hotspot_share
    loss_t = hot * y / 10 * s.loss_share
    spray = hot * (1 + s.buffer)
    survey = flight_plan(s.area_ha, 100)
    detail = sampling_plan(hot)
    return {
        "yield_cph": y, "harvest_t": s.area_ha * y / 10, "hotspot_ha": hot,
        "loss_t": loss_t, "loss_tg": loss_t * s.price_tg_t,
        "spray_ha": spray, "spray_tg": spray * s.fungicide_tg_ha,
        "full_spray_tg": s.area_ha * s.fungicide_tg_ha,
        "saving_tg": (s.area_ha - spray) * s.fungicide_tg_ha,
        "saving_pct": (s.area_ha - spray) / s.area_ha * 100,
        "survey_hours": survey["hours"], "survey_flights": survey["flights"], "survey_gsd_cm": survey["gsd_cm"],
        "detail_hours": detail["hours"], "detail_samples": detail["samples"], "detail_gsd_cm": detail["gsd_cm"],
    }


if __name__ == "__main__":
    import json
    print(json.dumps({k: round(v, 2) for k, v in report(FieldScenario()).items()}, indent=1, ensure_ascii=False))
