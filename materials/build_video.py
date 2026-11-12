"""Демо-видео жинау: титрлі карталар + телефон экранының жазбасы → 1920×1080 MP4.

    python3 materials/build_video.py
Кіріс: materials/video/raw/marks.json (capture.py жазады), materials/figures/*.png
Шығыс: materials/EginAI_Demo.mp4
"""
from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "materials" / "figures"
OUT = ROOT / "materials" / "video" / "build"
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1920, 1080
INK, WHEAT, FIELD, WHITE, MUTED, LEAF = (27, 42, 31), (232, 185, 49), (238, 242, 236), (255, 255, 255), (201, 211, 204), (47, 107, 58)
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
M = json.loads((ROOT / "ml" / "metrics.json").read_text())


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else REG, size)


def text(d, xy, s, size, color=INK, bold=False, width=None, gap=1.3):
    """Мәтінді жолдарға бөліп жазу; соңғы y-ті қайтарады."""
    f = font(size, bold)
    lines = []
    for para in s.split("\n"):
        lines += textwrap.wrap(para, width) if width else [para]
    x, y = xy
    for ln in lines:
        d.text((x, y), ln, font=f, fill=color)
        y += int(size * gap)
    return y


def logo(img, x, y, s):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x, y, x + s, y + s), radius=s // 5, fill=INK, outline=WHEAT, width=2)
    k = s / 32
    d.line((x + 16 * k, y + 9 * k, x + 16 * k, y + 27 * k), fill=WHEAT, width=max(2, int(2 * k)))
    for yy in (11, 15, 19):
        d.ellipse((x + 9.6 * k, y + (yy - 1.8) * k, x + 15.6 * k, y + (yy + 1.8) * k), fill=WHEAT)
        d.ellipse((x + 16.4 * k, y + (yy - 1.8) * k, x + 22.4 * k, y + (yy + 1.8) * k), fill=WHEAT)
    d.ellipse((x + 14.2 * k, y + 4 * k, x + 17.8 * k, y + 10 * k), fill=WHEAT)


def card(name, bg, draw_fn):
    img = Image.new("RGB", (W, H), bg)
    draw_fn(img, ImageDraw.Draw(img))
    p = OUT / f"{name}.png"
    img.save(p)
    return p


