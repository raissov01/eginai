"""Масақ детекторына деректер: Global Wheat Head (GWHD 2020, MIT) → torch Dataset.

Дереккөз: HF `yinsights8/global-wheat-detection-hf` (Kaggle «Global Wheat
Detection» train бөлігі, 3373 сурет 1024×1024, рамкалар [x1, y1, x2, y2, ауданы]).
Бөлу сурет идентификаторының хэшімен (80/10/10) — детерминистік, қайталанады.

«Дрон биіктігі» аугментациясы (`degrade`): суретті s есе кішірейтіп, қайта
1024-ке үлкейтеміз. Геометрия (рамкалар) өзгермейді, тек ажыратымдылық
төмендейді — бұл жоғарырақ ұшқан камераның GSD-сін имитациялайды.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import tv_tensors
from torchvision.transforms import v2 as T
from torchvision.transforms.v2 import functional as F

DATA = Path("data/gwhd2020")
SIZE = 1024


def split_of(image_id: str) -> str:
    h = int(hashlib.md5(image_id.encode()).hexdigest(), 16) % 10
    return "test" if h == 0 else "val" if h == 1 else "train"


def extract(data: Path = DATA) -> Path:
    """Parquet → data/gwhd2020/img/*.jpg + index.json (бір рет; жадты үнемдеу үшін ағынмен)."""
    index_path = data / "index.json"
    if index_path.exists():
        return index_path
    (data / "img").mkdir(exist_ok=True)
    index = []
    for f in sorted(data.glob("*.parquet")):
        for batch in pq.ParquetFile(f).iter_batches(batch_size=64, columns=["image_id", "image", "boxes"]):
            for r in batch.to_pylist():
                (data / "img" / f"{r['image_id']}.jpg").write_bytes(r["image"]["bytes"])
                b = np.array(r["boxes"], dtype=np.float32).reshape(-1, 5)[:, :4]
                index.append({"id": r["image_id"], "split": split_of(r["image_id"]), "boxes": b.tolist()})
    index_path.write_text(json.dumps(index))
    return index_path


def load_rows(split: str, data: Path = DATA) -> list[dict]:
    index = json.loads(extract(data).read_text())
    return [{"id": r["id"], "path": str(data / "img" / f"{r['id']}.jpg"),
             "boxes": np.array(r["boxes"], dtype=np.float32).reshape(-1, 4)}
            for r in index if r["split"] == split]


def degrade(img: torch.Tensor, s: float) -> torch.Tensor:
    """Ажыратымдылықты s есе төмендету (s=1 — өзгеріссіз), өлшемі сол күйі."""
    if s >= 0.999:
        return img
    h, w = img.shape[-2:]
    small = F.resize(img, [max(8, round(h * s)), max(8, round(w * s))], antialias=True)
    return F.resize(small, [h, w], antialias=True)


class Heads(Dataset):
    def __init__(self, rows: list[dict], train: bool, degrade_p: float = 0.5,
                 degrade_range: tuple[float, float] = (0.2, 1.0), fixed_scale: float = 1.0):
        self.rows, self.train = rows, train
        self.degrade_p, self.degrade_range, self.fixed_scale = degrade_p, degrade_range, fixed_scale
        self.aug = T.Compose([
            T.RandomHorizontalFlip(), T.RandomVerticalFlip(),
            T.RandomApply([T.RandomRotation((90, 90))], p=0.5),
            T.ColorJitter(0.3, 0.3, 0.3, 0.03),
        ])

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int):
        r = self.rows[i]
        img = F.to_image(Image.open(r["path"]).convert("RGB"))
        boxes = tv_tensors.BoundingBoxes(torch.from_numpy(r["boxes"]), format="XYXY",
                                         canvas_size=(int(img.shape[-2]), int(img.shape[-1])))
        if self.train:
            img, boxes = self.aug(img, boxes)
            if torch.rand(()) < self.degrade_p:
                lo, hi = self.degrade_range
                img = degrade(img, float(torch.empty(()).uniform_(lo, hi)))
        else:
            img = degrade(img, self.fixed_scale)
        img = F.to_dtype(img, torch.float32, scale=True)
        b = boxes.as_subclass(torch.Tensor)
        keep = (b[:, 2] - b[:, 0] > 2) & (b[:, 3] - b[:, 1] > 2)
        b = b[keep]
        return img, {"boxes": b, "labels": torch.ones(len(b), dtype=torch.int64)}


def collate(batch):
    return tuple(zip(*batch))
