"""Entry point:  python -m apnews.run [--only id1,id2] [--data-dir PATH] [--dry-run]"""
from __future__ import annotations

import argparse
import importlib
import logging
import os
import sys
from pathlib import Path

import yaml

from . import store
from .http import Fetcher
from .sources.base import SourceConfig
from .util import iso, utcnow

log = logging.getLogger("apnews")

ROOT = Path(__file__).resolve().parents[2]  # repo root (scraper/apnews/run.py -> ../../)
DEFAULT_DATA = ROOT / "web" / "public" / "data"
SOURCES_YAML = ROOT / "scraper" / "sources.yaml"


def load_sources(only: set[str] | None):
    conf = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    d = conf.get("defaults", {})
    fetcher = Fetcher(d["user_agent"], d.get("min_delay_seconds", 2.0), d.get("timeout_seconds", 20))
    for s in conf["sources"]:
        if not s.get("enabled") or not s.get("module"):
            continue
        if only and s["id"] not in only:
            continue
        cfg = SourceConfig(id=s["id"], name=s["name"], language=s["language"],
                           feeds=s.get("feeds", []), options=s.get("options", {}),
                           max_items=d.get("max_items_per_source", 60),
                           excerpt_chars=d.get("excerpt_chars", 280))
        mod = importlib.import_module(f"apnews.sources.{s['module']}")
        yield mod.Impl(cfg, fetcher)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated source ids")
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--stories", action="store_true", help="also group into stories + enrich (needs requirements-stories.txt)")
    ap.add_argument("--dry-run", action="store_true", help="fetch and report, write nothing")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    only = set(args.only.split(",")) if args.only else None
    collected: list[dict] = []
    report: dict[str, dict] = {}

    for src in load_sources(only):
        sid = src.cfg.id
        try:
            items = src.fetch()
            collected.extend(items)
            report[sid] = {"ok": True, "items": len(items)}
            log.info("%s: %d items", sid, len(items))
        except Exception as e:  # one broken source must never stop the others
            report[sid] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
            log.error("%s FAILED: %s", sid, e)

    if not report:
        log.error("no sources ran")
        return 1

    if args.dry_run:
        log.info("dry run: %d items collected, nothing written", len(collected))
        return 0

    saved = store.save(args.data_dir, collected, {"at": iso(utcnow()), "sources": report},
                       headlines_only=not args.stories)
    log.info("articles: %d new, %d in pool", len(saved["fresh"]), len(saved["pool"]))

    if args.stories:
        from . import stories
        # Default: rule-based, no LLM. ENRICH_BACKEND=llm opts in (needs ANTHROPIC_API_KEY).
        if os.environ.get("ENRICH_BACKEND", "rules") == "llm":
            from .llm import Enricher
        else:
            from .rules import Enricher
        enricher = Enricher()
        log.info("stories: %s", stories.process(args.data_dir, saved["pool"], enricher))
    # Fail the job only if *every* source failed (so the Action surfaces total outages).
    return 0 if any(r["ok"] for r in report.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
