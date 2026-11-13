"""Дауыстық хабарлама → мәтін (Vosk, Apache 2.0; CPU-да, интернетсіз).

Модельдер жолы ортадан: VOSK_MODEL_KK, VOSK_MODEL_RU (мысалы, vosk-model-small-kz-0.42,
vosk-model-small-ru-0.22). Модель не vosk жоқ болса — `available()` False, бот
«дауысты әзірге түсінбеймін» дейді. Telegram voice = OGG/Opus → ffmpeg → 16 кГц моно PCM.
"""
from __future__ import annotations

import json
import os
import subprocess
from functools import lru_cache

RATE = 16000
MAX_SECONDS = 60


def model_path(lang: str) -> str | None:
    p = os.environ.get(f"VOSK_MODEL_{lang.upper()}")
    return p if p and os.path.isdir(p) else None


def available(lang: str) -> bool:
    try:
        import vosk  # noqa: F401
    except ImportError:
        return False
    return model_path(lang) is not None


@lru_cache(maxsize=2)
def _model(path: str):
    import vosk
    vosk.SetLogLevel(-1)
    return vosk.Model(path)


def to_pcm(audio: bytes) -> bytes:
    """Кез келген аудио (ogg/opus, mp3, wav) → 16 кГц моно s16le, ең көбі 60 с."""
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-t", str(MAX_SECONDS),
                        "-ac", "1", "-ar", str(RATE), "-f", "s16le", "pipe:1"],
                       input=audio, capture_output=True, timeout=30, check=True)
    return r.stdout


def transcribe(audio: bytes, lang: str) -> str:
    import vosk
    path = model_path(lang)
    if not path:
        raise RuntimeError(f"no Vosk model for {lang}")
    rec = vosk.KaldiRecognizer(_model(path), RATE)
    pcm = to_pcm(audio)
    for i in range(0, len(pcm), 8000):
        rec.AcceptWaveform(pcm[i:i + 8000])
    return json.loads(rec.FinalResult()).get("text", "").strip()
