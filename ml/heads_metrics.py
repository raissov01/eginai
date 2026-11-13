"""Детектор метрикалары (тәуелділіксіз, numpy): AP@IoU және санау қателігі."""
from __future__ import annotations

import numpy as np


def iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a [N,4], b [M,4] (xyxy) → [N,M]."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)), np.float32)
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area = lambda r: (r[:, 2] - r[:, 0]) * (r[:, 3] - r[:, 1])  # noqa: E731
    return inter / (area(a)[:, None] + area(b)[None, :] - inter + 1e-9)


def average_precision(preds: list[tuple[np.ndarray, np.ndarray]], gts: list[np.ndarray],
                      thr: float = 0.5) -> float:
    """Бір класты AP (VOC, барлық нүктелік интерполяция). preds: [(boxes, scores)]."""
    recs, n_gt = [], sum(len(g) for g in gts)
    for (pb, ps), g in zip(preds, gts):
        order = np.argsort(-ps)
        pb, ps = pb[order], ps[order]
        used = np.zeros(len(g), bool)
        m = iou(pb, g)
        for k in range(len(pb)):
            tp = 0
            if len(g):
                j = int(np.argmax(np.where(used, -1, m[k])))
                if not used[j] and m[k, j] >= thr:
                    used[j], tp = True, 1
            recs.append((ps[k], tp))
    if n_gt == 0:
        return float("nan")
    recs.sort(key=lambda t: -t[0])
    tp = np.cumsum([t for _, t in recs])
    fp = np.cumsum([1 - t for _, t in recs])
    rec = tp / n_gt
    prec = tp / np.maximum(tp + fp, 1e-9)
    mrec = np.concatenate([[0], rec, [1]])
    mpre = np.concatenate([[0], prec, [0]])
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))


def count_errors(pred_counts: list[int], gt_counts: list[int]) -> dict:
    p, g = np.asarray(pred_counts, float), np.asarray(gt_counts, float)
    mask = g > 0
    return {
        "mae": float(np.mean(np.abs(p - g))),
        "rmse": float(np.sqrt(np.mean((p - g) ** 2))),
        "mean_rel_err_pct": float(100 * np.mean(np.abs(p[mask] - g[mask]) / g[mask])),
        "total_bias_pct": float(100 * (p.sum() - g.sum()) / max(g.sum(), 1)),
    }
