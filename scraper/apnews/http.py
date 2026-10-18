"""Polite HTTP client: robots.txt, per-host rate limit, retries."""
from __future__ import annotations

import logging
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

log = logging.getLogger(__name__)


class BlockedByRobots(Exception):
    pass


class Fetcher:
    def __init__(self, user_agent: str, min_delay: float = 2.0, timeout: float = 20.0):
        self.ua = user_agent
        self.min_delay = min_delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept-Language": "en,te;q=0.8"})
        self._last_hit: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    # -- robots ---------------------------------------------------------------
    def _robots_for(self, host_root: str) -> RobotFileParser | None:
        if host_root in self._robots:
            return self._robots[host_root]
        rp: RobotFileParser | None = RobotFileParser()
        r = None
        for attempt in range(3):  # a flaky robots.txt must not silently disable a source
            try:
                self._throttle(host_root)
                r = self.session.get(host_root + "/robots.txt", timeout=self.timeout)
                if r.status_code < 500:
                    break
            except requests.RequestException as e:
                log.warning("robots.txt fetch failed for %s: %s", host_root, e)
                r = None
            time.sleep(2 * (attempt + 1))
        if r is None or r.status_code >= 500 or r.status_code in (401, 403):
            rp.parse(["User-agent: *", "Disallow: /"])  # still unreachable/forbidden: be conservative
        elif r.status_code >= 400:
            rp.parse([])  # no robots.txt => everything allowed
        else:
            rp.parse(r.text.splitlines())
        self._robots[host_root] = rp
        return rp

    def allowed(self, url: str) -> bool:
        p = urlsplit(url)
        rp = self._robots_for(f"{p.scheme}://{p.netloc}")
        return True if rp is None else rp.can_fetch(self.ua, url)

    # -- rate limiting ----------------------------------------------------------
    def _throttle(self, key: str) -> None:
        host = urlsplit(key).netloc or key
        wait = self._last_hit.get(host, 0) + self.min_delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_hit[host] = time.monotonic()

    # -- fetch ------------------------------------------------------------------
    def get(self, url: str, retries: int = 2) -> requests.Response:
        if not self.allowed(url):
            raise BlockedByRobots(url)
        last: Exception | None = None
        for attempt in range(retries + 1):
            self._throttle(url)
            try:
                r = self.session.get(url, timeout=self.timeout)
                if r.status_code >= 500 or r.status_code == 429:
                    raise requests.HTTPError(f"{r.status_code} for {url}")
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                last = e
                if attempt < retries:
                    time.sleep(2 ** (attempt + 1))
        assert last is not None
        raise last
