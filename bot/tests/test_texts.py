"""Бот жауабын пішімдеу: тілдер, сенімсіз жағдай, HTML қауіпсіздігі."""
from bot.texts import T, format_result

ADVICE = {"title": "Бурая <ржавчина>", "severity": "high", "timing": "в колошение",
          "actions": {"agro": "осмотр", "chemical": "триазолы"},
          "symptoms": "s", "prevention": "p", "similar": "x"}


def res(**kw):
    r = {"top": [{"id": "leaf_rust", "name": "Бурая", "prob": 0.93}, {"id": "stripe_rust", "name": "Жёлтая", "prob": 0.05}],
         "unsure": False, "reason": None, "affected_pct": 12.4, "advice": ADVICE}
    r.update(kw)
    return r


def test_same_keys_in_both_languages():
    assert T["kk"].keys() == T["ru"].keys()


def test_confident_result():
    main, adv = format_result(res(), "ru")
    assert "93%" in main and "12%" in main
    assert "&lt;ржавчина&gt;" in main  # HTML экрандалған
    assert "триазолы" in adv and "пестицидов РК" in adv


def test_not_plant_has_no_advice():
    main, adv = format_result(res(reason="not_plant", unsure=True, advice=None), "kk")
    assert adv is None and "жапырағы" in main


def test_unsure_lists_alternatives():
    main, _ = format_result(res(unsure=True, reason="low_confidence"), "kk")
    assert "Жёлтая 5%" in main


def test_healthy_skips_chemical():
    healthy = dict(ADVICE, severity="none", timing="—")
    _, adv = format_result(res(advice=healthy), "kk")
    assert "Химиялық" not in adv


def test_alert_message_escapes_and_truncates():
    from bot.texts import format_alert
    cases = [{"name": "Тат <b>", "distance_km": 3.2, "date": "2026-06-10"}] * 12
    msg = format_alert({"lang": "kk", "radius_km": 30.0, "cases": cases})
    assert "30 км" in msg and "&lt;b&gt;" in msg and "+2" in msg
    assert msg.count("3.2 км") == 10


def test_history_message():
    from bot.texts import format_history
    assert "бос" in format_history([], "kk")
    rows = [{"date": "2026-06-10T08:00", "field": "Алқап <3>", "name": "Қоңыр тат", "confidence": 0.91}]
    msg = format_history(rows, "kk")
    assert "2026-06-10 · Алқап &lt;3&gt; — Қоңыр тат (91%)" in msg


def test_reminder_message():
    from bot.texts import format_reminder
    m = format_reminder({"lang": "ru", "name": "Бурая <x>", "field": "Поле 1"})
    assert "Поле 1: " in m and "&lt;x&gt;" in m and "7 дней" in m
    assert "«Қоңыр тат»" in format_reminder({"lang": "kk", "name": "Қоңыр тат", "field": None})
