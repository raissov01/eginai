"""EginAI демо-видеосына фондық музыка — толық синтезделген (авторлық құқық мәселесі жоқ).

Жылы, тыныш поп-эмбиент, 100 BPM, F-dur (Fmaj7 – Am7 – B♭maj7 – C).
Құрылым видеоға сәйкес: кіріспе/мәселе — тек аккордтар; демо — жеңіл ритм;
нәтижелер — толығырақ; команда — бәсеңдеу.

    python3 materials/music.py <ұзақтығы_сек> <демо_басы> <демо_соңы>
"""
import sys
import wave

import numpy as np

SR = 44100
END, DEMO_A, DEMO_B = (float(x) for x in sys.argv[1:4])
N = int((END + 0.5) * SR)
rng = np.random.default_rng(7)
mix = np.zeros((N, 2))
BEAT = 0.6
BAR = 4 * BEAT
PROG = [(41, [65, 69, 72, 76]), (45, [64, 69, 72, 76]), (46, [65, 70, 74, 77]), (48, [64, 67, 72, 76])]
midi = lambda m: 440 * 2 ** ((m - 69) / 12)  # noqa: E731


def tt(d):
    return np.arange(int(d * SR)) / SR


def put(t, sig, pan=0.0, gain=1.0):
    i = int(round(t * SR))
    if i >= N:
        return
    b = min(i + len(sig), N)
    s = sig[: b - i] * gain
    mix[i:b, 0] += s * (1 - max(pan, 0))
    mix[i:b, 1] += s * (1 + min(pan, 0))


def epiano(m, d, g):
    t = tt(d)
    f = midi(m)
    mod = np.sin(2 * np.pi * f * t) * 1.1 * np.exp(-t * 3)
    env = np.minimum(t / 0.01, 1) * np.exp(-t * 1.1) * np.minimum((d - t) / 0.08, 1)
    return np.sin(2 * np.pi * f * t + mod) * env * g


def pad(m, d, g):
    # баяу кіретін жұмсақ пад: сәл ауытқыған екі синус
    t = tt(d)
    f = midi(m)
    env = np.minimum(t / 0.8, 1) * np.minimum((d - t) / 0.8, 1)
    return (np.sin(2 * np.pi * f * t) + np.sin(2 * np.pi * f * 1.003 * t)) * 0.5 * env * g


def bass(m, d, g):
    t = tt(d)
    f = midi(m)
    env = np.minimum(t / 0.01, 1) * np.minimum((d - t) / 0.05, 1) * np.exp(-t * 0.8)
    return (np.sin(2 * np.pi * f * t) + 0.2 * np.sin(4 * np.pi * f * t)) * env * g


def kick(g):
    t = tt(0.3)
    return np.sin(2 * np.pi * np.cumsum(48 + 80 * np.exp(-t * 35)) / SR) * np.exp(-t * 10) * g


def shaker(g):
    t = tt(0.05)
    return np.diff(np.diff(rng.standard_normal(len(t) + 2))) * np.sin(np.pi * t / 0.05) * g


def bell(m, g):
    t = tt(0.9)
    f = midi(m)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 6)) * np.exp(-t * 4) * g


MEL = [77, 76, 72, 74, 72, 69, 72, 74]  # қарапайым әуен, нәтижелер бөлігінде
bar = 0
t = 0.0
while t < END:
    root, ch = PROG[bar % 4]
    demo = DEMO_A <= t < DEMO_B
    outro = t >= DEMO_B
    for m in ch:
        put(t, pad(m - 12, BAR + 0.6, 0.022), pan=0.0)
    put(t, epiano(ch[0], BAR, 0.035), pan=-0.2)
    put(t + 2 * BEAT, epiano(ch[2], 2 * BEAT, 0.03), pan=0.2)
    if t >= 6:  # бас — титулдан кейін
        put(t, bass(root - 12, 2 * BEAT, 0.16))
        put(t + 2.5 * BEAT, bass(root - 12, 1.5 * BEAT, 0.12))
    if demo or outro:
        for k in range(4):
            put(t + k * BEAT, kick(0.22 if k in (0, 2) else 0.12))
            for h in (0.5, 0.75) if demo else (0.5,):
                put(t + (k + h) * BEAT, shaker(0.03), pan=0.3)
    if outro:
        put(t, bell(MEL[(2 * bar) % 8], 0.04), pan=0.25)
        put(t + 2 * BEAT, bell(MEL[(2 * bar + 1) % 8], 0.035), pan=-0.25)
    t += BAR
    bar += 1

# Финал аккорды
put(END - 4.0, sum(pad(m, 4.0, 0.03) for m in [53, 65, 69, 72]))

# Жұмсақ компрессия + кіру/шығу
mix = np.tanh(mix * 1.6) / 1.6
fade_in = np.minimum(np.arange(N) / (1.5 * SR), 1)
fade_out = np.clip((END - np.arange(N) / SR) / 3.0, 0, 1)
mix *= (fade_in * fade_out)[:, None]
mix = mix / np.abs(mix).max() * 0.6
pcm = (mix * 32767).astype("<i2")
with wave.open("materials/video/build/music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("music.wav", END, "s")
