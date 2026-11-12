"""Скриншоттар мен демо-видеоның шикі жазбасы (Playwright, мобильді экран).

    python materials/capture.py http://localhost:8000

Шығады: materials/figures/ui-*.png, materials/video/raw/*.webm
Картадағы нүктелер — көрсетілім үшін `source=demo` деп белгіленген демо-деректер.
"""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "materials" / "figures"
VID = ROOT / "materials" / "video" / "raw"
S = ROOT / "samples"
FIG.mkdir(parents=True, exist_ok=True)
VID.mkdir(parents=True, exist_ok=True)


def seed_demo_points():
    """Солтүстік Қазақстандағы көрсетілім нүктелері (source=demo)."""
    rnd = random.Random(7)
    centers = [(51.2, 71.4), (53.2, 63.6), (54.9, 69.1), (52.3, 76.9), (50.3, 72.9), (51.7, 68.4)]
    diseases = ["leaf_rust"] * 5 + ["stripe_rust", "powdery_mildew", "glume_blotch", "fusarium_head_blight"]
    with httpx.Client(base_url=BASE) as c:
        if len(c.get("/api/map?days=90").json()["features"]) >= 15:
            return
        for _ in range(22):
            la, lo = rnd.choice(centers)
            c.post("/api/cases", json={"disease": rnd.choice(diseases), "confidence": round(rnd.uniform(.7, .99), 2),
                                       "lat": la + rnd.uniform(-.6, .6), "lon": lo + rnd.uniform(-.9, .9),
                                       "consent": True, "source": "demo"})


SLOW = 1.6  # видео үшін баяулату
MARKS: list[tuple[float, str]] = []
T0 = [0.0]


def mark(label):
    """Видеодағы оқиға уақыты (титрлер үшін)."""
    MARKS.append((round(time.monotonic() - T0[0], 2), label))


def pause(page, s):
    page.wait_for_timeout(int(s * 1000 * SLOW))


def main():
    seed_demo_points()
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 824, "height": 1720}, device_scale_factor=1, locale="kk-KZ",
                            record_video_dir=str(VID), record_video_size={"width": 824, "height": 1720},
                            geolocation={"latitude": 51.62, "longitude": 69.95}, permissions=["geolocation"])
        # 412 px телефон макеті 2× анықтықпен: CSS zoom (видео жазбасы DPR-ді ескермейді)
        ctx.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');s.textContent='html{zoom:2}';document.head.appendChild(s)})")
        page = ctx.new_page()
        T0[0] = time.monotonic()
        page.goto(BASE + "/#diagnose")
        page.evaluate("localStorage.setItem('lang','kk')")
        page.reload()
        pause(page, 2.5)
        page.screenshot(path=FIG / "ui-1-home-kk.png")
        mark("home")
        pause(page, 1.5)

        # 1) Қоңыр тат
        mark("upload_rust")
        page.locator("input[type=file]").nth(1).set_input_files(str(next(S.glob("leaf_rust_00048_0.jpg"))))
        page.wait_for_selector(".diag h1")
        pause(page, 2.5)
        page.screenshot(path=FIG / "ui-2-result-kk.png")
        mark("result_rust")
        pause(page, 1.5)
        mark("cam_toggle")
        page.get_by_role("button", name="Түпнұсқа").click()
        pause(page, 1.5)
        page.get_by_role("button", name="Белгілер аймағы").click()
        pause(page, 1.5)
        mark("advice")
        for _ in range(6):
            page.mouse.wheel(0, 520)
            pause(page, .7)
        page.screenshot(path=FIG / "ui-3-advice-kk.png")
        # Сұрақ қою
        mark("ask")
        page.fill("#ask", "Қай кезде өңдеген дұрыс?")
        pause(page, .8)
        page.get_by_role("button", name="Сұрау").click()
        page.wait_for_selector(".answer")
        page.locator(".answer").scroll_into_view_if_needed()
        pause(page, 3)
        page.screenshot(path=FIG / "ui-4-ask-kk.png")
        # Картаға белгілеу
        mark("consent")
        page.locator(".check input").scroll_into_view_if_needed()
        page.locator(".check input").check()
        pause(page, .8)
        page.locator(".panel .btn-primary").first.click()
        page.wait_for_selector(".notice.ok")
        pause(page, 2)

        # 2) Орысша, сары тат
        page.evaluate("window.scrollTo(0,0)")
        mark("lang_ru")
        page.get_by_role("button", name="Рус").click()
        pause(page, 1)
        page.get_by_role("button", name="Новое фото").click() if page.get_by_role("button", name="Новое фото").count() else None
        pause(page, 1)
        page.locator("input[type=file]").nth(1).set_input_files(str(S / "stripe_rust_00273_0.jpg"))
        page.wait_for_selector(".diag h1")
        pause(page, 3)
        page.screenshot(path=FIG / "ui-5-result-ru.png")
        mark("result_stripe")

        # 3) Өсімдік емес фото — адал жауап
        page.evaluate("window.scrollTo(0,0)")
        page.get_by_role("button", name="Новое фото").last.click()
        pause(page, .8)
        mark("not_plant")
        page.locator("input[type=file]").nth(1).set_input_files(str(ROOT / "materials" / "figures" / "not_plant.jpg"))
        page.wait_for_selector(".notice.warn")
        pause(page, 3)
        page.screenshot(path=FIG / "ui-6-unsure-ru.png")

        # 4) Карта
        mark("map")
        page.goto(BASE + "/#map")
        pause(page, 3.5)
        page.screenshot(path=FIG / "ui-7-map-ru.png")
        page.get_by_role("button", name="Бурая (листовая) ржавчина", exact=False).click()
        pause(page, 2.5)
        page.get_by_role("button", name="Все", exact=False).click()
        pause(page, 1.5)

        # 5) Жоба туралы
        mark("about")
        page.goto(BASE + "/#about")
        pause(page, 2.5)
        page.screenshot(path=FIG / "ui-8-about-ru.png", full_page=True)
        for _ in range(4):
            page.mouse.wheel(0, 600)
            pause(page, .8)
        mark("end")
        ctx.close()
        b.close()
    vids = sorted(VID.glob("*.webm"), key=lambda f: f.stat().st_mtime)
    import json
    (VID / "marks.json").write_text(json.dumps({"video": str(vids[-1]), "marks": MARKS}, ensure_ascii=False, indent=1))
    print("video:", vids[-1] if vids else None, MARKS)


if __name__ == "__main__":
    main()
