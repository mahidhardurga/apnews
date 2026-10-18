"""Eenadu - AP section via its news sitemap (robots.txt explicitly allows /sitemap-news.xml)."""
from .sitemap import NewsSitemapSource


class Impl(NewsSitemapSource):
    pass
