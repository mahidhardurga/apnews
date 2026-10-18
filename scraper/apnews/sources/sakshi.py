"""Sakshi - site-wide feed filtered to /andhra-pradesh/ URLs (see sources.yaml options)."""
from .base import Source


class Impl(Source):
    def excerpt_from(self, entry) -> str:
        return ""  # feed description is just "<title> <author> <timestamp>", not a real excerpt
