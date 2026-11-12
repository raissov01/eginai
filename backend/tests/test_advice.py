"""Білім базасының толықтығы және іздеу."""
import json

import pytest

from app import advice
from conftest import MODEL_DIR

LABELS = ["fusarium_head_blight", "glume_blotch", "healthy_ear", "healthy_leaf",
          "leaf_rust", "powdery_mildew", "stripe_rust"]


def test_every_model_class_has_kb_entry():
    labels_file = MODEL_DIR / "labels.json"
    labels = json.loads(labels_file.read_text()) if labels_file.exists() else LABELS
    for cid in labels:
        advice.disease(cid)  # KeyError болмауы керек


@pytest.mark.parametrize("cid", LABELS)
@pytest.mark.parametrize("lang", ["kk", "ru"])
def test_advice_has_all_fields_in_both_languages(cid, lang):
    a = advice.advise(cid, lang)
    for k in ("title", "symptoms", "prevention", "similar"):
        assert a[k] and a[k] != "—", (cid, lang, k)
    assert a["actions"]["agro"] and a["actions"]["chemical"]
    assert a["sources"]


def test_kk_and_ru_texts_differ():
    a, b = advice.advise("leaf_rust", "kk"), advice.advise("leaf_rust", "ru")
    assert a["symptoms"] != b["symptoms"]


def test_no_api_key_uses_kb():
    r = advice.answer("жапырақта сары жолақтар пайда болды", "kk")
    assert r["generated_by"] == "kb"
    assert r["context"][0]["class_id"] == "stripe_rust"


def test_ru_retrieval_finds_rust():
    r = advice.answer("рыжие пустулы на листе, ржавый порошок", "ru")
    assert r["context"][0]["class_id"] == "leaf_rust"


def test_unrelated_question_gives_safe_fallback():
    r = advice.answer("xyz qwerty", "ru")
    assert "агроном" in r["answer"].lower()


def test_llm_error_falls_back(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-invalid")
    monkeypatch.setattr(advice, "LLM_MODEL", "claude-opus-5-5")

    class Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("network down")

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", Boom)
    r = advice.answer("мучнистый налёт на листьях", "ru")
    assert r["generated_by"] == "kb"


def test_question_with_diagnosis_answers_about_that_disease():
    r = advice.answer("Қай кезде өңдеген дұрыс?", "kk", class_id="leaf_rust")
    assert r["context"][0]["class_id"] == "leaf_rust"
    assert r["context"][0]["field"] in ("timing", "threshold", "chemical")
