"""EfficientNet-B0-ны бидай ауруларына үйрету (transfer learning).

    python -m ml.train --data data/cls --epochs 12

GTX 1650 (4 ГБ) үшін: 224 px, batch 32, AMP. Ең жақсы чекпойнт val macro-F1
бойынша `ml/runs/best.pt`-ке сақталады.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import timm
import torch
from sklearn.metrics import f1_score
from torch import nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets
from torchvision.transforms import v2 as T

MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)  # ImageNet
SIZE = 224


def train_tf() -> T.Compose:
    # Далалық фото: жарық, бұрыш, қашықтық әртүрлі — соны имитациялаймыз
    return T.Compose([
        T.RandomResizedCrop(SIZE, scale=(0.5, 1.0)),
        T.RandomHorizontalFlip(), T.RandomVerticalFlip(),
        T.RandomRotation(20),
        T.ColorJitter(0.3, 0.3, 0.2, 0.03),
        T.ToImage(), T.ToDtype(torch.float32, scale=True), T.Normalize(MEAN, STD),
    ])


def eval_tf() -> T.Compose:
    return T.Compose([T.Resize((SIZE, SIZE)), T.ToImage(),
                      T.ToDtype(torch.float32, scale=True), T.Normalize(MEAN, STD)])


def balanced_sampler(ds: datasets.ImageFolder) -> WeightedRandomSampler:
    """Сирек кластар әр эпохада жиірек көрінуі үшін."""
    counts = torch.bincount(torch.tensor(ds.targets), minlength=len(ds.classes)).float()
    w = (1.0 / counts)[torch.tensor(ds.targets)]
    return WeightedRandomSampler(w, num_samples=len(ds.targets), replacement=True)


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: str) -> tuple[float, float, list, list]:
    model.eval()
    ys, ps = [], []
    for x, y in loader:
        with torch.autocast(device, enabled=device == "cuda"):
            p = model(x.to(device)).argmax(1).cpu()
        ys += y.tolist()
        ps += p.tolist()
    acc = sum(a == b for a, b in zip(ys, ps)) / len(ys)
    return acc, f1_score(ys, ps, average="macro"), ys, ps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/cls"))
    ap.add_argument("--out", type=Path, default=Path("ml/runs"))
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--lr", type=float, default=4e-4)
    ap.add_argument("--patience", type=int, default=4)
    args = ap.parse_args()
    torch.manual_seed(42)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tr = datasets.ImageFolder(args.data / "train", train_tf())
    va = datasets.ImageFolder(args.data / "val", eval_tf())
    assert tr.classes == va.classes, "train/val класстары сәйкес емес"
    tl = DataLoader(tr, args.bs, sampler=balanced_sampler(tr), num_workers=6, pin_memory=True,
                    drop_last=True, persistent_workers=True)
    vl = DataLoader(va, 64, num_workers=4)

    model = timm.create_model("efficientnet_b0.ra_in1k", pretrained=True,
                              num_classes=len(tr.classes), drop_rate=0.3).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.02)
    steps = args.epochs * len(tl)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=steps, pct_start=0.15)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)
    scaler = torch.amp.GradScaler(enabled=device == "cuda")

    args.out.mkdir(parents=True, exist_ok=True)
    best, bad, history = -1.0, 0, []
    for ep in range(1, args.epochs + 1):
        model.train()
        t0, tot = time.time(), 0.0
        for x, y in tl:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device, enabled=device == "cuda"):
                loss = loss_fn(model(x), y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            tot += loss.item()
        acc, f1, _, _ = evaluate(model, vl, device)
        row = {"epoch": ep, "loss": round(tot / len(tl), 4), "val_acc": round(acc, 4),
               "val_macro_f1": round(f1, 4), "sec": round(time.time() - t0)}
        history.append(row)
        print(json.dumps(row), flush=True)
        if f1 > best:
            best, bad = f1, 0
            torch.save({"state_dict": model.state_dict(), "classes": tr.classes,
                        "arch": "efficientnet_b0.ra_in1k"}, args.out / "best.pt")
        else:
            bad += 1
            if bad >= args.patience:
                print("early stop", flush=True)
                break
    (args.out / "history.json").write_text(json.dumps(history, indent=1))
    print(f"best val macro-F1 = {best:.4f}")


if __name__ == "__main__":
    main()
