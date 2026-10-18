from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parents[1] / "taxonomy.yaml"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class Taxonomy:
    def __init__(self, raw: dict):
        self.parties = list(raw["parties"])
        self.topics = list(raw["topics"])
        self.districts = list(raw["districts"])
        self._alias: dict[str, str] = {}
        for canon, aliases in (raw.get("leaders") or {}).items():
            for a in [canon, *aliases]:
                self._alias[a.lower()] = canon
        self._district = {d.lower(): d for d in self.districts}
        self._party = {p.lower(): p for p in self.parties}

    def party(self, v: str) -> str | None:
        return self._party.get(v.strip().lower())

    def district(self, v: str | None) -> str | None:
        return self._district.get((v or "").strip().lower())

    def topic(self, v: str | None) -> str:
        v = (v or "").strip().lower()
        return v if v in self.topics else "other"

    def leader(self, v: str) -> str:
        v = v.strip()
        return self._alias.get(v.lower(), v)


@lru_cache(maxsize=1)
def load() -> Taxonomy:
    return Taxonomy(yaml.safe_load(PATH.read_text(encoding="utf-8")))
