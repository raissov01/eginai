"""Дрон модулінің есептерін тексеру: формулалар қолмен есептелген мәндерге сәйкес."""
import math

from drone.calc import FieldScenario, coverage, flight_plan, report, yield_cph


def test_yield_formula():
    # 300 масақ/м² × 22 дән × 32 г/1000 = 211.2 г/м² = 21.12 ц/га
    assert math.isclose(yield_cph(300, 22, 32), 21.12, rel_tol=1e-9)


def test_footprint_and_gsd_at_100m():
    c = coverage(altitude_m=100)
    assert 140 < c["footprint_w_m"] < 160          # ~150 м
    assert 2.5 < c["gsd_cm"] < 3.1                  # ~2.8 см/пиксель


def test_low_altitude_is_finer_but_slower():
    hi, lo = flight_plan(100, 100), flight_plan(100, 25)
    assert lo["gsd_cm"] < hi["gsd_cm"]
    assert lo["hours"] > hi["hours"] * 3


def test_report_500ha_example():
    r = report(FieldScenario())
    assert math.isclose(r["yield_cph"], 21.12, rel_tol=1e-6)
    assert math.isclose(r["harvest_t"], 1056.0, rel_tol=1e-6)          # 500 га × 2.112 т
    assert math.isclose(r["hotspot_ha"], 30.0, rel_tol=1e-6)           # 6 %
    assert math.isclose(r["loss_t"], 30 * 2.112 * 0.15, rel_tol=1e-6)  # ≈ 9.5 т
    assert r["spray_ha"] == 45.0                                       # ошақ + 50 % буфер
    assert math.isclose(r["saving_pct"], (500 - 45) / 500 * 100, rel_tol=1e-6)


def test_no_disease_means_no_loss_and_full_saving():
    r = report(FieldScenario(hotspot_share=0.0))
    assert r["loss_t"] == 0 and r["spray_ha"] == 0 and r["saving_pct"] == 100