def paste_fit(img, path, box):
    x0, y0, x1, y1 = box
    im = Image.open(path).convert("RGB")
    k = min((x1 - x0) / im.width, (y1 - y0) / im.height)
    im = im.resize((int(im.width * k), int(im.height * k)), Image.Resampling.LANCZOS)
    img.paste(im, (x0 + (x1 - x0 - im.width) // 2, y0 + (y1 - y0 - im.height) // 2))


# ---------- Карталар ----------
def c_title(img, d):
    logo(img, 140, 160, 120)
    text(d, (140, 340), "EginAI", 150, WHITE, True)
    text(d, (140, 540), "Бидай ауруларын фото бойынша ерте анықтау", 56, WHITE)
    text(d, (140, 640), "Фото → диагноз → қазақша не орысша кеңес → аурулар картасы", 36, MUTED)
    text(d, (140, 900), "«AI autumn» 2026  |  С. Сейфуллин атындағы ҚАТЗУ", 32, MUTED)


def c_problem(img, d):
    text(d, (140, 130), "Мәселе", 72, INK, True)
    text(d, (140, 260), "40%-ға дейін", 110, (181, 71, 27), True)
    text(d, (140, 400), "әлемдік егін зиянкестер мен аурулардан жоғалады (ФАО)", 40, INK)
    y = 540
    for s in ["Шалғай ауылдарда агроном жетпейді — ауру кеш байқалады.",
              "Қате диагноз: өнім жоғалады, фунгицид «қалай болса да» шашылады.",
              "Бар қолданбаларда қазақ тілі жоқ, жарнама көп, ауру картасы жоқ."]:
        d.ellipse((140, y + 14, 164, y + 38), fill=WHEAT, outline=INK, width=2)
        y = text(d, (190, y), s, 40, INK, width=70) + 30


def c_results(img, d):
    text(d, (120, 110), "Нәтиже: модель көрмеген 580 сурет", 60, INK, True)
    for i, (n, l) in enumerate([(f"{M['accuracy']*100:.1f}%".replace('.', ','), "дәлдік"),
                                (f"{M['macro_f1']*100:.1f}%".replace('.', ','), "macro-F1"),
                                ("98,4%", "сенімді жауаптардағы дәлдік"),
                                (f"{round(M['cpu_ms_per_image_median'])} мс", "бір фото, кәдімгі CPU")]):
        y = 260 + i * 185
        text(d, (120, y), n, 84, LEAF if i == 0 else INK, True)
        text(d, (120, y + 100), l, 32, (85, 98, 90))
    paste_fit(img, FIG / "confusion.png", (900, 220, 1820, 1020))


def c_cam(img, d):
    text(d, (120, 110), "Модель қайда қарады: CAM жылу картасы", 60, INK, True)
    paste_fit(img, FIG / "cam_examples2.png", (120, 230, 1800, 900))
    text(d, (120, 940), "Сенім төмен болса — «қайта түсіріңіз» және 3 ықтимал нұсқа. Ойдан диагноз жоқ.", 36, INK)


def c_arch(img, d):
    paste_fit(img, FIG / "architecture.png", (100, 60, 1820, 1020))


def c_launch(img, d):
    text(d, (140, 130), "Жюри компьютерінде бір командамен", 64, WHITE, True)
    d.rounded_rectangle((140, 300, 1780, 420), radius=18, fill=(15, 25, 18), outline=WHEAT, width=2)
    d.text((190, 335), "docker compose up   →   http://localhost:8000", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 52), fill=WHEAT)
    y = 520
    for s in ["Фото сақталмайды; картаға тек келісіммен, ~1 км дәлдікпен.",
              "Кілт қажет емес: кеңестер білім базасынан, LLM — қалауы бойынша.",
              "Код — MIT; датасет CC-BY-4.0; 52 автотест."]:
        d.ellipse((140, y + 14, 164, y + 38), fill=WHEAT)
        y = text(d, (190, y), s, 40, WHITE, width=70) + 34


def c_team(img, d):
    logo(img, 140, 120, 90)
    text(d, (270, 130), "EginAI командасы", 64, WHITE, True)
    team = [("Әбдімүтәлі Бекназар", "капитан, архитектура, қорғау"), ("Әбдіқадыр Ернұр", "ML: датасет, үйрету, бағалау"),
            ("Есен Арман", "backend, дерекқор, Telegram-бот"), ("Жақсығұл Рамазан", "frontend, UI/UX, карта")]
    for i, (n, r) in enumerate(team):
        x, y = 140 + (i % 2) * 860, 360 + (i // 2) * 210
        text(d, (x, y), n, 46, WHEAT, True)
        text(d, (x, y + 64), r, 34, WHITE)
    text(d, (140, 900), "Ғылыми жетекші: Таберхан Роман      Рақмет!", 36, MUTED)


CAPTIONS = {
    "start": "Фермер EginAI-ды ашады: тіркелусіз, браузерде немесе Telegram-да.",
    "upload_rust": "Ауру жапырақты суретке түсіреді.",
    "result_rust": "Бірнеше секундта: қоңыр тат, сенімділік, қауіп деңгейі және зақымданған аудан.",
    "cam_toggle": "«Белгілер аймағы»: модель шешімді қай жерге қарап қабылдағанын көрсетеді.",
    "advice": "Не істеу керек: агро- және химиялық шаралар, мерзімі, алдын алу. Бәрі қазақша.",
    "ask": "Еркін сұрақ қоюға болады: жауап білім базасынан алынады, диагноз ескеріледі.",
    "consent": "Келісім берілсе, жағдай картаға түседі. Фото сақталмайды, орын ~1 км дәлдікпен.",
    "lang_ru": "Интерфейс орыс тілінде де бар. Сары тат анықталды.",
    "not_plant": "Өсімдік емес фото: ойдан диагноз жоқ, «қайта түсіріңіз» деп жауап береді.",
    "map": "Аурулар ошақтарының картасы: ауру мен кезең бойынша сүзгі (көрсетілімге арналған демо-деректер).",
    "about": "«Жоба туралы»: модель сапасы, шектеулер, деректер саясаты.",
}


def demo_frames(marks):
    """Демо бөлігінің фондары: сол жақта телефон орны, оң жақта қадам титрі."""
    keys = [("start", 0.0)] + [(k, t) for t, k in marks if k in CAPTIONS and k not in ("home",)]
    # lang_ru мен result_stripe бір титрге біріктіріледі
    end = dict((k, t) for t, k in marks)["end"]
    segs = []
    for i, (k, t) in enumerate(keys):
        t2 = keys[i + 1][1] if i + 1 < len(keys) else end
        n = i + 1

        def draw(img, d, k=k, n=n):
            d.rounded_rectangle((300, 50, 300 + 470, 50 + 980), radius=26, fill=(15, 25, 18), outline=(70, 90, 75), width=2)
            logo(img, 900, 120, 70)
            text(d, (995, 135), "EginAI — демо", 40, WHITE, True)
            d.ellipse((900, 330, 980, 410), fill=WHEAT)
            f = font(40, True)
            tw = d.textlength(str(n), font=f)
            d.text((940 - tw / 2, 345), str(n), font=f, fill=INK)
            text(d, (900, 450), CAPTIONS[k], 46, WHITE, width=34, gap=1.35)
        segs.append((card(f"demo_{n:02d}", INK, draw), round(t2 - t, 2)))
    return segs


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def still(png, dur, name):
    out = OUT / f"{name}.mp4"
    run(["ffmpeg", "-y", "-loop", "1", "-t", str(dur), "-i", str(png), "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=48000:cl=stereo",
         "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-threads", "4", "-crf", "20",
         "-c:a", "aac", "-shortest", str(out)])
    return out


def main():
    mk = json.loads((ROOT / "materials" / "video" / "raw" / "marks.json").read_text())
    marks = [tuple(m) for m in mk["marks"]]
    segs = demo_frames(marks)
    end = dict((k, t) for t, k in marks)["end"]
    # 1) Телефон жазбасын тұрақты 30 fps-ке келтіру (Playwright webm уақыт белгілері тұрақсыз)
    phone = OUT / "phone.mp4"
    run(["ffmpeg", "-y", "-i", mk["video"], "-vf", "fps=30,scale=446:930,format=yuv420p", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "20", str(phone)])
    # 2) Әр титр фонын жеке сегмент етіп кодтау, сосын біріктіру (бір үлкен concat жадты бітіреді)
    bgs = [still(pth, dur, f"bg_{i:02d}") for i, (pth, dur) in enumerate(segs)]
    (OUT / "bg.txt").write_text("".join(f"file '{b}'\n" for b in bgs))
    bg = OUT / "bg.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "bg.txt"), "-c", "copy", str(bg)])
    # 3) Фон + телефон
    demo = OUT / "demo.mp4"
    run(["ffmpeg", "-y", "-i", str(bg), "-i", str(phone), "-filter_complex",
         "[0:v][1:v]overlay=312:75:eof_action=repeat,format=yuv420p[v]", "-map", "[v]", "-map", "0:a",
         "-t", str(end), "-c:v", "libx264", "-preset", "veryfast", "-threads", "4", "-crf", "20", "-c:a", "aac", str(demo)])
    parts = [
        still(card("01_title", INK, c_title), 6, "p01"),
        still(card("02_problem", WHITE, c_problem), 9, "p02"),
        demo,
        still(card("03_results", WHITE, c_results), 10, "p03"),
        still(card("04_cam", WHITE, c_cam), 8, "p04"),
        still(card("05_arch", WHITE, c_arch), 9, "p05"),
        still(card("06_launch", INK, c_launch), 8, "p06"),
        still(card("07_team", INK, c_team), 6, "p07"),
    ]
    cl = OUT / "parts.txt"
    cl.write_text("".join(f"file '{p}'\n" for p in parts))
    final = ROOT / "materials" / "EginAI_Demo.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(cl), "-c:v", "libx264", "-preset", "veryfast", "-threads", "4", "-crf", "21",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(final)])
    print("→", final)


if __name__ == "__main__":
    main()
