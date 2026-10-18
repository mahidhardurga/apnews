"""Derived files built from archived story cards: leaders, districts, trending, daily digest."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from . import taxonomy
from .store import read_json, write_json
from .util import iso, utcnow

IST = timezone(timedelta(hours=5, minutes=30))


def _recent_cards(data_dir, since_iso: str) -> list[dict]:
    now = utcnow()
    months = {now.strftime("%Y-%m"), (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")}
    cards = []
    for m in sorted(months):
        doc = read_json(data_dir / "archive" / f"{m}.json", {})
        cards += [c for c in doc.get("stories", []) if c["updated"] >= since_iso]
    return sorted(cards, key=lambda c: c["updated"], reverse=True)


def _stub(c: dict) -> dict:
    return {"id": c["id"], "headline_en": c["headline_en"], "headline_te": c["headline_te"],
            "updated": c["updated"]}


def score(c: dict) -> int:
    return 3 * len(c["outlets"]) + c["n_articles"]


def build(data_dir) -> None:
    taxo = taxonomy.load()
    now = utcnow()
    week = _recent_cards(data_dir, iso(now - timedelta(days=7)))

    # leaders
    leaders: dict[str, list[dict]] = defaultdict(list)
    for c in week:
        for name in c["tags"]["leaders"]:
            leaders[name].append(c)
    write_json(data_dir / "leaders.json", {
        "generated_at": iso(now),
        "leaders": sorted(({"slug": taxonomy.slug(n), "name": n, "count": len(cs),
                            "parties": sorted({p for c in cs for p in c["tags"]["parties"]}),
                            "last_seen": cs[0]["updated"], "stories": [_stub(c) for c in cs[:30]]}
                           for n, cs in leaders.items()), key=lambda x: -x["count"])})

    # districts (all listed, zero allowed, so the map can colour every district)
    by_d: dict[str, list[dict]] = defaultdict(list)
    for c in week:
        if c["tags"]["district"]:
            by_d[c["tags"]["district"]].append(c)
    write_json(data_dir / "districts.json", {
        "generated_at": iso(now),
        "districts": [{"slug": taxonomy.slug(d), "name": d, "count": len(by_d[d]),
                       "stories": [_stub(c) for c in by_d[d][:10]]} for d in taxo.districts]})

    # trending: tag counts in last 24h vs the 24h before
    t0, t1 = iso(now - timedelta(hours=24)), iso(now - timedelta(hours=48))
    cur: dict[tuple, int] = defaultdict(int)
    prev: dict[tuple, int] = defaultdict(int)
    for c in _recent_cards(data_dir, t1):
        bucket = cur if c["updated"] >= t0 else prev
        tg = c["tags"]
        keys = [("leader", x) for x in tg["leaders"]] + [("party", x) for x in tg["parties"]] \
            + [("topic", tg["topic"])] + ([("district", tg["district"])] if tg["district"] else [])
        for k in keys:
            bucket[k] += 1
    rows = [{"kind": k, "name": n, "count": v, "previous": prev.get((k, n), 0),
             "delta": v - prev.get((k, n), 0)} for (k, n), v in cur.items() if n != "other"]
    rows.sort(key=lambda r: (-r["count"], -r["delta"]))
    write_json(data_dir / "trending.json", {"generated_at": iso(now), "tags": rows[:25]})

    # daily digest (IST calendar day): top 10 by outlet coverage
    day = now.astimezone(IST).strftime("%Y-%m-%d")
    todays = [c for c in _recent_cards(data_dir, iso(now - timedelta(hours=48)))
              if datetime.fromisoformat(c["updated"].replace("Z", "+00:00"))
              .astimezone(IST).strftime("%Y-%m-%d") == day]
    todays.sort(key=lambda c: (-score(c), c["updated"]))
    write_json(data_dir / "digest" / f"{day}.json",
               {"date": day, "generated_at": iso(now), "stories": todays[:10]})
    dates = sorted((f.stem for f in (data_dir / "digest").glob("????-??-??.json")), reverse=True)
    write_json(data_dir / "digest" / "index.json", {"dates": dates})
