import time

from reccobeats import get_features_for_spotify_ids
from spotify_client import get_client


SPOTIFY_MAX_PER_PAGE = 10


def _search_tracks(query, total=30, market="US"):
    sp = get_client()
    items = []
    seen = set()
    offset = 0

    while len(items) < total:
        results = sp.search(
            q=query,
            type="track",
            limit=SPOTIFY_MAX_PER_PAGE,
            offset=offset,
            market=market,
        )
        page_items = results.get("tracks", {}).get("items", [])
        if not page_items:
            break
        for item in page_items:
            tid = item.get("id")
            if tid and tid not in seen:
                seen.add(tid)
                items.append(item)
        offset += SPOTIFY_MAX_PER_PAGE
        if len(page_items) < SPOTIFY_MAX_PER_PAGE:
            break
    return items[:total]


# Broad-mood seed queries that build a varied candidate pool for the Mood
# plane. We aren't curating editorially — we just want coverage across the
# (valence, energy) plane. Cached for an hour so each click doesn't re-run
# six Spotify searches.
_MOOD_SEED_QUERIES = (
    "happy upbeat",
    "sad emotional",
    "chill mellow",
    "energetic dance",
    "melancholy slow",
    "uplifting anthem",
)
_POOL_TTL_SECONDS = 3600
_POOL_PER_QUERY = 20

_pool_cache = {"candidates": None, "features": None, "ts": 0.0, "market": None}


def _load_mood_pool(market="US"):
    now = time.time()
    if (
        _pool_cache["candidates"]
        and _pool_cache["features"]
        and _pool_cache["market"] == market
        and now - _pool_cache["ts"] < _POOL_TTL_SECONDS
    ):
        return _pool_cache["candidates"], _pool_cache["features"]

    seen = {}
    for q in _MOOD_SEED_QUERIES:
        try:
            tracks = _search_tracks(q, total=_POOL_PER_QUERY, market=market)
        except Exception:
            continue
        for t in tracks:
            tid = t.get("id")
            if tid and tid not in seen:
                seen[tid] = t

    candidates = list(seen.values())
    try:
        features = get_features_for_spotify_ids(list(seen.keys())) if seen else {}
    except Exception:
        features = {}

    _pool_cache["candidates"] = candidates
    _pool_cache["features"] = features
    _pool_cache["ts"] = now
    _pool_cache["market"] = market
    return candidates, features


def mood_seed(market="US"):
    """Return the curated candidate pool as (valence, energy) points for the mood plane."""
    candidates, features = _load_mood_pool(market=market)
    points = []
    for t in candidates:
        tid = t.get("id")
        feat = features.get(tid)
        if not feat:
            continue
        v = feat.get("valence")
        e = feat.get("energy")
        if v is None or e is None:
            continue
        points.append({
            "id": tid,
            "name": t.get("name", ""),
            "artists": [a["name"] for a in t.get("artists", [])],
            "valence": round(float(v), 3),
            "energy": round(float(e), 3),
        })
    return {"points": points}


_GENRE_CACHE = {}  # key: "genre:market" -> {candidates, features, ts}
_GENRE_TTL = 3600
_GENRE_TRACKS = 60  # more tracks → denser plane


def _load_genre_pool(genre, market="US"):
    key = f"{genre}:{market}"
    now = time.time()
    cached = _GENRE_CACHE.get(key)
    if (
        cached
        and cached.get("candidates")
        and cached.get("features")
        and now - cached.get("ts", 0) < _GENRE_TTL
    ):
        return cached["candidates"], cached["features"]

    try:
        tracks = _search_tracks(genre, total=_GENRE_TRACKS, market=market)
    except Exception:
        tracks = []

    ids = [t["id"] for t in tracks if t.get("id")]
    try:
        features = get_features_for_spotify_ids(ids) if ids else {}
    except Exception:
        features = {}

    _GENRE_CACHE[key] = {"candidates": tracks, "features": features, "ts": now}
    return tracks, features


