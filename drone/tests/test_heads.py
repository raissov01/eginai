"""Масақ санау модулі: тайлдау, тығыздық формуласы, метрикалар, (бар болса) ONNX модель."""
import math
from pathlib import Path

import numpy as np
import pytest

from drone.heads import MODEL_DIR, heads_per_m2, tiles
from ml.heads_metrics import average_precision, count_errors, iou


def test_small_image_is_single_tile():
    assert tiles(800, 600) == [(0, 0, 800, 600, 0, 0, 800, 600)]


@pytest.mark.parametrize("w,h", [(1024, 1024), (2000, 1500), (5280, 3956)])
def test_tile_own_regions_partition_the_image(w, h):
    ts = tiles(w, h)
    own = np.zeros((h, w), np.int32)
    for x0, y0, x1, y1, cx0, cy0, cx1, cy1 in ts:
        assert x1 - x0 <= 1024 and y1 - y0 <= 1024
        assert x0 <= cx0 < cx1 <= x1 and y0 <= cy0 < cy1 <= y1   # «өз» аймақ тайл ішінде
        own[cy0:cy1, cx0:cx1] += 1
    assert (own == 1).all()                                       # әр пиксель дәл бір тайлға тиесілі


def test_density_formula():
    # 1000×1000 px, 0.2 см/px → 2 м × 2 м = 4 м²; 1200 масақ → 300 /м²
    assert math.isclose(heads_per_m2(1200, 1000, 1000, 0.2), 300.0)


def test_iou_and_ap():
    g = [np.array([[0, 0, 10, 10], [20, 20, 30, 30]], np.float32)]
    assert math.isclose(iou(g[0][:1], g[0][:1])[0, 0], 1.0, rel_tol=1e-6)
    perfect = [(g[0], np.array([0.9, 0.8], np.float32))]
    assert math.isclose(average_precision(perfect, g), 1.0)
    half = [(g[0][:1], np.array([0.9], np.float32))]
    assert math.isclose(average_precision(half, g), 0.5)
    shifted = [(g[0] + 8, np.array([0.9, 0.8], np.float32))]       # IoU < 0.5
    assert average_precision(shifted, g) == 0.0


def test_count_errors():
    e = count_errors([90, 110], [100, 100])
    assert e["mae"] == 10 and math.isclose(e["mean_rel_err_pct"], 10) and e["total_bias_pct"] == 0


@pytest.mark.skipif(not (MODEL_DIR / "heads.onnx").exists(), reason="модель экспортталмаған")
def test_onnx_counter_runs_on_sample():
    from drone.heads import HeadCounter
    sample = Path(__file__).resolve().parents[2] / "samples" / "heads_sample.jpg"
    if not sample.exists():
        pytest.skip("үлгі сурет жоқ")
    r = HeadCounter().count(sample.read_bytes(), gsd_cm=0.05)
    assert r["count"] > 5 and r["heads_m2"] > 0
