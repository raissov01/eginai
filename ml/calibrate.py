"""Сенімділікті калибрлеу (temperature scaling, Guo et al. 2017).

Val жиынында logits / T температурасын NLL бойынша таңдаймыз; тестте ECE (күтілетін
калибрлеу қатесі) T-ге дейін және кейін есептеледі. Нәтиже <model_dir>/calibration.json —
backend/app/inference.py оны бар болса оқиды. Класс болжамы өзгермейді (argmax сол),
тек ықтималдық шынайырақ болады, сондықтан «сенімсіз» (p < 0.5) шегі мағыналырақ.

    python -m ml.calibrate --ckpt ml/runs/cls9/best.pt --data data/cls9 --out backend/app/model
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import timm
import torch
from torch.utils.data import DataLoader
from torchvision import datasets

from ml.train import eval_tf


@torch.no_grad()
def logits_of(model, loader, dev):
    zs, ys = [], []
    for x, y in loader:
        zs.append(model(x.to(dev)).float().cpu())
        ys.append(y)
    return torch.cat(zs), torch.cat(ys)


def ece(probs: torch.Tensor, y: torch.Tensor, bins: int = 15) -> float:
    conf, pred = probs.max(1)
    acc = (pred == y).float()
    edges = torch.linspace(0, 1, bins + 1)
    e = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            e += m.float().mean().item() * abs(acc[m].mean().item() - conf[m].mean().item())
    return e


def fit_temperature(z: torch.Tensor, y: torch.Tensor) -> float:
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=200)
    nll = torch.nn.CrossEntropyLoss()

    def step():
        opt.zero_grad()
        loss = nll(z / log_t.exp(), y)
        loss.backward()
        return loss
    opt.step(step)
    return float(log_t.exp())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    ck = torch.load(args.ckpt, map_location="cpu")
    model = timm.create_model(ck["arch"], pretrained=False, num_classes=len(ck["classes"]))
    model.load_state_dict(ck["state_dict"])
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.eval().to(dev)
    sets = {s: datasets.ImageFolder(args.data / s, eval_tf()) for s in ("val", "test")}
    assert sets["val"].classes == ck["classes"]
    zv, yv = logits_of(model, DataLoader(sets["val"], 64, num_workers=2), dev)
    zt, yt = logits_of(model, DataLoader(sets["test"], 64, num_workers=2), dev)
    t = fit_temperature(zv, yv)
    res = {"temperature": round(t, 4),
           "test_ece_before": round(ece(zt.softmax(1), yt), 4),
           "test_ece_after": round(ece((zt / t).softmax(1), yt), 4),
           "test_acc": round(float((zt.argmax(1) == yt).float().mean()), 4)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "calibration.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res))


if __name__ == "__main__":
    main()