def genre_seed(genre, market="US"):
    """Return genre tracks as (valence, energy) points for the mood plane."""
    candidates, features = _load_genre_pool(genre, market=market)
    points = []
    for t in candidates:
        tid = t.get("id")
        feat = features.get(tid)
        if not feat:
            continue
        v = feat.get("valence")
        e = feat.get("energy")
        if v is None or e is None:
            continue
        points.append({
            "id": tid,
            "name": t.get("name", ""),
            "artists": [a["name"] for a in t.get("artists", [])],
            "valence": round(float(v), 3),
            "energy": round(float(e), 3),
        })
    return {"points": points, "genre": genre}


def genre_search(valence, energy, genre, count=10, market="US"):
    """Return tracks closest to (valence, energy) from the given genre pool."""
    try:
        target_v = max(0.0, min(1.0, float(valence)))
        target_e = max(0.0, min(1.0, float(energy)))
    except (TypeError, ValueError):
        return {"error": "invalid coordinates"}

    candidates, features = _load_genre_pool(genre, market=market)
    if not candidates or not features:
        return {
            "target": {"valence": target_v, "energy": target_e},
            "recommendations": [],
            "candidate_count": 0,
            "feature_coverage": 0,
        }

    scored = []
    for t in candidates:
        tid = t.get("id")
        feat = features.get(tid)
        if not feat:
            continue
        v = feat.get("valence")
        e = feat.get("energy")
        if v is None or e is None:
            continue
        dv = float(v) - target_v
        de = float(e) - target_e
        scored.append((dv * dv + de * de, t, feat))

    scored.sort(key=lambda x: x[0])

    items = []
    for _d, t, feat in scored[:count]:
        items.append({
            "id": t.get("id"),
            "name": t.get("name", ""),
            "artists": [a["name"] for a in t.get("artists", [])],
            "album": (t.get("album") or {}).get("name", ""),
            "image": ((t.get("album") or {}).get("images") or [{}])[-1].get("url"),
            "url": (t.get("external_urls") or {}).get("spotify", ""),
            "popularity": t.get("popularity", 0),
            "features": {
                "valence": round(float(feat["valence"]), 3),
                "energy": round(float(feat["energy"]), 3),
                "tempo": round(float(feat["tempo"]), 1) if feat.get("tempo") is not None else None,
                "danceability": round(float(feat["danceability"]), 2) if feat.get("danceability") is not None else None,
            },
        })

    return {
        "target": {"valence": target_v, "energy": target_e},
        "recommendations": items,
        "candidate_count": len(candidates),
        "feature_coverage": len(features),
    }


def mood_search(valence, energy, count=10, market="US"):
    """Return tracks whose audio features sit closest to a (valence, energy) target."""
    try:
        target_v = max(0.0, min(1.0, float(valence)))
        target_e = max(0.0, min(1.0, float(energy)))
    except (TypeError, ValueError):
        return {"error": "invalid coordinates"}

    candidates, features = _load_mood_pool(market=market)
    if not candidates or not features:
        return {
            "target": {"valence": target_v, "energy": target_e},
            "recommendations": [],
            "candidate_count": 0,
            "feature_coverage": 0,
        }

    scored = []
    for t in candidates:
        tid = t.get("id")
        feat = features.get(tid)
        if not feat:
            continue
        v = feat.get("valence")
        e = feat.get("energy")
        if v is None or e is None:
            continue
        dv = float(v) - target_v
        de = float(e) - target_e
        scored.append((dv * dv + de * de, t, feat))

    scored.sort(key=lambda x: x[0])

    items = []
    for _d, t, feat in scored[:count]:
        items.append({
            "id": t.get("id"),
            "name": t.get("name", ""),
            "artists": [a["name"] for a in t.get("artists", [])],
            "album": (t.get("album") or {}).get("name", ""),
            "image": ((t.get("album") or {}).get("images") or [{}])[-1].get("url"),
            "url": (t.get("external_urls") or {}).get("spotify", ""),
            "popularity": t.get("popularity", 0),
            "features": {
                "valence": round(float(feat["valence"]), 3),
                "energy": round(float(feat["energy"]), 3),
                "tempo": round(float(feat["tempo"]), 1) if feat.get("tempo") is not None else None,
                "danceability": round(float(feat["danceability"]), 2) if feat.get("danceability") is not None else None,
            },
        })

    return {
        "target": {"valence": target_v, "energy": target_e},
        "recommendations": items,
        "candidate_count": len(candidates),
        "feature_coverage": len(features),
    }
