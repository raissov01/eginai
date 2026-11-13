"""Офлайн режим: браузерге модель файлы мен кеңестер бумасы."""


def test_offline_bundle(client, predictor):
    j = client.get("/api/offline/bundle").json()
    assert j["labels"] == predictor.labels
    assert len(j["classifier_w"]) == len(predictor.labels) and len(j["classifier_w"][0]) == 1280
    assert set(j["advice"]) == {"kk", "ru"} and j["advice"]["ru"]["leaf_rust"]["threshold_pct"] == [1, 5]
    assert len(j["key"]["kk"]) >= 2 and j["names"]["kk"]["leaf_rust"] == "Қоңыр тат"
    assert j["thresholds"] == {"min_conf": 0.5, "min_plant": 0.08, "min_texture": 6.0}
    assert j["version"] and j["temperature"] > 0


def test_offline_model_file(client, predictor):
    r = client.get("/api/offline/model.onnx")
    assert r.status_code == 200 and len(r.content) > 1_000_000
    assert r.headers["content-type"] == "application/octet-stream"
    assert "max-age" in r.headers.get("cache-control", "")
