"""Group articles into stories using multilingual sentence embeddings.

Story IDs are stable: existing stories keep their members, and each new article
joins the best-matching story still "open" (updated within the window) or starts
a new one. So "new or updated" is simply "story gained members".
"""
from __future__ import annotations

import hashlib
import os
from datetime import timedelta

import numpy as np

from .util import iso, utcnow

MODEL_NAME = os.environ.get("EMBED_MODEL", "intfloat/multilingual-e5-small")
WINDOW_HOURS = 48
# Cosine similarity to the nearest existing member needed to join a story. Depends on the model
# (e5 scores are compressed into ~0.8-1.0); tuned on real AP articles, see README.
JOIN_THRESHOLD = float(os.environ.get("GROUP_THRESHOLD", "0.89"))
MAX_ARTICLES_PER_STORY = 30

_model = None


def embed(texts: list[str]) -> np.ndarray:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
    if "e5" in MODEL_NAME.lower():  # e5 models expect an instruction prefix
        texts = ["query: " + t for t in texts]
    return np.asarray(_model.encode(texts, batch_size=64, normalize_embeddings=True,
                                    show_progress_bar=False))


def story_id(first_article_id: str) -> str:
    return hashlib.sha1(("s:" + first_article_id).encode()).hexdigest()[:12]


def slim(a: dict) -> dict:
    return {k: a[k] for k in ("id", "url", "title", "excerpt", "source", "source_name",
                              "language", "published")}


def group(pool: list[dict], stories: dict[str, dict], embed_fn=embed) -> set[str]:
    """Assign pool articles to stories (mutating `stories`). Returns IDs of new/changed stories."""
    now = utcnow()
    window_start = iso(now - timedelta(hours=WINDOW_HOURS))
    window = [a for a in pool if a["published"] >= window_start]
    if not window:
        return set()

    vecs = dict(zip((a["id"] for a in window),
                    embed_fn([f'{a["title"]}. {a["excerpt"][:200]}' for a in window])))
    by_id = {a["id"]: a for a in window}
    assigned = {aid for s in stories.values() for aid in s["article_ids"]}

    # open clusters = stories touched within the window and with embeddable members
    clusters: dict[str, dict] = {}
    for sid, s in stories.items():
        if s["updated"] < window_start:
            continue
        members = [vecs[a] for a in s["article_ids"] if a in vecs]
        if members:
            clusters[sid] = members

    changed: set[str] = set()
    todo = sorted((a for a in window if a["id"] not in assigned), key=lambda a: a["published"])
    for art in todo:
        v = vecs[art["id"]]
        best, best_sim = None, JOIN_THRESHOLD
        for sid, members in clusters.items():
            # nearest-member linking: a centroid drifts towards generic "AP news" and absorbs everything
            sim = float(np.max(np.stack(members) @ v))
            if sim >= best_sim:
                best, best_sim = sid, sim
        if best is None:
            best = story_id(art["id"])
            stories[best] = {"id": best, "created": art["published"], "updated": art["published"],
                             "article_ids": [], "articles": []}
            clusters[best] = []
        s = stories[best]
        s["article_ids"].append(art["id"])
        s["articles"].append(slim(art))
        s["updated"] = max(s["updated"], art["published"])
        clusters[best].append(v)
        changed.add(best)

    for sid in changed:
        s = stories[sid]
        s["articles"].sort(key=lambda a: a["published"])
        s["articles"] = s["articles"][-MAX_ARTICLES_PER_STORY:]
        s["article_ids"] = [a["id"] for a in s["articles"]]
    return changed
