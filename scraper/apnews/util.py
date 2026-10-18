from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

_TRACKING = re.compile(r"^(utm_|fbclid|gclid|ref$|ref_src$|from$)", re.I)
_WS = re.compile(r"\s+")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_url(url: str) -> str:
    """Normalise a URL so the same article dedupes across runs."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING.match(k)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def article_id(url: str) -> str:
    return hashlib.sha1(canonical_url(url).encode()).hexdigest()[:12]


def clean_text(raw: str | None) -> str:
    """Strip HTML tags/entities and collapse whitespace."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "lxml").get_text(" ")
    return _WS.sub(" ", html.unescape(text)).strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return cut + "…"


def norm_title(title: str) -> str:
    """Lowercase, drop punctuation; works for Telugu too (keeps all letters/digits)."""
    t = re.sub(r"[^\w\s]", " ", title.lower(), flags=re.UNICODE)
    return _WS.sub(" ", t).strip()
