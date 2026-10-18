"""Stage 2 pipeline: group -> (LLM only for new/updated stories) -> story files, latest.json, archive."""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import timedelta
from pathlib import Path

from . import aggregate, group
from .store import read_json, write_json
from .util import iso, utcnow

log = logging.getLogger(__name__)

LATEST_LIMIT = 200
STORY_RETENTION_DAYS = 90
LOAD_HOURS = 72
MAX_LLM_PER_RUN = int(os.environ.get("MAX_LLM_PER_RUN", "40"))


def fingerprint(story: dict) -> str:
    return hashlib.sha1(",".join(sorted(story["article_ids"])).encode()).hexdigest()[:10]


def card(s: dict) -> dict:
    return {
        "id": s["id"],
        "headline_en": s["headline_en"], "headline_te": s["headline_te"],
        "summary_en": s["summary_en"], "summary_te": s["summary_te"],
        "tags": s["tags"], "fallback": s.get("fallback", {"en": False, "te": False}),
        "created": s["created"], "updated": s["updated"],
        "n_articles": len(s["articles"]),
        "outlets": sorted({a["source_name"] for a in s["articles"]}),
        "languages": sorted({a["language"] for a in s["articles"]}),
    }


def _load_recent(stories_dir: Path) -> dict[str, dict]:
    cutoff = iso(utcnow() - timedelta(hours=LOAD_HOURS))
    out = {}
    if stories_dir.exists():
        for p in stories_dir.glob("*.json"):
            s = read_json(p, None)
            if s and s.get("updated", "") >= cutoff:
                out[s["id"]] = s
    return out


def _prune(stories_dir: Path, state: dict) -> None:
    today = utcnow().strftime("%Y-%m-%d")
    if state.get("last_prune") == today or not stories_dir.exists():
        return
    cutoff = iso(utcnow() - timedelta(days=STORY_RETENTION_DAYS))
    for p in stories_dir.glob("*.json"):
        s = read_json(p, None)
        if s is None or s.get("updated", "") < cutoff:
            p.unlink(missing_ok=True)  # cards stay in data/archive/
            state.get("stories", {}).pop(p.stem, None)
    state["last_prune"] = today


def process(data_dir: Path, pool: list[dict], enricher, embed_fn=group.embed) -> dict:
    stories_dir = data_dir / "stories"
    state = read_json(data_dir / "state.json", {"seen": {}})
    sstate: dict = state.setdefault("stories", {})  # id -> {"fp": fingerprint, "llm_at": iso}

    stories = _load_recent(stories_dir)
    changed = group.group(pool, stories, embed_fn)

    # Which stories need the LLM? Any whose article set differs from what was last summarised.
    pending = [s for s in stories.values()
               if sstate.get(s["id"], {}).get("fp") != fingerprint(s)]
    # Most-covered first, then newest; the cap protects the API bill after outages/first runs.
    pending.sort(key=lambda s: (len({a["source"] for a in s["articles"]}), s["updated"]), reverse=True)

    enriched, failed = [], 0
    if enricher is not None:
        for s in pending[:getattr(enricher, "cap", MAX_LLM_PER_RUN)]:
            try:
                s.update(enricher.enrich(s))
                sstate[s["id"]] = {"fp": fingerprint(s), "llm_at": iso(utcnow())}
                enriched.append(s["id"])
            except Exception as e:  # keep going; the story is retried next run
                failed += 1
                log.error("enrich failed for %s: %s", s["id"], e)
    elif pending:
        log.warning("no enricher configured: %d stories left unsummarised", len(pending))

    for sid in set(changed) | set(enriched):
        write_json(stories_dir / f"{sid}.json", stories[sid])

    # cards for summarised, relevant stories
    new_cards = {sid: card(stories[sid]) for sid in enriched
                 if stories[sid].get("relevant", True)}
    hide = {sid for sid in enriched if not stories[sid].get("relevant", True)}
    # stories touched but already summarised before (new article, LLM failed/capped) keep their old card
    latest_doc = read_json(data_dir / "latest.json", {"stories": []})
    cards = {c["id"]: c for c in latest_doc.get("stories", []) if "headline_en" in c}
    for sid in hide:
        cards.pop(sid, None)
    cards.update(new_cards)
    latest = sorted(cards.values(), key=lambda c: c["updated"], reverse=True)[:LATEST_LIMIT]
    write_json(data_dir / "latest.json",
               {"generated_at": iso(utcnow()), "count": len(latest), "stories": latest})

    # monthly archive keeps every card ever produced
    by_month: dict[str, list[dict]] = {}
    for c in new_cards.values():
        by_month.setdefault(c["created"][:7], []).append(c)
    for month, items in by_month.items():
        p = data_dir / "archive" / f"{month}.json"
        doc = read_json(p, {"month": month, "articles": [], "stories": []})
        existing = {c["id"]: c for c in doc.get("stories", [])}
        existing.update({c["id"]: c for c in items})
        doc["stories"] = sorted(existing.values(), key=lambda c: c["updated"], reverse=True)
        write_json(p, doc)

    _prune(stories_dir, state)
    write_json(data_dir / "state.json", state)
    aggregate.build(data_dir)
    return {"stories_total": len(stories), "changed": len(changed), "enriched": len(enriched),
            "failed": failed, "deferred": max(0, len(pending) - len(enriched) - failed)}
