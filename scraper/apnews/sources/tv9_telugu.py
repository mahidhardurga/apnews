"""TV9 Telugu - Andhra Pradesh category feed (RSS, WordPress)."""
from ..util import clean_text
from .base import Source


class Impl(Source):
    def excerpt_from(self, entry) -> str:
        # WordPress feeds carry the full article in content:encoded; only use the short summary.
        return clean_text(entry.get("summary") or "")
