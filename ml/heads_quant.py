"""Масақ детекторын кішірейту: FC қабаттарын (Gemm/MatMul) int8-ке динамикалық квантизациялау.

Салмақтың ~73 %-ы box_head.fc6-да (51 МБ), сондықтан тек Gemm/MatMul квантизацияланады —
Conv fp32 қалады (CPU-да ConvInteger баяу). Тест бөлігінде fp32-мен салыстырылады:
AP@0.5, санау қателігі, CPU уақыты; толық және 0.35 ажыратымдылықта (~3.7 м).

    python -m ml.heads_quant          → drone/model/heads.int8.onnx + ml/heads_quant.json
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import numpy as np

from drone.heads import HeadCounter
from ml.heads_eval import counts_at, run
from ml.heads_metrics import average_precision, count_errors

SRC = Path("drone/model")


def quantize(dst: Path) -> None:
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(SRC / "heads.onnx", dst, op_types_to_quantize=["Gemm", "MatMul"],
                     weight_type=QuantType.QInt8)


def main() -> None:
    from ml.heads_data import load_rows
    dst = SRC / "heads.int8.onnx"
    quantize(dst)
    test = load_rows("test")
    thr = json.loads((SRC / "heads.json").read_text())["score_threshold"]
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(SRC / "heads.json", tmp / "heads.json")
    os.symlink(dst.resolve(), tmp / "heads.onnx")
    res = {"size_mb": {"fp32": round((SRC / "heads.onnx").stat().st_size / 1e6, 1),
                       "int8": round(dst.stat().st_size / 1e6, 1)}, "rows": []}
    for name, d in (("fp32", SRC), ("int8", tmp)):
        hc = HeadCounter(d, score=0.05)
        for s in (1.0, 0.35):
            preds, gts, times = run(hc, test, s)
            row = {"model": name, "scale": s, "ap50": round(average_precision(preds, gts, 0.5), 4),
                   **{k: round(v, 2) for k, v in count_errors(counts_at(preds, thr), [len(g) for g in gts]).items()},
                   "cpu_ms_median": round(1000 * float(np.median(times)))}
            res["rows"].append(row)
            print(json.dumps(row), flush=True)
        del hc
    Path("ml/heads_quant.json").write_text(json.dumps(res, indent=1))
    print(res["size_mb"])


if __name__ == "__main__":
    main()
