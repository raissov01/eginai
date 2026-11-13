"""Дрон кадрындағы масақтарды санау (ONNX, тек CPU) → масақ/м² → өнімділік.

Үлкен кадр (мысалы, 5280×3956) 1024 px тайлдарға қабаттасумен бөлінеді;
масақ тек центрі тайлдың «өз» аймағына түссе саналады — шекарадағы масақ екі
рет саналмайды.

    from drone.heads import HeadCounter
    hc = HeadCounter()                       # drone/model/heads.onnx
    r = hc.count(jpg_bytes, gsd_cm=0.2)      # {"count", "heads_m2", "boxes", ...}
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

MODEL_DIR = Path(__file__).resolve().parent / "model"
TILE, OVERLAP = 1024, 96


def tiles(w: int, h: int, tile: int = TILE, overlap: int = OVERLAP) -> list[tuple[int, int, int, int, int, int, int, int]]:
    """(x0, y0, x1, y1) тайл + (cx0, cy0, cx1, cy1) — тайлдың «өз» аймағы (центрлер осында саналады)."""
    def axis(n: int) -> list[tuple[int, int, int, int]]:
        if n <= tile:
            return [(0, n, 0, n)]
        step = tile - overlap
        starts = list(range(0, n - tile, step)) + [n - tile]
        out = []
        for k, s in enumerate(starts):
            lo = 0 if k == 0 else (s + starts[k - 1] + tile) // 2   # алдыңғы тайлмен қабаттасудың ортасы
            hi = n if k == len(starts) - 1 else (starts[k + 1] + s + tile) // 2
            out.append((s, s + tile, lo, hi))
        return out
    return [(x0, y0, x1, y1, cx0, cy0, cx1, cy1)
            for (y0, y1, cy0, cy1) in axis(h) for (x0, x1, cx0, cx1) in axis(w)]


def heads_per_m2(count: int, w_px: int, h_px: int, gsd_cm: float) -> float:
    area_m2 = (w_px * gsd_cm / 100) * (h_px * gsd_cm / 100)
    return count / area_m2


class HeadCounter:
    def __init__(self, model_dir: Path = MODEL_DIR, score: float | None = None):
        import onnxruntime as ort
        meta = json.loads((model_dir / "heads.json").read_text())
        self.score = score if score is not None else meta["score_threshold"]
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        self.sess = ort.InferenceSession(str(model_dir / "heads.onnx"), opts,
                                         providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name

    def _detect(self, tile: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        h, w = tile.shape[:2]
        if (h, w) != (TILE, TILE):  # шеткі кіші тайлды толтырамыз
            pad = np.zeros((TILE, TILE, 3), np.uint8)
            pad[:h, :w] = tile
            tile = pad
        x = tile.astype(np.float32).transpose(2, 0, 1) / 255.0
        boxes, scores = self.sess.run(None, {self.inp: x})[:2]
        keep = scores >= self.score
        return boxes[keep], scores[keep]

    def count(self, image: bytes | Image.Image, gsd_cm: float | None = None) -> dict:
        im = image if isinstance(image, Image.Image) else Image.open(io.BytesIO(image))
        a = np.asarray(im.convert("RGB"))
        H, W = a.shape[:2]
        all_boxes, all_scores = [], []
        for x0, y0, x1, y1, cx0, cy0, cx1, cy1 in tiles(W, H):
            b, s = self._detect(a[y0:y1, x0:x1])
            if len(b):
                b = b + np.array([x0, y0, x0, y0], np.float32)
                cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
                own = (cx >= cx0) & (cx < cx1) & (cy >= cy0) & (cy < cy1)
                all_boxes.append(b[own])
                all_scores.append(s[own])
        boxes = np.concatenate(all_boxes) if all_boxes else np.zeros((0, 4), np.float32)
        scores = np.concatenate(all_scores) if all_scores else np.zeros(0, np.float32)
        out = {"count": int(len(boxes)), "width": W, "height": H,
               "boxes": boxes.round(1).tolist(), "scores": scores.round(3).tolist()}
        if gsd_cm:
            out["heads_m2"] = heads_per_m2(len(boxes), W, H, gsd_cm)
        return out
