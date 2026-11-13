"""Масақ детекторын ONNX-ке экспорттау → drone/model/heads.onnx (+ heads.json).

    python -m ml.heads_export --ckpt ml/runs/heads/best.pt

Кіріс: бір сурет [3, 1024, 1024] float 0..1. Шығыс: boxes [N,4] (xyxy), scores [N].
Экспорттан кейін нақты суретте torch пен ONNX нәтижесі салыстырылады.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from PIL import Image
from torch import nn

from ml.heads_data import load_rows
from ml.heads_model import SIZE, build


class Single(nn.Module):
    def __init__(self, m: nn.Module):
        super().__init__()
        self.m = m

    def forward(self, x):
        o = self.m([x])[0]
        return o["boxes"], o["scores"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=Path("ml/runs/heads/best.pt"))
    ap.add_argument("--out", type=Path, default=Path("drone/model"))
    args = ap.parse_args()
    ck = torch.load(args.ckpt, map_location="cpu")
    model = build(pretrained=False)
    model.load_state_dict(ck["state_dict"])
    wrap = Single(model).eval()

    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "heads.onnx"
    x = torch.rand(3, SIZE, SIZE)
    torch.onnx.export(wrap, (x,), path, input_names=["image"], output_names=["boxes", "scores"],
                      dynamic_axes={"boxes": {0: "n"}, "scores": {0: "n"}}, opset_version=17, dynamo=False)

    # Тексеру нақты тест суретінде
    row = load_rows("test")[0]
    img = np.asarray(Image.open(row["path"]).convert("RGB")).astype(np.float32).transpose(2, 0, 1) / 255
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    bo, so = sess.run(None, {"image": img})
    with torch.no_grad():
        bt, st = wrap(torch.from_numpy(img))
    k = min(len(so), len(st), 50)
    assert abs(len(so) - len(st)) <= 2, f"бокс саны әртүрлі: onnx={len(so)} torch={len(st)}"
    assert np.allclose(bo[:k], bt.numpy()[:k], atol=1.0), "ONNX боксы torch-тан ерекше"
    meta_path = args.out / "heads.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.update({"arch": ck["arch"], "input": [3, SIZE, SIZE], "epoch": ck["epoch"],
                 "train_data": "Global Wheat Head Dataset 2020 (MIT)"})
    meta.setdefault("score_threshold", 0.5)
    meta_path.write_text(json.dumps(meta, indent=1))
    print(f"OK → {path} ({path.stat().st_size / 1e6:.1f} MB), onnx={len(so)} torch={len(st)} бокс")


if __name__ == "__main__":
    main()
