"""Чекпойнтты манифест бойынша бағалау: әр дереккөз (base/eth/jic/bgd) және әр класс бөлек.

Бастапқы 580 тест суретіндегі дәлдік (source=base) — регрессия бақылауы;
кросс-тексерісте: басқа көзден келген септориоз суреттерінің recall-ы.

    python -m ml.eval_sources --ckpt ml/runs/cls9/best.pt --data data/cls9 --out ml/runs/cls9/eval.json
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import timm
import torch
from PIL import Image

from ml.train import eval_tf


@torch.no_grad()
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    ck = torch.load(args.ckpt, map_location="cpu")
    classes = ck["classes"]
    model = timm.create_model(ck["arch"], pretrained=False, num_classes=len(classes))
    model.load_state_dict(ck["state_dict"])
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.eval().to(dev)
    tf = eval_tf()
    rows = [r for r in csv.DictReader(open(args.data / "manifest.csv")) if r["split"] == "test"]
    by_src, by_cls, conf = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0]), defaultdict(int)
    batch, meta = [], []

    def flush():
        if not batch:
            return
        pred = model(torch.stack(batch).to(dev)).argmax(1).cpu().tolist()
        for (src, cls), p in zip(meta, pred):
            ok = classes[p] == cls
            by_src[src][0] += ok; by_src[src][1] += 1
            by_cls[f"{src}/{cls}"][0] += ok; by_cls[f"{src}/{cls}"][1] += 1
            if not ok:
                conf[f"{cls}->{classes[p]}"] += 1
        batch.clear(); meta.clear()

    for r in rows:
        batch.append(tf(Image.open(r["link"]).convert("RGB")))
        meta.append((r["source"], r["class"]))
        if len(batch) == 64:
            flush()
    flush()
    res = {"classes": classes,
           "by_source": {k: {"acc": round(a / n, 4), "n": n} for k, (a, n) in sorted(by_src.items())},
           "by_class": {k: {"recall": round(a / n, 4), "n": n} for k, (a, n) in sorted(by_cls.items())},
           "top_confusions": dict(sorted(conf.items(), key=lambda x: -x[1])[:12])}
    args.out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res["by_source"]), "\n", {k: v for k, v in res["by_class"].items() if "septoria" in k or "root" in k})


if __name__ == "__main__":
    main()
