"""Google-News-style sitemap source (<news:title>, <news:publication_date>).

Used for outlets with no RSS but a publisher-provided news sitemap that robots.txt allows.
Options: url_regex (keep only matching URLs), limit (newest N).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from ..util import clean_text
from .base import Source

NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "n": "http://www.google.com/schemas/sitemap-news/0.9"}


class NewsSitemapSource(Source):
    def fetch(self) -> list[dict]:
        rx = re.compile(self.cfg.options["url_regex"]) if self.cfg.options.get("url_regex") else None
        found: list[dict] = []
        for sm_url in self.cfg.feeds:
            root = ET.fromstring(self.http.get(sm_url).content)
            for u in root.findall("s:url", NS):
                loc = (u.findtext("s:loc", namespaces=NS) or "").strip()
                news = u.find("n:news", NS)
                if not loc or news is None or (rx and not rx.search(loc)):
                    continue
                title = clean_text(news.findtext("n:title", namespaces=NS))
                when = news.findtext("n:publication_date", namespaces=NS) or u.findtext("s:lastmod", namespaces=NS)
                if not title:
                    continue
                try:
                    dt = datetime.fromisoformat(when.strip().replace("Z", "+00:00")).astimezone(timezone.utc)
                except (ValueError, AttributeError):
                    continue
                found.append(self.make(loc, title, "", dt))
        found.sort(key=lambda a: a["published"], reverse=True)
        return found[: int(self.cfg.options.get("limit", self.cfg.max_items))]
