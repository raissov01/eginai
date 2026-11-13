"""«Диагноз дұрыс па?» кері байланысы және нақты өрістегі дәлдік статистикасы."""


def fb(**kw):
    base = {"predicted": "leaf_rust", "confidence": 0.9, "correct": True, "source": "web"}
    base.update(kw)
    return base


def test_feedback_accuracy_stats(client, predictor):
    for ok in (True, True, True, False):
        assert client.post("/api/feedback", json=fb(correct=ok,
                           actual=None if ok else "stripe_rust")).status_code == 201
    assert client.post("/api/feedback", json=fb(predicted="powdery_mildew", correct=True)).status_code == 201
    s = client.get("/api/feedback/stats?lang=ru").json()
    assert s["n"] == 5 and s["accuracy"] == 0.8
    per = {x["id"]: x for x in s["per_class"]}
    assert per["leaf_rust"]["n"] == 4 and per["leaf_rust"]["accuracy"] == 0.75
    assert per["leaf_rust"]["name"] == "Бурая (листовая) ржавчина"
    assert s["confusions"] == [{"predicted": "leaf_rust", "actual": "stripe_rust", "n": 1}]


def test_empty_stats(client, predictor):
    s = client.get("/api/feedback/stats").json()
    assert s["n"] == 0 and s["accuracy"] is None and s["per_class"] == []


def test_wrong_without_actual_is_allowed(client, predictor):
    # Фермер дұрыс ауруды білмеуі мүмкін: тек «қате» дейді
    assert client.post("/api/feedback", json=fb(correct=False)).status_code == 201


def test_feedback_validation(client, predictor):
    assert client.post("/api/feedback", json=fb(predicted="cancer")).status_code == 422
    assert client.post("/api/feedback", json=fb(correct=False, actual="cancer")).status_code == 422
    assert client.post("/api/feedback", json=fb(correct=True, actual="stripe_rust")).status_code == 422
    assert client.post("/api/feedback", json=fb(confidence=1.5)).status_code == 422
