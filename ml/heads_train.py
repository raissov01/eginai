"""Масақ детекторын үйрету (GWHD 2020).

    python -m ml.heads_train --epochs 20

GTX 1650 (4 ГБ): 1024 px, batch 4, AMP. Ең жақсы чекпойнт val AP@0.5 бойынша
`ml/runs/heads/best.pt`-ке сақталады.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from ml.heads_data import Heads, collate, load_rows
from ml.heads_metrics import average_precision, count_errors
from ml.heads_model import build

SCORE = 0.5  # санау үшін сенімділік шегі (val-да таңдалады, evaluate-те қайта тексеріледі)


@torch.no_grad()
def run_eval(model, loader, device) -> tuple[list, list]:
    model.eval()
    preds, gts = [], []
    for imgs, tgts in loader:
        with torch.autocast(device, enabled=device == "cuda"):
            out = model([i.to(device) for i in imgs])
        for o, t in zip(out, tgts):
            preds.append((o["boxes"].float().cpu().numpy(), o["scores"].float().cpu().numpy()))
            gts.append(t["boxes"].numpy())
    return preds, gts


def summarize(preds, gts, score: float = SCORE) -> dict:
    counts = [int((s >= score).sum()) for _, s in preds]
    return {"ap50": round(average_precision(preds, gts, 0.5), 4),
            "ap75": round(average_precision(preds, gts, 0.75), 4),
            **{k: round(v, 3) for k, v in count_errors(counts, [len(g) for g in gts]).items()}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--bs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=0.02)
    ap.add_argument("--out", type=Path, default=Path("ml/runs/heads"))
    ap.add_argument("--limit", type=int, default=0, help="жылдам тексеру үшін")
    args = ap.parse_args()
    torch.manual_seed(42)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tr_rows, va_rows = load_rows("train"), load_rows("val")
    if args.limit:
        tr_rows, va_rows = tr_rows[:args.limit], va_rows[:max(8, args.limit // 8)]
    print(f"train={len(tr_rows)} val={len(va_rows)}", flush=True)
    tl = DataLoader(Heads(tr_rows, train=True), args.bs, shuffle=True, num_workers=3,
                    collate_fn=collate, drop_last=True, persistent_workers=True)
    vl = DataLoader(Heads(va_rows, train=False), 4, num_workers=2, collate_fn=collate)

    model = build().to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.SGD(params, lr=args.lr, momentum=0.9, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=args.epochs * len(tl),
                                                pct_start=0.1)
    scaler = torch.amp.GradScaler(enabled=device == "cuda")
    args.out.mkdir(parents=True, exist_ok=True)
    best, history = -1.0, []
    for ep in range(1, args.epochs + 1):
        model.train()
        t0, tot = time.time(), 0.0
        for imgs, tgts in tl:
            imgs = [i.to(device, non_blocking=True) for i in imgs]
            tgts = [{k: v.to(device) for k, v in t.items()} for t in tgts]
            with torch.autocast(device, enabled=device == "cuda"):
                loss = sum(model(imgs, tgts).values())
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(params, 10.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            tot += loss.item()
        preds, gts = run_eval(model, vl, device)
        row = {"epoch": ep, "loss": round(tot / len(tl), 4), **summarize(preds, gts),
               "sec": round(time.time() - t0)}
        history.append(row)
        print(json.dumps(row), flush=True)
        if row["ap50"] > best:
            best = row["ap50"]
            torch.save({"state_dict": model.state_dict(), "arch": "fasterrcnn_mobilenet_v3_large_fpn",
                        "epoch": ep}, args.out / "best.pt")
    (args.out / "history.json").write_text(json.dumps(history, indent=1))
    print(f"best val AP50 = {best:.4f}")


if __name__ == "__main__":
    main()
