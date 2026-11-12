"""Дрон модулінің анимациясы (GIF): алқапты «ары-бері» шолу → ошақтарды табу →
25 м-ден нақтылау → тәуекел картасы. Слайдқа арналған, 960×540, тегіс стиль.

    python3 materials/drone_anim.py   →  materials/figures/drone_flight.gif
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "figures" / "drone_flight.gif"
W, H, FPS = 960, 540, 12
INK, WHEAT, RUST, LEAF = (27, 42, 31), (232, 185, 49), (181, 71, 27), (47, 107, 58)
G1, G2, PALE, WHITE = (120, 160, 80), (104, 146, 68), (201, 211, 204), (255, 255, 255)
FX0, FY0, FX1, FY1 = 30, 30, 650, 510            # алқап
LANE = 64                                        # «ары-бері» жолақтар арасы (100 м ұшу)
FP_W, FP_H = 92, 76                              # кадр қамтуы (100 м)
HOT = [(170, 120, 26), (455, 175, 30), (300, 300, 22), (540, 380, 28), (120, 420, 20)]  # ошақтар (x, y, r)
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f_b = ImageFont.truetype(BOLD, 22)
f_r = ImageFont.truetype(REG, 17)
f_big = ImageFont.truetype(BOLD, 34)


def lanes():
    """Жылан тәрізді маршрут нүктелері."""
    # Жолақтар саны кадр биіктігі мен қабаттасу бойынша — алқап шетіне дейін толық жабылады
    top, bot = FY0 + FP_H / 2, FY1 - FP_H / 2
    n = math.ceil((bot - top) / LANE) + 1
    pts, left = [], True
    for k in range(n):
        y = top + (bot - top) * k / (n - 1)
        xa, xb = (FX0 + FP_W / 2, FX1 - FP_W / 2) if left else (FX1 - FP_W / 2, FX0 + FP_W / 2)
        pts += [(xa, y), (xb, y)]
        left = not left
    return pts


def path_point(pts, s):
    """Маршрут бойындағы s ∈ [0,1] нүктесі."""
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    lens = [math.dist(a, b) for a, b in segs]
    d = s * sum(lens)
    for (a, b), L in zip(segs, lens):
        if d <= L:
            t = d / L if L else 0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        d -= L
    return pts[-1]


def field(img):
    d = ImageDraw.Draw(img)
    for i, x in enumerate(range(FX0, FX1, 14)):
        d.rectangle((x, FY0, min(x + 13, FX1), FY1), fill=G1 if i % 2 else G2)
    d.rectangle((FX0, FY0, FX1, FY1), outline=INK, width=3)


def drone(d, x, y, k, phase):
    """Жоғарыдан көрінетін квадрокоптер; пропеллер сызығы айналады."""
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        cx, cy = x + dx * 15 * k, y + dy * 15 * k
        d.line((x, y, cx, cy), fill=INK, width=int(4 * k))
        d.ellipse((cx - 10 * k, cy - 10 * k, cx + 10 * k, cy + 10 * k), outline=INK, width=2, fill=PALE)
        a = phase + (dx + dy)
        d.line((cx - 9 * k * math.cos(a), cy - 9 * k * math.sin(a), cx + 9 * k * math.cos(a), cy + 9 * k * math.sin(a)), fill=INK, width=2)
    d.rounded_rectangle((x - 9 * k, y - 9 * k, x + 9 * k, y + 9 * k), radius=4, fill=WHEAT, outline=INK, width=2)


def panel(d, lines, big=None):
    d.rectangle((670, 30, 930, 510), fill=INK)
    y = 52
    for kind, text in lines:
        font, col = (f_b, WHITE) if kind == "h" else (f_r, PALE) if kind == "p" else (f_b, WHEAT)
        d.text((690, y), text, font=font, fill=col)
        y += 34 if kind == "h" else 28
    if big:  # негізгі сан — соңғы жолдың астында
        d.text((690, y + 4), big, font=f_big, fill=WHEAT)
        d.text((690, y + 46), "фунгицид үнемі", font=f_r, fill=PALE)


def main():
    pts = lanes()
    frames = []
    N1, N2, N3 = 8 * FPS, 4 * FPS, 4 * FPS       # шолу, нақтылау, карта
    scanned = Image.new("L", (W, H), 0)          # шолынған аймақ маскасы
    found = []
    for i in range(N1 + N2 + N3):
        img = Image.new("RGB", (W, H), WHITE)
        field(img)
        d = ImageDraw.Draw(img, "RGBA")
        if i < N1:                                # 1) шолу ұшуы, 100 м
            x, y = path_point(pts, i / (N1 - 1))
            ImageDraw.Draw(scanned).rectangle((x - FP_W / 2, y - FP_H / 2, x + FP_W / 2, y + FP_H / 2), fill=255)
            for h in HOT:
                if h not in found and abs(h[0] - x) < FP_W / 2 and abs(h[1] - y) < FP_H / 2:
                    found.append(h)
            overlay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
            overlay.putalpha(scanned.point(lambda v: 70 if v else 0))
            img.paste(Image.new("RGB", (W, H), WHITE), (0, 0), overlay.getchannel("A"))
            d = ImageDraw.Draw(img, "RGBA")
            for (hx, hy, r) in found:
                d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=RUST + (200,))
                d.rectangle((hx - r - 6, hy - r - 6, hx + r + 6, hy + r + 6), outline=RUST, width=3)
            for a, b in zip(pts, pts[1:]):        # маршрут сызығы
                d.line((a, b), fill=INK + (90,), width=1)
            d.rectangle((x - FP_W / 2, y - FP_H / 2, x + FP_W / 2, y + FP_H / 2), outline=WHEAT, width=3, fill=(255, 255, 255, 40))
            drone(d, x, y, 1.0, i * 0.9)
            pct = int(min(100, (i + 1) / N1 * 100))
            panel(d, [("h", "1. Шолу ұшуы"), ("p", "Биіктік: 100 м"), ("p", "Кадр: ~2,8 см/пиксель"),
                      ("p", "Маршрут: ары-бері"), ("p", "Қабаттасу: 70%"), ("h", ""),
                      ("h", f"Шолынды: {pct}%"), ("y", f"Ошақ: {len(found)}")])
        elif i < N1 + N2:                         # 2) нақтылау ұшуы, 25 м
            j = i - N1
            k = min(len(found) - 1, j * len(found) // N2)
            hx, hy, r = found[k]
            for n, (ax, ay, ar) in enumerate(found):
                col = LEAF if n < k else RUST
                d.ellipse((ax - ar, ay - ar, ax + ar, ay + ar), fill=RUST + (200,))
                d.rectangle((ax - ar - 6, ay - ar - 6, ax + ar + 6, ay + ar + 6), outline=col, width=3)
            d.rectangle((hx - 32, hy - 26, hx + 32, hy + 26), outline=WHITE, width=3)
            drone(d, hx + 34, hy - 30, 0.8, i * 0.9)
            panel(d, [("h", "2. Нақтылау"), ("p", "Тек ошақтар үстінде"), ("p", "Биіктік: 25 м"),
                      ("p", "Кадр: ~0,7 см/пиксель"), ("p", "EginAI моделі →"), ("p", "ауру түрі + дәрежесі"),
                      ("h", ""), ("y", f"Тексерілді: {k + 1}/{len(found)}")])
        else:                                     # 3) тәуекел картасы + есеп
            cell = 40
            for gx in range(FX0, FX1, cell):
                for gy in range(FY0, FY1, cell):
                    cx, cy = gx + cell / 2, gy + cell / 2
                    dmin = min(math.dist((cx, cy), (hx, hy)) - r for hx, hy, r in found)
                    if dmin < 8:
                        d.rectangle((gx, gy, gx + cell, gy + cell), fill=RUST + (150,), outline=INK + (60,))
                    elif dmin < 40:
                        d.rectangle((gx, gy, gx + cell, gy + cell), fill=WHEAT + (130,), outline=INK + (60,))
            panel(d, [("h", "3. Есеп (500 га)"), ("p", "Өнімділік: 21,1 ц/га"), ("p", "Ошақ: 30 га (6%)"),
                      ("p", "Шашырату: 45 га"), ("p", "Шығын, өңделмесе:"), ("p", "  9,5 т ≈ 855 мың ₸"), ("h", ""),
                      ("y", "Үнем: 4,55 млн ₸")], big="91%")
        frames.append(img.convert("P", palette=Image.Palette.ADAPTIVE, colors=64))
    frames += [frames[-1]] * (2 * FPS)            # соңғы кадрда кідіріс
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0, optimize=True)
    print(OUT, OUT.stat().st_size // 1024, "KB", len(frames), "frames")


if __name__ == "__main__":
    main()
