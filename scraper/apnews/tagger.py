"""Tag each headline with one topic and (if any) one AP district. Keyword rules only: no ML, no API."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from .rules import _Matcher

ROOT = Path(__file__).resolve().parents[1]
GENERAL = "general"


@lru_cache(maxsize=1)
def _load():
    topics = yaml.safe_load((ROOT / "topics.yaml").read_text(encoding="utf-8"))["topics"]
    lex = yaml.safe_load((ROOT / "lexicon.yaml").read_text(encoding="utf-8"))
    return {
        "topics": {t: [_Matcher([w]) for w in words] for t, words in topics.items()},
        "order": list(topics),
        "people": [_Matcher([w]) for v in list(lex["parties"].values()) + list(lex["leaders"].values()) for w in v],
        "districts": {d: _Matcher(words) for d, words in lex["districts"].items()},
    }


def _text(a: dict) -> str:
    slug = re.sub(r"[-_/.]+", " ", urlsplit(a["url"]).path)  # English words in the link help Telugu titles
    return f'{a["title"]} {slug}'


def topic_of(a: dict) -> str:
    cfg = _load()
    text = _text(a)
    scores = {t: sum(m.hits(text) for m in ms) for t, ms in cfg["topics"].items()}
    scores["politics"] += 2 * sum(m.hits(a["title"]) for m in cfg["people"])
    best = max(scores.values())
    if best == 0:
        return GENERAL
    return next(t for t in cfg["order"] if scores[t] == best)  # tie -> earlier topic


def district_of(a: dict) -> str | None:
    text = _text(a)
    return next((d for d, m in _load()["districts"].items() if m.hits(text)), None)


def apply(a: dict) -> dict:
    a["topic"] = topic_of(a)
    a["district"] = district_of(a)
    return a
