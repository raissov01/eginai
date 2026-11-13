"""Қосымша ашық датасеттер → 9 класс (жапырақ септориозы, тамыр/сабақ түбі шірігі қосылады).

Дереккөздер (бәрі CC BY 4.0):
  eth — Mendeley wgd66f8n6h «Wheat Leaf Dataset» (Эфиопия, далада, DSLR);
  jic — Zenodo 7573133, Long et al. 2023, John Innes (Ұлыбритания, телефон, егіс ішінде);
  bgd — Mendeley 5gc7hwydwg «Disease Dataset of Wheat» (Бангладеш), тек «Original Dataset».
Алынбайтыны: bgd WheatBlast (ҚР-да жоқ, фузариозға ұқсас), BlackPoint (дән ауруы), LeafBlight (бұлыңғыр).

Не істейді:
  * суретті ұзын жағы 1024 px-ке кішірейтіп data/extra/<source>/<class>/ ішіне JPEG етіп сақтайды;
  * сериямен түсірілген ұқсас кадрларды (aHash 16×16, Хэмминг ≤ 6) бір топқа біріктіріп,
    топ бойынша 70/15/15 бөледі — бір серия train мен test-ке бөлініп кетпейді;
  * data/cls (бастапқы 7 класс) + қосымшалар → data/<out>/{train,val,test}/<class>/ (симлинк);
  * --septoria eth|jic: кросс-тексеріс — тек көрсетілген көздің септориозы үйретуге кіреді,
    екіншісінікі толығымен test-ке кетеді (модель фонды емес, ауруды үйренгенін тексеру үшін).
  * манифест data/<out>/manifest.csv: path, class, source, split.

    python -m ml.prepare_extra --out cls9
    python -m ml.prepare_extra --out cls9_ethS --septoria eth
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path("data")
NEW = ROOT / "newdis"
SRC = {
    "eth": (NEW / "eth/wheat_leaf", {"Healthy": "healthy_leaf", "septoria": "septoria_leaf",
                                     "stripe_rust": "stripe_rust"}),
    "jic": (NEW / "jic", {"BrownRust": "leaf_rust", "Healthy": "healthy_leaf", "Mildew": "powdery_mildew",
                          "Septoria": "septoria_leaf", "YellowRust": "stripe_rust"}),
    "bgd": (NEW / "bgd/Wheat Disease/Original Dataset", {"FusariumFootRot": "root_rot",
                                                         "HealthyLeaf": "healthy_leaf"}),
}
EXT = {".jpg", ".jpeg", ".png"}


def files_of(source: str) -> list[tuple[Path, str]]:
    root, mapping = SRC[source]
    out = []
    if source == "jic":  # бір папка, класс файл атауында: Septoria6659.png
        for f in sorted(root.iterdir()):
            stem = f.stem.rstrip("0123456789")
            if f.suffix.lower() in EXT and stem in mapping:
                out.append((f, mapping[stem]))
    else:
        for d, cls in mapping.items():
            out += [(f, cls) for f in sorted((root / d).iterdir()) if f.suffix.lower() in EXT]
    return out


def ahash(im: Image.Image) -> np.ndarray:
    a = np.asarray(im.convert("L").resize((16, 16)), dtype=np.float32)
    return (a > a.mean()).flatten()


def groups(hashes: list[np.ndarray], thr: int = 6) -> list[int]:
    """Union-find: Хэмминг ≤ thr болған кадрлар бір топ."""
    n = len(hashes)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    H = np.array(hashes)
    for i in range(n):
        d = (H[i + 1:] != H[i]).sum(1)
        for j in np.nonzero(d <= thr)[0]:
            parent[find(i)] = find(i + 1 + int(j))
    return [find(i) for i in range(n)]


def split_of(key: str) -> str:
    h = int(hashlib.md5(key.encode()).hexdigest(), 16) % 100
    return "test" if h < 15 else "val" if h < 30 else "train"


def build_extra() -> list[dict]:
    """data/extra-ға кішірейтілген көшірмелер + топтық бөлу (бір рет есептеледі)."""
    rows = []
    for source in SRC:
        items = files_of(source)
        hashes, outs = [], []
        for f, cls in items:
            dst = ROOT / "extra" / source / cls / (f.stem + ".jpg")
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
                im.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                im.save(dst, quality=92)
            im = Image.open(dst)
            hashes.append(ahash(im))
            outs.append((dst, cls))
        gid = groups(hashes)
        for (dst, cls), g in zip(outs, gid):
            rows.append({"path": str(dst), "class": cls, "source": source,
                         "split": split_of(f"{source}:{cls}:{g}"), "group": f"{source}:{g}"})
        print(f"{source}: {len(items)} сурет, {len(set(gid))} топ")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="cls9")
    ap.add_argument("--septoria", choices=["eth", "jic"], default=None)
    args = ap.parse_args()
    extra = build_extra()
    out = ROOT / args.out
    manifest = []
    # бастапқы 7 класс өзгеріссіз (source=base)
    for split in ("train", "val", "test"):
        for f in sorted((ROOT / "cls" / split).rglob("*.jpg")):
            manifest.append({"path": str(f), "class": f.parent.name, "source": "base", "split": split})
    for r in extra:
        r = dict(r)
        if args.septoria and r["class"] == "septoria_leaf" and r["source"] != args.septoria:
            r["split"] = "test"  # кросс-тексеріс: басқа көздің септориозы тек тестте
        manifest.append(r)
    for r in manifest:
        dst = out / r["split"] / r["class"] / f"{r['source']}_{Path(r['path']).name}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            os.symlink(Path(r["path"]).resolve(), dst)
        r["link"] = str(dst)
    with open(out / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["link", "path", "class", "source", "split", "group"], extrasaction="ignore")
        w.writeheader()
        w.writerows(manifest)
    from collections import Counter
    c = Counter((r["split"], r["class"]) for r in manifest)
    for cls in sorted({r["class"] for r in manifest}):
        print(f"{cls:22s} train {c[('train', cls)]:5d}  val {c[('val', cls)]:4d}  test {c[('test', cls)]:4d}")


if __name__ == "__main__":
    main()
