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
