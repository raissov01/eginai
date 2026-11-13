"""Дауыс → мәтін: модельсіз мінез, ffmpeg түрлендіруі, (бар болса) нақты Vosk модель."""
import os
import subprocess
from pathlib import Path

import pytest

from bot import stt

ROOT = Path(__file__).resolve().parents[2]
KK = ROOT / "data" / "vosk" / "vosk-model-small-kz-0.42"


def test_unavailable_without_model(monkeypatch):
    monkeypatch.delenv("VOSK_MODEL_KK", raising=False)
    assert stt.available("kk") is False
    monkeypatch.setenv("VOSK_MODEL_KK", "/nonexistent")
    assert stt.available("kk") is False


def tone(seconds: float) -> bytes:
    return subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                           "-c:a", "libopus", "-f", "ogg", "pipe:1"], capture_output=True, check=True).stdout


def test_to_pcm_is_16k_mono_and_capped():
    pcm = stt.to_pcm(tone(2))
    assert abs(len(pcm) - 2 * 16000 * 2) < 16000 * 2 * 0.1      # ≈ 2 с × 16 кГц × 2 байт
    long = stt.to_pcm(tone(stt.MAX_SECONDS + 5))
    assert len(long) <= stt.MAX_SECONDS * 16000 * 2 + 3200


@pytest.mark.skipif(not KK.is_dir(), reason="Vosk kk моделі жүктелмеген")
def test_kk_model_runs_on_tone(monkeypatch):
    monkeypatch.setenv("VOSK_MODEL_KK", str(KK))
    assert stt.available("kk")
    assert isinstance(stt.transcribe(tone(1), "kk"), str)      # тон — сөз жоқ, бірақ қатесіз
