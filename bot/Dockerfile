FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# ffmpeg — Telegram дауысын (OGG/Opus) PCM-ге түрлендіру; curl+unzip — Vosk модельдері
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl unzip ca-certificates \
 && rm -rf /var/lib/apt/lists/*
# Шағын Vosk модельдері (Apache 2.0): kk ~60 МБ, ru ~46 МБ. VOSK=0 — дауыссыз жинау
ARG VOSK=1
RUN if [ "$VOSK" = "1" ]; then mkdir -p /models && cd /models \
 && curl -fsSL -o kz.zip https://alphacephei.com/vosk/models/vosk-model-small-kz-0.42.zip && unzip -q kz.zip && rm kz.zip \
 && curl -fsSL -o ru.zip https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip && unzip -q ru.zip && rm ru.zip; fi
ENV VOSK_MODEL_KK=/models/vosk-model-small-kz-0.42 VOSK_MODEL_RU=/models/vosk-model-small-ru-0.22
COPY bot/requirements.txt bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt
COPY bot bot
RUN useradd -r -u 10001 eginai
USER eginai
CMD ["python", "-m", "bot.main"]
