"""Base class for sources. One module per outlet; subclass and override hooks."""
from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import feedparser

from ..http import Fetcher
from ..util import article_id, canonical_url, clean_text, iso, truncate, utcnow

log = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    id: str
    name: str
    language: str
    feeds: list[str] = field(default_factory=list)
    options: dict = field(default_factory=dict)
    max_items: int = 60
    excerpt_chars: int = 280


class Source:
    """Default behaviour = generic RSS. Override `keep()` / `parse_entry()` or `fetch()`."""

    def __init__(self, cfg: SourceConfig, fetcher: Fetcher):
        self.cfg = cfg
        self.http = fetcher

    # -- hooks ----------------------------------------------------------------
    def keep(self, url: str, entry) -> bool:
        """Return False to drop an item (e.g. not about Andhra Pradesh)."""
        must = self.cfg.options.get("url_must_contain")
        if must and not any(m in url for m in must):
            return False
        words = self.cfg.options.get("keywords_any")  # for national feeds: keep only items about AP
        if words:
            text = f'{entry.get("title", "")} {entry.get("summary", "")}'.lower()
            return any(w.lower() in text for w in words)
        return True

    def excerpt_from(self, entry) -> str:
        return clean_text(entry.get("summary") or entry.get("description") or "")

    # -- machinery ------------------------------------------------------------
    def fetch(self) -> list[dict]:
        out: list[dict] = []
        for feed_url in self.cfg.feeds:
            resp = self.http.get(feed_url)
            parsed = feedparser.parse(resp.content)
            if parsed.bozo and not parsed.entries:
                raise ValueError(f"unparseable feed {feed_url}: {parsed.bozo_exception}")
            for entry in parsed.entries[: self.cfg.max_items]:
                art = self.to_article(entry)
                if art:
                    out.append(art)
        return out

    def to_article(self, entry) -> dict | None:
        url = (entry.get("link") or "").strip()
        title = clean_text(entry.get("title"))
        if not url or not title or not self.keep(url, entry):
            return None
        excerpt = truncate(self.excerpt_from(entry), self.cfg.excerpt_chars) if self.cfg.excerpt_chars else ""
        return self.make(url, title, excerpt, self._published(entry))

    def make(self, url: str, title: str, excerpt: str, published: datetime) -> dict:
        return {
            "id": article_id(url),
            "url": canonical_url(url),
            "title": title,
            "excerpt": excerpt,
            "source": self.cfg.id,
            "source_name": self.cfg.name,
            "language": self.cfg.language,
            "published": iso(published),
            "fetched": iso(utcnow()),
        }

    @staticmethod
    def _published(entry) -> datetime:
        for key in ("published_parsed", "updated_parsed"):
            t = entry.get(key)
            if t:
                return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
        return utcnow()
