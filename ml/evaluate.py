"""Тест бөлігінде ONNX модельді бағалау → ml/metrics.json + confusion matrix.

Бағалау API-дағы дәл сол препроцессинг пен ONNX моделімен жүреді, яғни
жюриге көрсетілетін сандар нақты жұмыс істейтін жүйенікі.

    python -m ml.evaluate --data data/cls/test
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.inference import Predictor  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/cls/test"))
    ap.add_argument("--model", type=Path, default=Path("backend/app/model"))
    ap.add_argument("--fig", type=Path, default=Path("materials/figures/confusion.png"))
    args = ap.parse_args()
    pred = Predictor(args.model)
    labels = pred.labels
    ys, ps, times = [], [], []
    for ci, cls in enumerate(labels):
        for f in sorted((args.data / cls).glob("*.jpg")):
            t0 = time.perf_counter()
            r = pred.predict(f.read_bytes(), with_cam=False)
            times.append(time.perf_counter() - t0)
            ys.append(ci)
            ps.append(labels.index(r.top[0][0]))
    rep = classification_report(ys, ps, target_names=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(ys, ps, labels=list(range(len(labels))))
    metrics = {
        "n_test": len(ys), "accuracy": round(rep["accuracy"], 4),
        "macro_f1": round(rep["macro avg"]["f1-score"], 4),
        "per_class": {c: {k: round(rep[c][k], 4) for k in ("precision", "recall", "f1-score", "support")}
                      for c in labels},
        "cpu_ms_per_image_median": round(1000 * float(np.median(times)), 1),
        "confusion": cm.tolist(), "labels": labels,
    }
    out = json.dumps(metrics, indent=1, ensure_ascii=False)
    Path("ml/metrics.json").write_text(out)
    (args.model / "metrics.json").write_text(out)  # API «Жоба туралы» беті үшін
    print(json.dumps({k: metrics[k] for k in ("n_test", "accuracy", "macro_f1", "cpu_ms_per_image_median")}))
    print(classification_report(ys, ps, target_names=labels, zero_division=0))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    args.fig.parent.mkdir(parents=True, exist_ok=True)
    norm = cm / cm.sum(1, keepdims=True).clip(min=1)
    fig, ax = plt.subplots(figsize=(7, 6), dpi=160)
    ax.imshow(norm, cmap="Greens", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=40, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if norm[i, j] > 0.5 else "black", fontsize=8)
    ax.set_xlabel("Предсказано")
    ax.set_ylabel("Истинный класс")
    ax.set_title(f"EginAI — тест: accuracy {metrics['accuracy']:.3f}, macro-F1 {metrics['macro_f1']:.3f}")
    fig.tight_layout()
    fig.savefig(args.fig)
    print("→", args.fig)


if __name__ == "__main__":
    main()
