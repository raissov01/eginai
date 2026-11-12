"""Чекпойнтты ONNX-ке экспорттау: екі шығыс — logits және соңғы feature map.

Feature map + классификатор салмақтары арқылы API CAM (класс активациясы
картасы) жылу картасын градиентсіз, тек numpy-мен есептейді.

    python -m ml.export_onnx --ckpt ml/runs/best.pt --out backend/app/model
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import timm
import torch
from torch import nn


class TwoHead(nn.Module):
    def __init__(self, m: nn.Module):
        super().__init__()
        self.m = m

    def forward(self, x):
        f = self.m.forward_features(x)  # [B, 1280, 7, 7]
        return self.m.forward_head(f), f


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=Path("ml/runs/best.pt"))
    ap.add_argument("--out", type=Path, default=Path("backend/app/model"))
    args = ap.parse_args()
    ck = torch.load(args.ckpt, map_location="cpu")
    model = timm.create_model(ck["arch"], pretrained=False, num_classes=len(ck["classes"]))
    model.load_state_dict(ck["state_dict"])
    model.eval()
    wrap = TwoHead(model).eval()

    args.out.mkdir(parents=True, exist_ok=True)
    onnx_path = args.out / "eginai.onnx"
    x = torch.randn(1, 3, 224, 224)
    torch.onnx.export(wrap, x, onnx_path, input_names=["image"], output_names=["logits", "features"],
                      dynamic_axes={"image": {0: "b"}, "logits": {0: "b"}, "features": {0: "b"}},
                      opset_version=17, dynamo=False)
    # Классификатор салмақтары (CAM үшін)
    np.save(args.out / "classifier_w.npy", model.get_classifier().weight.detach().numpy().astype(np.float32))
    np.save(args.out / "classifier_b.npy", model.get_classifier().bias.detach().numpy().astype(np.float32))
    (args.out / "labels.json").write_text(json.dumps(ck["classes"]), encoding="utf-8")

    # Тексеру: ONNX нәтижесі torch-пен бірдей болуы керек
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    lo, fo = sess.run(None, {"image": x.numpy()})
    with torch.no_grad():
        lt, ft = wrap(x)
    assert np.allclose(lo, lt.numpy(), atol=1e-3), "ONNX logits сәйкес емес"
    assert np.allclose(fo, ft.numpy(), atol=1e-3), "ONNX features сәйкес емес"
    # CAM формуласының дұрыстығы: avgpool(F)·Wᵀ + b == logits
    w, b = np.load(args.out / "classifier_w.npy"), np.load(args.out / "classifier_b.npy")
    assert np.allclose(fo.mean((2, 3)) @ w.T + b, lo, atol=1e-3), "CAM формуласы logits бермейді"
    print(f"OK → {onnx_path} ({onnx_path.stat().st_size / 1e6:.1f} MB), classes={ck['classes']}")


if __name__ == "__main__":
    main()
