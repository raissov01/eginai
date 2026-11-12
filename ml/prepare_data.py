"""Детекция датасетінен (бокстар) классификация датасетін құрастыру.

Дереккөз: Project-AgML/wheat_disease_detection (CC-BY-4.0) — Қытай, Хэнань,
далада түсірілген 4156 бидай суреті, 7 класс, бокстармен.

Не істейді:
  * әр боксты 25 % жиекпен қиып, өз класының папкасына салады;
  * (--background) әр суреттен бір «фон» патчын `healthy` класына алады —
    бұл датасетте сау класс жоқ кезге арналған; біздің датасетте healthy_leaf
    пен healthy_ear бар, сондықтан әдепкіде өшірулі;
  * датасеттің өз train/val/test бөлінісін сақтайды.

Іске қосу:
    python -m ml.prepare_data --src data/raw/wheat_det --dst data/cls
"""
from __future__ import annotations

import argparse
import io
import json
import random
from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

Box = tuple[int, int, int, int]  # (x0, y0, x1, y1)


def crop_box(img_w: int, img_h: int, bbox: list[float], margin: float, min_side: int) -> Box:
    """COCO bbox [x, y, w, h] → жиегі бар, сурет ішінде қалатын қиық."""
    x, y, w, h = bbox
    cx, cy = x + w / 2, y + h / 2
    half_w = max(w * (1 + 2 * margin), min_side) / 2
    half_h = max(h * (1 + 2 * margin), min_side) / 2
    x0, y0 = max(0, round(cx - half_w)), max(0, round(cy - half_h))
    x1, y1 = min(img_w, round(cx + half_w)), min(img_h, round(cy + half_h))
    return x0, y0, x1, y1


def iou(a: Box, b: Box) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter == 0:
        return 0.0
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])  # noqa: E731
    return inter / (area(a) + area(b) - inter)


def sample_background(boxes: list[Box], img_w: int, img_h: int, side: int, seed: int,
                      tries: int = 50) -> Box | None:
    """Ешбір бокспен қиылыспайтын шаршы патч; орын болмаса None."""
    if side > img_w or side > img_h:
        return None
    rng = random.Random(seed)
    for _ in range(tries):
        x0, y0 = rng.randint(0, img_w - side), rng.randint(0, img_h - side)
        cand = (x0, y0, x0 + side, y0 + side)
        if all(iou(cand, b) == 0 for b in boxes):
            return cand
    return None


def is_green(img: Image.Image) -> bool:
    """Патчта жасыл басым ба (топырақ/аспан патчтарын «сау» деп алмау үшін)."""
    mr, mg, mb = ImageStat.Stat(img.convert("RGB").resize((16, 16))).mean
    return mg > mr * 1.05 and mg > mb * 1.05


def _coco_to_box(b: list[float]) -> Box:
    return round(b[0]), round(b[1]), round(b[0] + b[2]), round(b[1] + b[3])


def build(src: Path, dst: Path, names: dict[str, str], margin: float = 0.25,
          min_side: int = 64, background: bool = False) -> Counter:
    import pyarrow.parquet as pq

    counts: Counter = Counter()
    n = 0
    for shard in sorted(src.glob("*.parquet")):
        pf = pq.ParquetFile(shard)
        for batch in pf.iter_batches(batch_size=16):
            for row in batch.to_pylist():
                n += 1
                split = {"valid": "val", "validation": "val"}.get(row["split"], row["split"])
                img = ImageOps.exif_transpose(Image.open(io.BytesIO(row["image"]["bytes"]))).convert("RGB")
                W, H = img.size
                cats, bboxes = row["objects"]["categories"], row["objects"]["bbox"]
                for k, (c, bb) in enumerate(zip(cats, bboxes)):
                    cls = names[str(c)]
                    if cls == "skip":
                        continue
                    crop = img.crop(crop_box(W, H, bb, margin, min_side))
                    out = dst / split / cls
                    out.mkdir(parents=True, exist_ok=True)
                    crop.save(out / f"{n:05d}_{k}.jpg", quality=92)
                    counts[(split, cls)] += 1
                if not background:
                    continue
                # «Сау» патч: бокстардан алыс, жасыл (датасетте сау класс жоқ болса ғана)
                side = max(min_side, min(W, H) // 4)
                bg = sample_background([_coco_to_box(b) for b in bboxes], W, H, side, seed=n)
                if bg is not None:
                    patch = img.crop(bg)
                    if is_green(patch):
                        out = dst / split / "healthy"
                        out.mkdir(parents=True, exist_ok=True)
                        patch.save(out / f"{n:05d}_bg.jpg", quality=92)
                        counts[(split, "healthy")] += 1
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("data/raw/wheat_det"))
    ap.add_argument("--dst", type=Path, default=Path("data/cls"))
    ap.add_argument("--names", type=Path, default=Path("ml/source_labels.json"),
                    help="датасеттің сандық класы → біздің class id (немесе 'skip')")
    ap.add_argument("--background", action="store_true",
                    help="фон патчтарын healthy класына қосу")
    args = ap.parse_args()
    names = {k: v for k, v in json.loads(args.names.read_text(encoding="utf-8")).items()
             if not k.startswith("_")}  # "_source" сияқты түсініктеме кілттерін өткізу
    counts = build(args.src, args.dst, names, background=args.background)
    for (split, cls), v in sorted(counts.items()):
        print(f"{split:5s} {cls:20s} {v}")


if __name__ == "__main__":
    main()
