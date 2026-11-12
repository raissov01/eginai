"""Кеңестер: білім базасы (kb/diseases.yaml) + BM25 іздеу + қалауы бойынша LLM.

* `advise(class_id, lang)` — диагнозға арналған құрылымды кеңес, тек базадан
  (детерминистік, интернетсіз жұмыс істейді).
* `answer(question, lang, class_id)` — фермердің еркін сұрағына жауап. Базадан
  BM25-пен ең жақын фрагменттер табылады; `ANTHROPIC_API_KEY` болса, Claude
  тек сол фрагменттерге сүйеніп жауап құрастырады (RAG). Кілт жоқ немесе API
  қатесі болса — фрагменттердің өзі қайтарылады. Жюри компьютерінде кілтсіз
  де толық жұмыс істейді.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from rank_bm25 import BM25Okapi

log = logging.getLogger("eginai.advice")
Lang = Literal["kk", "ru"]
KB_PATH = Path(os.environ.get("EGINAI_KB", Path(__file__).resolve().parents[2] / "kb" / "diseases.yaml"))
FIELDS = ("symptoms", "conditions", "threshold", "timing", "prevention", "similar")
LLM_MODEL = os.environ.get("EGINAI_LLM_MODEL", "claude-opus-5-5")


@dataclass
class Chunk:
    class_id: str
    field: str
    lang: str
    text: str


@lru_cache(maxsize=1)
def kb() -> dict:
    return yaml.safe_load(KB_PATH.read_text(encoding="utf-8"))


def disease(class_id: str) -> dict:
    d = kb()["diseases"].get(class_id)
    if d is None:
        raise KeyError(class_id)
    return d


def name(class_id: str, lang: Lang) -> str:
    return disease(class_id)["name"][lang]


def advise(class_id: str, lang: Lang) -> dict:
    """Диагноз бойынша толық кеңес (базадан)."""
    d = disease(class_id)
    return {
        "title": d["name"][lang],
        "pathogen": d["pathogen"],
        "severity": d["severity"],
        "symptoms": d["symptoms"][lang],
        "conditions": d["conditions"][lang],
        "threshold": d["threshold"][lang],
        "actions": {"agro": d["actions"]["agro"][lang], "chemical": d["actions"]["chemical"][lang]},
        "timing": d["timing"][lang],
        "prevention": d["prevention"][lang],
        "similar": d["similar"][lang],
        "sources": [{"title": s["title"], "url": s["url"]} for s in kb()["sources"]],
    }


# --- Іздеу (RAG-тың «R» бөлігі) ------------------------------------------

def _tokens(text: str, lang: str = "kk") -> list[str]:
    """Қарапайым стемминг: сөздің алғашқы 4 (kk) немесе 5 (ru) әрпі.

    Қазақ және орыс тілі жалғамалы/флективті, сондықтан «сарғаяды», «сары»,
    «сарғайып» сияқты пішіндер бір түбірге жақындайды. Морфологиялық
    анализатор қоспай-ақ шағын база үшін жеткілікті.
    """
    n = 4 if lang == "kk" else 5  # қазақ жұрнақтары түбірге тезірек жалғанады
    return [w[:n] for w in re.findall(r"[\wәғқңөұүһі]+", text.lower()) if len(w) > 2]


@lru_cache(maxsize=1)
def _index() -> tuple[list[Chunk], dict[str, BM25Okapi]]:
    chunks: list[Chunk] = []
    for cid, d in kb()["diseases"].items():
        for lang in ("kk", "ru"):
            for f in FIELDS:
                if d[f][lang] != "—":
                    chunks.append(Chunk(cid, f, lang, f"{d['name'][lang]}. {d[f][lang]}"))
            for k in ("agro", "chemical"):
                chunks.append(Chunk(cid, k, lang, f"{d['name'][lang]}. {d['actions'][k][lang]}"))
    per_lang = {lang: BM25Okapi([_tokens(c.text, lang) for c in chunks if c.lang == lang]) for lang in ("kk", "ru")}
    return chunks, per_lang


def retrieve(question: str, lang: Lang, k: int = 4, class_id: str | None = None) -> list[Chunk]:
    chunks, bm = _index()
    pool = [c for c in chunks if c.lang == lang]
    scores = bm[lang].get_scores(_tokens(question, lang))
    ranked = sorted(zip(scores, pool), key=lambda t: -t[0])
    if class_id:
        # Диагноз белгілі: алдымен сол аурудың ең жақын фрагменттері, сосын басқалары
        own = [c for s, c in ranked if c.class_id == class_id][: k - 1]
        other = [c for s, c in ranked if c.class_id != class_id and s > 0][:1]
        return own + other
    return [c for s, c in ranked[:k] if s > 0]


# --- Генерация (RAG-тың «G» бөлігі, міндетті емес) -------------------------

SYSTEM = (
    "You are EginAI, an assistant for wheat farmers in Kazakhstan. Answer ONLY from the "
    "provided knowledge-base excerpts. If the excerpts do not contain the answer, say so "
    "and advise contacting an agronomist or the regional phytosanitary service. Never "
    "invent pesticide product names or doses; refer to the Kazakhstan pesticide register. "
    "Reply in {lang_name}, in 2-5 short sentences, plain text without markdown."
)


def _llm(question: str, lang: Lang, ctx: list[Chunk]) -> str | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(timeout=20.0, max_retries=1)
        excerpts = "\n".join(f"[{i + 1}] {c.text}" for i, c in enumerate(ctx))
        resp = client.beta.messages.create(
            model=LLM_MODEL,
            max_tokens=1024,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM.format(lang_name="Kazakh" if lang == "kk" else "Russian"),
            messages=[{"role": "user", "content": f"Knowledge base:\n{excerpts}\n\nQuestion: {question}"}],
        )
        if resp.stop_reason == "refusal":
            return None
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        return text or None
    except Exception as e:  # кез келген қате → базадағы мәтінге қайту
        log.warning("LLM unavailable, falling back to KB: %s", type(e).__name__)
        return None


def answer(question: str, lang: Lang, class_id: str | None = None) -> dict:
    ctx = retrieve(question, lang, class_id=class_id)
    text = _llm(question, lang, ctx) if ctx else None
    if text is None:
        fallback = {"kk": "Базада сәйкес мәлімет табылмады. Агрономға немесе фитосанитарлық қызметке хабарласыңыз.",
                    "ru": "В базе знаний нет подходящих сведений. Обратитесь к агроному или в фитосанитарную службу."}
        text = "\n".join(c.text for c in ctx[:2]) if ctx else fallback[lang]
        by = "kb"
    else:
        by = "llm"
    return {"answer": text, "generated_by": by,
            "context": [{"class_id": c.class_id, "field": c.field, "text": c.text} for c in ctx]}
