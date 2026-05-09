import requests

from spotify_client import get_client
from vibe_profile import build_vibe_profile, feature_closeness_score

RECCOBEATS_BASE = "https://api.reccobeats.com/v1"
TIMEOUT = 15
RECCOBEATS_BATCH = 40  # ReccoBeats caps at 40 ids per call


def _chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]

NUMERIC_FILTERS = [
    ("tempo", "tempo_min", "tempo_max", 200.0),
    ("energy", "energy_min", "energy_max", 1.0),
    ("danceability", "danceability_min", "danceability_max", 1.0),
    ("valence", "valence_min", "valence_max", 1.0),
    ("acousticness", "acousticness_min", "acousticness_max", 1.0),
]


def _spotify_to_reccobeats_map(spotify_ids):
    mapping = {}
    for chunk in _chunked(spotify_ids, RECCOBEATS_BATCH):
        r = requests.get(
            f"{RECCOBEATS_BASE}/track",
            params={"ids": ",".join(chunk)},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        for item in r.json().get("content", []):
            href = item.get("href") or ""
            sid = href.rsplit("/", 1)[-1] if href else None
            rid = item.get("id")
            if sid and rid:
                mapping[sid] = rid
    return mapping


def _fetch_features(reccobeats_ids):
    out = {}
    for chunk in _chunked(reccobeats_ids, RECCOBEATS_BATCH):
        r = requests.get(
            f"{RECCOBEATS_BASE}/audio-features",
            params={"ids": ",".join(chunk)},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        for item in r.json().get("content", []):
            if "id" in item:
                out[item["id"]] = item
    return out


def reccobeats_recommendations(seed_reccobeats_ids, size=30):
    """Ask ReccoBeats for tracks similar to the given seed track ids (max 5 seeds)."""
    seeds = seed_reccobeats_ids[:5]
    if not seeds:
        return []
    r = requests.get(
        f"{RECCOBEATS_BASE}/track/recommendation",
        params={"seeds": ",".join(seeds), "size": size},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("content") or []


def spotify_id_from_href(href):
    if not href:
        return None
    tail = href.rsplit("/", 1)[-1]
    return tail or None


def get_features_for_spotify_ids(spotify_ids):
    """Fetch ReccoBeats audio features for a list of Spotify track IDs.

    Returns dict mapping spotify_id -> features dict. Tracks ReccoBeats doesn't
    have are silently dropped.
    """
    s2r = _spotify_to_reccobeats_map(spotify_ids)
    if not s2r:
        return {}
    feats = _fetch_features(list(s2r.values()))
    return {sid: feats[rid] for sid, rid in s2r.items() if rid in feats}


def _passes(feat, filters):
    for key, lo_k, hi_k, _ in NUMERIC_FILTERS:
        v = feat.get(key)
        lo, hi = filters.get(lo_k), filters.get(hi_k)
        if lo is not None and (v is None or v < lo):
            return False
        if hi is not None and (v is None or v > hi):
            return False
    if filters.get("key") is not None and feat.get("key") != filters["key"]:
        return False
    if filters.get("mode") is not None and feat.get("mode") != filters["mode"]:
        return False
    return True


def _score(feat, filters, vibe_profile=None):
    """Lower is better — sum of normalized distances from each range midpoint."""
    score = 0.0
    for key, lo_k, hi_k, span in NUMERIC_FILTERS:
        lo, hi = filters.get(lo_k), filters.get(hi_k)
        if lo is None or hi is None:
            continue
        v = feat.get(key)
        if v is None:
            continue
        midpoint = (lo + hi) / 2
        score += abs(v - midpoint) / span
    if vibe_profile:
        # Convert closeness [0..1] to distance [1..0], blended with filter score.
        vibe_distance = 1.0 - feature_closeness_score(feat, vibe_profile["targets"])
        score += 0.75 * vibe_distance
    return score


SPOTIFY_MAX_PER_PAGE = 10  # this client's quota caps search at 10 per call


def _paginated_search(sp, query, total, market):
    items = []
    seen = set()
    offset = 0
    while len(items) < total:
        page = sp.search(
            q=query, type="track", limit=SPOTIFY_MAX_PER_PAGE, offset=offset, market=market
        )
        page_items = page.get("tracks", {}).get("items", [])
        if not page_items:
            break
        for t in page_items:
            tid = t.get("id")
            if tid and tid not in seen:
                seen.add(tid)
                items.append(t)
        offset += SPOTIFY_MAX_PER_PAGE
        if len(page_items) < SPOTIFY_MAX_PER_PAGE:
            break
    return items[:total]


def filter_search(query, filters, limit=10, candidate_pool=50, market="US", vibe_keywords=None):
    """Search Spotify, fetch audio features from ReccoBeats, filter and rank."""
    sp = get_client()
    candidate_pool = max(min(candidate_pool, 50), limit)
    items = _paginated_search(sp, query, candidate_pool, market)
    if not items:
        return {"results": [], "candidate_count": 0, "feature_coverage": 0}
    vibe_profile = build_vibe_profile(vibe_keywords)

    spotify_ids = [t["id"] for t in items if t.get("id")]
    features = get_features_for_spotify_ids(spotify_ids)

    enriched = []
    for t in items:
        sid = t.get("id")
        if not sid or sid not in features:
            continue
        feat = features[sid]
        if not _passes(feat, filters):
            continue
        enriched.append((t, feat, _score(feat, filters, vibe_profile=vibe_profile)))

    enriched.sort(key=lambda x: x[2])
    return {
        "results": enriched[:limit],
        "candidate_count": len(items),
        "feature_coverage": len(features),
    }
