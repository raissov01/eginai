"""Робасттық тесті: фермер телефонының нақты «бұзылулары» кезінде дәлдік пен «сенімсіз» үлесі.

Тест суреттеріне бұлыңғырлық, қараңғылық/жарықтық, қатты JPEG сығу, бұру, шу қолданылып,
API-дағы сол Predictor-мен болжанады (CAM-сыз). Нәтиже ml/robustness.json.

    python -m ml.robustness_eval --model backend/app/model --data data/cls/test
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.inference import Predictor  # noqa: E402


def jpeg(im: Image.Image, q: int = 92) -> bytes:
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q)
    return b.getvalue()


def noise(im: Image.Image, sigma: float) -> Image.Image:
    a = np.asarray(im, dtype=np.float32) + np.random.default_rng(0).normal(0, sigma, (im.height, im.width, 3))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


PERTURB = {
    "clean": lambda im: jpeg(im),
    "blur_r2": lambda im: jpeg(im.filter(ImageFilter.GaussianBlur(2))),
    "blur_r4": lambda im: jpeg(im.filter(ImageFilter.GaussianBlur(4))),
    "dark_0.5": lambda im: jpeg(ImageEnhance.Brightness(im).enhance(0.5)),
    "bright_1.6": lambda im: jpeg(ImageEnhance.Brightness(im).enhance(1.6)),
    "low_contrast_0.5": lambda im: jpeg(ImageEnhance.Contrast(im).enhance(0.5)),
    "jpeg_q15": lambda im: jpeg(im, 15),
    "rotate_90": lambda im: jpeg(im.rotate(90, expand=True)),
    "noise_s20": lambda im: jpeg(noise(im, 20)),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=Path("backend/app/model"))
    ap.add_argument("--data", type=Path, default=Path("data/cls/test"))
    ap.add_argument("--per-class", type=int, default=40)
    ap.add_argument("--out", type=Path, default=Path("ml/robustness.json"))
    args = ap.parse_args()
    pred = Predictor(args.model)
    files = [(c, f) for c in pred.labels if (args.data / c).is_dir()
             for f in sorted((args.data / c).glob("*.jpg"))[:args.per_class]]
    rows = {}
    for name, fn in PERTURB.items():
        ok = unsure = ok_conf = n_conf = 0
        for c, f in files:
            r = pred.predict(fn(Image.open(f).convert("RGB")), with_cam=False)
            hit = r.top[0][0] == c
            ok += hit
            if r.unsure:
                unsure += 1
            else:
                n_conf += 1
                ok_conf += hit
        rows[name] = {"accuracy": round(ok / len(files), 4), "unsure_share": round(unsure / len(files), 4),
                      "accuracy_confident": round(ok_conf / max(n_conf, 1), 4)}
        print(name, rows[name], flush=True)
    args.out.write_text(json.dumps({"n": len(files), "model": str(args.model), "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
