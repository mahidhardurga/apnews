"""Rule-based enricher: same interface as llm.Enricher, but no model and no API key.

- tags: keyword lexicon (lexicon.yaml, English + Telugu)
- summary: extractive (leading sentences of the best article excerpt per language)
- coverage comparison: not generated (needs prose); the story page lists each outlet's own headline
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from . import taxonomy

PATH = Path(__file__).resolve().parents[1] / "lexicon.yaml"
SUMMARY_CHARS = 360
_SENT = re.compile(r"(?<=[.!?।])\s+")
_TELUGU = re.compile(r"[ఀ-౿]")


class _Matcher:
    """Matches a list of keywords. ASCII: word-boundary (case-sensitive if short all-caps acronym);
    non-ASCII (Telugu): plain substring."""

    def __init__(self, words: list[str]):
        pats = []
        for w in words:
            if _TELUGU.search(w):
                pats.append(re.escape(w))
            else:
                p = r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])"
                pats.append(p if (w.isupper() and len(w) <= 5) else "(?i:" + p + ")")
        self.rx = re.compile("|".join(pats)) if pats else None

    def hits(self, text: str) -> bool:
        return bool(self.rx and self.rx.search(text))


@lru_cache(maxsize=1)
def _lex():
    raw = yaml.safe_load(PATH.read_text(encoding="utf-8"))
    m = lambda d: {k: _Matcher(v) for k, v in d.items()}
    return {"parties": m(raw["parties"]), "leaders": m(raw["leaders"]), "districts": m(raw["districts"]),
            "topics": m(raw["topics"]), "political": _Matcher(raw["political_terms"])}


def _lead(text: str, limit: int = SUMMARY_CHARS) -> str:
    """First sentences of `text`, up to `limit` chars."""
    out = ""
    for s in _SENT.split(text.strip()):
        if out and len(out) + len(s) + 1 > limit:
            break
        out = f"{out} {s}".strip()
    if len(out) > limit:
        out = out[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return out


class Enricher:
    cap = 10**6  # no cost, no limit

    def __init__(self):
        self.taxo = taxonomy.load()
        self.lex = _lex()

    def enrich(self, story: dict) -> dict:
        arts = story["articles"]
        text = " \n".join(f'{a["title"]}. {a["excerpt"]}' for a in arts)
        lx = self.lex

        parties = [self.taxo.party(p) or p for p, mt in lx["parties"].items() if mt.hits(text)]
        leaders = [n for n, mt in lx["leaders"].items() if mt.hits(text)]
        districts = [d for d, mt in lx["districts"].items() if mt.hits(text)]
        political = bool(parties or leaders or lx["political"].hits(text))
        topic = next((t for t, mt in lx["topics"].items() if mt.hits(text)), None)
        if topic is None:
            topic = "politics" if political else "other"

        # Prefer the most widely reported framing: the first article in each language.
        by_lang: dict[str, dict] = {}
        for a in sorted(arts, key=lambda a: a["published"]):
            by_lang.setdefault(a["language"], a)

        def pick(field: str, lang: str, other: str):
            a = by_lang.get(lang) or by_lang.get(other)
            return a, (a["language"] != lang) if a else False

        h_en, h_en_fb = pick("title", "en", "te")
        h_te, h_te_fb = pick("title", "te", "en")

        def summary(a):
            return _lead(a["excerpt"] or a["title"])

        out = {
            "relevant": political,
            "headline_en": h_en["title"], "headline_te": h_te["title"],
            "summary_en": summary(h_en), "summary_te": summary(h_te),
            # set when the text is in the other language because no outlet wrote one in this language
            "fallback": {"en": h_en_fb, "te": h_te_fb},
            "tags": {"parties": parties, "leaders": leaders[:6],
                     "district": districts[0] if districts else None, "topic": topic},
            "coverage_en": None, "coverage_te": None,
            "enriched_by": "rules",
        }
        return out
