"""Офлайн белгілер анықтағышы (фото жоқта / модель сенімсіз болғанда) және сандық шектер."""
from app import advice


def test_key_covers_every_class_on_its_organs():
    key = advice.symptom_key("ru")
    where = {w["id"]: w for w in key}
    assert set(where) == {"leaf", "ear"}
    ids_leaf = {o["id"] for o in where["leaf"]["options"]}
    ids_ear = {o["id"] for o in where["ear"]["options"]}
    assert {"leaf_rust", "stripe_rust", "powdery_mildew", "healthy_leaf"} <= ids_leaf
    assert {"fusarium_head_blight", "glume_blotch", "healthy_ear"} <= ids_ear
    assert all(o["look"] and o["name"] for w in key for o in w["options"])


def test_key_lists_healthy_last_and_is_localized():
    kk, ru = advice.symptom_key("kk"), advice.symptom_key("ru")
    assert kk[0]["options"][-1]["id"].startswith("healthy")
    assert kk[0]["name"] != ru[0]["name"]


def test_threshold_numbers_in_advice():
    assert advice.advise("leaf_rust", "ru")["threshold_pct"] == [1, 5]
    assert advice.advise("healthy_leaf", "ru")["threshold_pct"] is None
    assert advice.advise("fusarium_head_blight", "kk")["threshold_pct"] is None  # тек профилактика


def test_symptom_key_endpoint(client, predictor):
    r = client.get("/api/symptom-key?lang=kk")
    assert r.status_code == 200 and len(r.json()) == 2


def test_advice_endpoint(client, predictor):
    r = client.get("/api/advice/stripe_rust?lang=ru")
    assert r.status_code == 200 and r.json()["threshold_pct"] == [0.5, 1]
    assert client.get("/api/advice/cancer").status_code == 404
