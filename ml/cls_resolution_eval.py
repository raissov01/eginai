"""Ауру классификаторы ажыратымдылық төмендегенде қалай жұмыс істейді.

Тест бөлігіндегі әр фрагментті ұзын жағы T пиксель болатындай кішірейтіп,
қайта бастапқы өлшеміне үлкейтеміз (детальдар жоғалады, өлшем сол күйі) да,
API-дағы сол ONNX модельмен болжаймыз. T — зақымдалған аймақ кадрда қанша
пиксельге созылатыны. Бұл дронның қандай биіктікте жапырақ ауруын тани
алатынын бағалауға керек.

    python -m ml.cls_resolution_eval
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.inference import Predictor  # noqa: E402

TARGETS = [None, 224, 112, 56, 28, 14, 7]   # None — бастапқы сурет


def degrade(path: Path, t: int | None) -> bytes:
    im = Image.open(path).convert("RGB")
    if t is not None and max(im.size) > t:
        w, h = im.size
        k = t / max(w, h)
        im = im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.Resampling.LANCZOS)
        im = im.resize((w, h), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def main() -> None:
    data = Path("data/cls/test")
    pred = Predictor(Path("backend/app/model"))
    files = [(c, f) for c in pred.labels for f in sorted((data / c).glob("*.jpg"))]
    rows = []
    for t in TARGETS:
        ok = unsure = ok_conf = n_conf = 0
        for c, f in files:
            r = pred.predict(degrade(f, t), with_cam=False)
            hit = r.top[0][0] == c
            ok += hit
            if r.unsure:
                unsure += 1
            else:
                n_conf += 1
                ok_conf += hit
        row = {"lesion_px": t or "orig", "accuracy": round(ok / len(files), 4),
               "unsure_share": round(unsure / len(files), 4),
               "accuracy_confident": round(ok_conf / n_conf, 4) if n_conf else None}
        rows.append(row)
        print(json.dumps(row), flush=True)
    Path("ml/cls_resolution.json").write_text(json.dumps({"n_test": len(files), "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
