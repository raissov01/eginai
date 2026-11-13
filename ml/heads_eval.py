"""Масақ детекторын бағалау (ONNX, CPU — дрон модулінде жұмыс істейтін сол модель).

1. Val бөлігінде санау шегін (score threshold) таңдау → drone/model/heads.json.
2. Тест бөлігі: AP@0.5, AP@0.75, санау қателігі, CPU уақыты.
3. «Биіктік қисығы»: суреттің ажыратымдылығын s есе төмендетіп (GSD өседі),
   метрикалар қалай нашарлайтынын өлшеу → дрон қай биіктікте масақ санай алады.

    python -m ml.heads_eval
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from drone.calc import coverage
from drone.heads import HeadCounter
from ml.heads_metrics import average_precision, count_errors

SCALES = [1.0, 0.5, 0.35, 0.25, 0.18, 0.12, 0.08]
HEAD_WIDTH_CM = 1.2   # бидай масағының орташа ені (болжам, 1.0–1.5 см) — GSD бағалау үшін


def degraded(path: str, s: float) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    if s < 0.999:
        w, h = im.size
        im = im.resize((max(8, round(w * s)), max(8, round(h * s))), Image.LANCZOS).resize((w, h), Image.BILINEAR)
    return np.asarray(im)


def run(hc: HeadCounter, rows: list[dict], s: float) -> tuple[list, list, list]:
    preds, gts, times = [], [], []
    for r in rows:
        a = degraded(r["path"], s)
        t0 = time.perf_counter()
        b, sc = hc._detect(a)
        times.append(time.perf_counter() - t0)
        preds.append((b, sc))
        gts.append(r["boxes"])
    return preds, gts, times


def counts_at(preds, thr: float) -> list[int]:
    return [int((sc >= thr).sum()) for _, sc in preds]


def main() -> None:
    from ml.heads_data import load_rows
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=Path("drone/model"))
    ap.add_argument("--fig", type=Path, default=Path("materials/figures"))
    args = ap.parse_args()
    hc = HeadCounter(args.model, score=0.05)
    val, test = load_rows("val"), load_rows("test")

    # 1. Шекті val-да таңдау (s=1 және s=0.35 орташасы бойынша — ажыратымдылыққа төзімді)
    cands = np.round(np.arange(0.3, 0.86, 0.05), 2)
    vp = {s: run(hc, val, s)[:2] for s in (1.0, 0.35)}
    def val_mae(t):
        return np.mean([count_errors(counts_at(p, t), [len(x) for x in g])["mae"] for p, g in vp.values()])
    thr = float(min(cands, key=val_mae))
    meta_path = args.model / "heads.json"
    meta = json.loads(meta_path.read_text())
    meta["score_threshold"] = thr
    meta_path.write_text(json.dumps(meta, indent=1))

    # 2–3. Тест, әр ажыратымдылықта
    short = np.concatenate([np.minimum(r["boxes"][:, 2] - r["boxes"][:, 0], r["boxes"][:, 3] - r["boxes"][:, 1])
                            for r in test if len(r["boxes"])])
    native_mm = HEAD_WIDTH_CM * 10 / float(np.median(short))   # мм/пиксель (бағалау)
    cm_per_m = coverage(1.0)["gsd_cm"]                          # біздің камера: GSD/биіктік
    curve = []
    for s in SCALES:
        preds, gts, times = run(hc, test, s)
        gsd_cm = native_mm / 10 / s
        row = {"scale": s, "gsd_cm": round(gsd_cm, 3), "altitude_m": round(gsd_cm / cm_per_m, 1),
               "head_px": round(float(np.median(short)) * s, 1),
               "ap50": round(average_precision(preds, gts, 0.5), 4),
               "ap75": round(average_precision(preds, gts, 0.75), 4),
               **{k: round(v, 2) for k, v in count_errors(counts_at(preds, thr), [len(g) for g in gts]).items()},
               "cpu_ms_median": round(1000 * float(np.median(times)), 0)}
        curve.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if s == 1.0:
            best = (preds, gts)

    out = {"n_test_images": len(test), "n_test_heads": int(sum(len(r["boxes"]) for r in test)),
           "score_threshold": thr, "native_gsd_mm_est": round(native_mm, 3),
           "head_width_cm_assumed": HEAD_WIDTH_CM, "median_head_short_side_px": round(float(np.median(short)), 1),
           "camera_gsd_cm_per_m_altitude": round(cm_per_m, 4), "curve": curve}
    Path("ml/heads_metrics.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))

    # Суреттер: биіктік қисығы + мысал детекция
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    args.fig.mkdir(parents=True, exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(7, 3.6), dpi=150)
    xs = [c["gsd_cm"] for c in curve]
    ax1.plot(xs, [c["ap50"] * 100 for c in curve], "o-", color="#2f6b3a", label="AP@0.5, %")
    ax1.plot(xs, [100 - c["mean_rel_err_pct"] for c in curve], "s--", color="#b07a12", label="Санау дәлдігі, %")
    ax1.set_xscale("log")
    ax1.set_xlabel("GSD, см/пиксель (log)")
    ax1.set_ylim(0, 100)
    ax1.grid(alpha=0.3)
    ax1.legend(loc="lower left", frameon=False)
    top = ax1.secondary_xaxis("top", functions=(lambda g: g / cm_per_m, lambda h: h * cm_per_m))
    top.set_xlabel("Дрон биіктігі, м (20 Мп, 24 мм экв.)")
    fig.tight_layout()
    fig.savefig(args.fig / "heads_gsd_curve.png")

    preds, gts = best
    i = int(np.argsort([len(g) for g in gts])[len(gts) // 2])
    im = Image.open(test[i]["path"]).convert("RGB")
    d = ImageDraw.Draw(im)
    b, sc = preds[i]
    for x0, y0, x1, y1 in b[sc >= thr]:
        d.rectangle([x0, y0, x1, y1], outline=(255, 214, 0), width=3)
    d.rectangle([0, 0, 520, 44], fill=(0, 0, 0))
    d.text((10, 8), f"EginAI: {int((sc >= thr).sum())} | gt {len(gts[i])}", fill=(255, 255, 255),
           font_size=28)
    im.save(args.fig / "heads_example.jpg", quality=88)
    Path("samples").mkdir(exist_ok=True)
    Image.open(test[i]["path"]).save("samples/heads_sample.jpg", quality=90)
    print(f"threshold={thr}  native≈{native_mm:.3f} мм/px  → ml/heads_metrics.json")


if __name__ == "__main__":
    main()
