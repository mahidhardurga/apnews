"""JSON persistence under web/public/data."""
from __future__ import annotations

import json
from datetime import timedelta
from difflib import SequenceMatcher
from pathlib import Path

from . import tagger
from .util import iso, norm_title, utcnow

POOL_HOURS = 24 * 7   # the site shows the last 7 days (also the pool for opt-in story grouping)
POOL_MAX = 6000
STATE_RETENTION_DAYS = 14
TITLE_SIM_THRESHOLD = 0.92


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # compact + sorted keys => small, stable diffs in git
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
                    encoding="utf-8")


def dedupe(new: list[dict], known: list[dict]) -> list[dict]:
    """Drop items whose id/URL we already have, or whose title nearly matches a same-language one."""
    seen_ids = {a["id"] for a in known}
    pool = [(a["language"], norm_title(a["title"])) for a in known]
    kept: list[dict] = []
    for art in new:
        if art["id"] in seen_ids:
            continue
        nt = norm_title(art["title"])
        sm = SequenceMatcher(autojunk=False)
        sm.set_seq2(nt)
        dup = False
        for lang, other in pool:
            if lang != art["language"]:
                continue
            sm.set_seq1(other)
            if sm.real_quick_ratio() >= TITLE_SIM_THRESHOLD and sm.quick_ratio() >= TITLE_SIM_THRESHOLD \
                    and sm.ratio() >= TITLE_SIM_THRESHOLD:
                dup = True
                break
        if dup:
            continue
        seen_ids.add(art["id"])
        pool.append((art["language"], nt))
        kept.append(art)
    return kept


LATEST_LIMIT = 2000


def save(data_dir: Path, new_articles: list[dict], run_info: dict, headlines_only: bool = True) -> dict:
    """Merge new articles into the rolling pool (articles.json) and the monthly archive.

    Returns {"pool": [...all pool articles...], "fresh": [...newly added...]}.
    """
    pool_path = data_dir / "articles.json"
    state_path = data_dir / "state.json"

    if pool_path.exists():
        pool = read_json(pool_path, {"articles": []})["articles"]
    else:  # stage-1 layout kept raw articles in latest.json
        old = read_json(data_dir / "latest.json", {})
        pool = old.get("articles", []) if isinstance(old, dict) else []
    state = read_json(state_path, {"seen": {}})

    # state.seen: id -> first_seen; skips re-adding articles that already left the pool.
    fresh = [a for a in dedupe(new_articles, pool) if a["id"] not in state["seen"]]

    now = utcnow()
    for a in fresh:
        state["seen"][a["id"]] = iso(now)
    cutoff = iso(now - timedelta(days=STATE_RETENTION_DAYS))
    state["seen"] = {k: v for k, v in state["seen"].items() if v >= cutoff}
    state["last_run"] = run_info

    pool_cutoff = iso(now - timedelta(hours=POOL_HOURS))
    pool = [a for a in pool + fresh if a["published"] >= pool_cutoff]
    pool.sort(key=lambda a: a["published"], reverse=True)
    pool = pool[:POOL_MAX]
    for a in pool:  # (re)tag everything so keyword changes apply to the whole pool
        tagger.apply(a)

    by_month: dict[str, list[dict]] = {}
    for a in fresh:
        by_month.setdefault(a["published"][:7], []).append(a)
    for month, items in by_month.items():
        p = data_dir / "archive" / f"{month}.json"
        doc = read_json(p, {"month": month, "articles": [], "stories": []})
        existing = {a["id"]: a for a in doc["articles"]}
        existing.update({a["id"]: a for a in items})
        doc["articles"] = sorted(existing.values(), key=lambda a: a["published"], reverse=True)
        write_json(p, doc)

    write_json(pool_path, {"generated_at": iso(now), "count": len(pool), "articles": pool})
    if headlines_only:  # the site reads this: just title, link, outlet, time, language
        heads = [{k: a[k] for k in ("id", "title", "url", "source", "source_name", "language", "published", "topic", "district")}
                 for a in pool[:LATEST_LIMIT]]
        write_json(data_dir / "latest.json", {"generated_at": iso(now), "count": len(heads), "articles": heads})
    write_json(state_path, state)
    return {"pool": pool, "fresh": fresh}
