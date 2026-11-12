"""Диагностика ядросы: ONNX модель + CAM жылу картасы.

Модельдің екі шығысы бар: `logits` және соңғы конволюция қабатының feature
map-і `features` [1, 1280, 7, 7]. Классификатор — global average pooling +
сызықтық қабат, сондықтан класс c үшін CAM = ReLU(Σ_k W[c,k] · F_k) — бұл
дәл формула (Zhou et al., 2016), градиент керек емес, numpy-мен есептеледі.
"""
from __future__ import annotations

import base64
import io
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps, UnidentifiedImageError

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
SIZE = 224
MAX_BYTES = 10 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 80_000_000  # «декомпрессия бомбасынан» қорғаныс


class ImageError(ValueError):
    """Енгізілген файл сурет емес немесе бүлінген. `code` — API қате коды."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class Prediction:
    top: list[tuple[str, float]]       # [(class_id, ықтималдық)], кему ретімен
    unsure: bool                       # True → «қайта түсіріңіз» деп жауап беру
    reason: str | None = None          # unsure себебі: "not_plant" | "low_confidence"
    cam_jpeg_b64: str | None = None    # жылу картасы қабатталған сурет
    affected_pct: float | None = None  # белгілер ауданының бағасы, %
    ms: float = 0.0
    plant_frac: float = field(default=0.0, repr=False)


def load_image(data: bytes) -> Image.Image:
    if len(data) > MAX_BYTES:
        raise ImageError("too_large")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # толық декодтау: бүлінген файл осында құлайды
    except UnidentifiedImageError:
        raise ImageError("not_image") from None
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise ImageError("bad_image") from None
    # Телефон фотосының бағытын EXIF бойынша түзеу
    return ImageOps.exif_transpose(img).convert("RGB")


def plant_fraction(img: Image.Image) -> float:
    """Өсімдікке ұқсас (сары-жасыл-қоңыр, қанық) пикселдер үлесі.

    Сұр қабырға, ақ қағаз, көк аспан ≈ 0. Ауру масақ (бозарған, сарғыш)
    және топырақ та санға кіреді — бұл тек «мүлде өсімдік емес» сүзгісі.
    """
    hsv = np.asarray(img.resize((96, 96)).convert("HSV"), dtype=np.float32)
    hue_deg = hsv[..., 0] * 360 / 255
    sat = hsv[..., 1] / 255
    val = hsv[..., 2] / 255
    mask = (sat > 0.12) & (val > 0.12) & (hue_deg >= 20) & (hue_deg <= 170)
    return float(mask.mean())


class Predictor:
    def __init__(self, model_dir: Path, min_conf: float = 0.5, min_plant: float = 0.08):
        model_dir = Path(model_dir)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        self.sess = ort.InferenceSession(str(model_dir / "eginai.onnx"), opts,
                                         providers=["CPUExecutionProvider"])
        self.w = np.load(model_dir / "classifier_w.npy")  # [C, 1280]
        self.labels: list[str] = json.loads((model_dir / "labels.json").read_text(encoding="utf-8"))
        self.min_conf, self.min_plant = min_conf, min_plant

    @staticmethod
    def _tensor(img: Image.Image) -> np.ndarray:
        x = np.asarray(img.resize((SIZE, SIZE), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
        x = (x - MEAN) / STD
        return x.transpose(2, 0, 1)[None]

    def _cam(self, feats: np.ndarray, cls_idx: int, img: Image.Image) -> tuple[str, float]:
        cam = np.maximum(np.tensordot(self.w[cls_idx], feats[0], axes=1), 0)  # [7, 7]
        cam = cam / cam.max() if cam.max() > 0 else cam
        # Көрсетуге арналған сурет: ұзын жағы 512 px
        view = img.copy()
        view.thumbnail((512, 512))
        heat = Image.fromarray((cam * 255).astype(np.uint8)).resize(view.size, Image.Resampling.BICUBIC)
        h = np.asarray(heat, dtype=np.float32) / 255.0
        affected = float((h > 0.5).mean() * 100)
        # Тұтас қызғылт-сары түсті мөлдірлікпен қабаттау (градиентсіз палитра)
        base = np.asarray(view, dtype=np.float32)
        color = np.array([255, 120, 0], dtype=np.float32)
        alpha = (np.clip((h - 0.25) / 0.75, 0, 1) * 0.6)[..., None]
        out = Image.fromarray((base * (1 - alpha) + color * alpha).astype(np.uint8))
        buf = io.BytesIO()
        out.save(buf, "JPEG", quality=82)
        return base64.b64encode(buf.getvalue()).decode(), round(affected, 1)

    def predict(self, data: bytes, with_cam: bool = True) -> Prediction:
        t0 = time.perf_counter()
        img = load_image(data)
        img.thumbnail((1024, 1024))  # үлкен суреттерді ерте кішірейту — жылдамдық
        logits, feats = self.sess.run(None, {"image": self._tensor(img)})
        z = logits[0] - logits[0].max()
        p = np.exp(z) / np.exp(z).sum()
        order = np.argsort(-p)[:3]
        top = [(self.labels[i], float(p[i])) for i in order]
        pf = plant_fraction(img)
        reason = "not_plant" if pf < self.min_plant else ("low_confidence" if top[0][1] < self.min_conf else None)
        pred = Prediction(top=top, unsure=reason is not None, reason=reason, plant_frac=pf)
        if with_cam and reason != "not_plant":
            pred.cam_jpeg_b64, pred.affected_pct = self._cam(feats, int(order[0]), img)
        pred.ms = round((time.perf_counter() - t0) * 1000, 1)
        return pred
