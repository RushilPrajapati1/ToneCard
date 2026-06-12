import math
import threading
import time

from previews import fill_previews
from reccobeats import get_features_for_spotify_ids
from spotify_client import get_client


SPOTIFY_MAX_PER_PAGE = 10

# Genres the public /api/genre endpoints accept — mirrors the chip lists in
# static/index.html and the iOS app. Internal genre pools (artist genres in
# search_by_name) are not restricted to this list.
ALLOWED_GENRES = frozenset({
    "pop", "hip hop", "rock", "r&b", "electronic", "jazz",
    "classical", "latin", "punjabi", "metal", "country", "indie",
})


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
    "dark ambient",
    "aggressive intense",
    "romantic slow",
    "party hype",
)
_POOL_TTL_SECONDS = 3600
_POOL_PER_QUERY = 20

_pool_cache = {"candidates": None, "features": None, "ts": 0.0, "market": None}
_pool_lock = threading.Lock()


def _mood_pool_fresh(market, now):
    return (
        _pool_cache["candidates"]
        and _pool_cache["features"]
        and _pool_cache["market"] == market
        and now - _pool_cache["ts"] < _POOL_TTL_SECONDS
    )


def _load_mood_pool(market="US"):
    now = time.time()
    if _mood_pool_fresh(market, now):
        return _pool_cache["candidates"], _pool_cache["features"]

    with _pool_lock:
        # Another request may have rebuilt the pool while we waited on the lock.
        now = time.time()
        if _mood_pool_fresh(market, now):
            return _pool_cache["candidates"], _pool_cache["features"]
        return _build_mood_pool(market, now)


def _build_mood_pool(market, now):
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
_GENRE_CACHE_MAX = 64  # search_by_name keys this by arbitrary artist genres — keep it bounded
_genre_lock = threading.Lock()


def _genre_pool_fresh(cached, now):
    return (
        cached
        and cached.get("candidates")
        and cached.get("features")
        and now - cached.get("ts", 0) < _GENRE_TTL
    )


def _load_genre_pool(genre, market="US"):
    key = f"{genre}:{market}"
    now = time.time()
    cached = _GENRE_CACHE.get(key)
    if _genre_pool_fresh(cached, now):
        return cached["candidates"], cached["features"]

    with _genre_lock:
        now = time.time()
        cached = _GENRE_CACHE.get(key)
        if _genre_pool_fresh(cached, now):
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

        if len(_GENRE_CACHE) >= _GENRE_CACHE_MAX:
            oldest = min(_GENRE_CACHE, key=lambda k: _GENRE_CACHE[k].get("ts", 0))
            _GENRE_CACHE.pop(oldest, None)
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
        target_v = float(valence)
        target_e = float(energy)
    except (TypeError, ValueError):
        return {"error": "invalid coordinates"}
    if math.isnan(target_v) or math.isnan(target_e):
        return {"error": "invalid coordinates"}
    target_v = max(0.0, min(1.0, target_v))
    target_e = max(0.0, min(1.0, target_e))

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
            "preview_url": t.get("preview_url"),
            "popularity": t.get("popularity", 0),
            "features": {
                "valence": round(float(feat["valence"]), 3),
                "energy": round(float(feat["energy"]), 3),
                "tempo": round(float(feat["tempo"]), 1) if feat.get("tempo") is not None else None,
                "danceability": round(float(feat["danceability"]), 2) if feat.get("danceability") is not None else None,
            },
        })

    fill_previews(items)

    return {
        "target": {"valence": target_v, "energy": target_e},
        "recommendations": items,
        "candidate_count": len(candidates),
        "feature_coverage": len(features),
    }


def _fmt_track(t, f):
    return {
        "id": t.get("id"),
        "name": t.get("name", ""),
        "artists": [a["name"] for a in t.get("artists", [])],
        "album": (t.get("album") or {}).get("name", ""),
        "image": ((t.get("album") or {}).get("images") or [{}])[-1].get("url"),
        "url": (t.get("external_urls") or {}).get("spotify", ""),
        "preview_url": t.get("preview_url"),
        "popularity": t.get("popularity", 0),
        "features": {
            "valence": round(float(f["valence"]), 3),
            "energy": round(float(f["energy"]), 3),
            "tempo": round(float(f["tempo"]), 1) if f.get("tempo") is not None else None,
            "danceability": round(float(f["danceability"]), 2) if f.get("danceability") is not None else None,
        },
    }


def search_by_name(q, count=10, market="US"):
    """Find a track by name, get its mood coordinates, and return similar tracks from its genre."""
    sp = get_client()

    raw = sp.search(q=q, type="track", limit=3, market=market)
    items = raw.get("tracks", {}).get("items", [])
    if not items:
        return {"error": "no tracks found"}

    top = items[0]
    tid = top.get("id")

    track_feats = get_features_for_spotify_ids([tid])
    feat = track_feats.get(tid)
    if not feat:
        return {"error": "could not get audio features for that track"}

    valence = float(feat.get("valence", 0.5))
    energy = float(feat.get("energy", 0.5))

    # One artist lookup to get Spotify genre tags
    artist_id = ((top.get("artists") or [{}])[0]).get("id")
    genre = None
    if artist_id:
        try:
            genres = sp.artist(artist_id).get("genres", [])
            genre = genres[0] if genres else None
        except Exception:
            pass

    if genre:
        candidates, pool_features = _load_genre_pool(genre, market=market)
    else:
        candidates, pool_features = _load_mood_pool(market=market)

    scored = []
    for t in candidates:
        cid = t.get("id")
        if cid == tid:
            continue
        cfeat = pool_features.get(cid)
        if not cfeat:
            continue
        cv = cfeat.get("valence")
        ce = cfeat.get("energy")
        if cv is None or ce is None:
            continue
        dv = float(cv) - valence
        de = float(ce) - energy
        scored.append((dv * dv + de * de, t, cfeat))
    scored.sort(key=lambda x: x[0])

    pool_points = []
    for t in candidates:
        cid = t.get("id")
        cfeat = pool_features.get(cid)
        if not cfeat:
            continue
        cv, ce = cfeat.get("valence"), cfeat.get("energy")
        if cv is None or ce is None:
            continue
        pool_points.append({
            "id": cid,
            "name": t.get("name", ""),
            "artists": [a["name"] for a in t.get("artists", [])],
            "valence": round(float(cv), 3),
            "energy": round(float(ce), 3),
        })

    target = _fmt_track(top, feat)
    similar = [_fmt_track(t, cfeat) for _, t, cfeat in scored[:count]]
    fill_previews([target] + similar)

    return {
        "track": target,
        "genre": genre,
        "similar": similar,
        "pool_points": pool_points,
        "candidate_count": len(candidates),
    }


def artist_search(query, count=10, market="US"):
    """Find an artist by name, return their profile and top tracks with mood features."""
    sp = get_client()

    raw = sp.search(q=query, type="artist", limit=1, market=market)
    items = raw.get("artists", {}).get("items", [])
    if not items:
        return {"error": "artist not found"}

    a = items[0]
    artist_info = {
        "id": a["id"],
        "name": a["name"],
        "genres": a.get("genres", []),
        "popularity": a.get("popularity", 0),
        "followers": (a.get("followers") or {}).get("total", 0),
        "image": (a.get("images") or [{}])[0].get("url"),
        "url": (a.get("external_urls") or {}).get("spotify"),
    }

    # artist_top_tracks is 403 for dev-mode Client Credentials apps.
    # Use a targeted search instead — "artist:Name" returns their tracks sorted by popularity.
    search_raw = sp.search(q=f'artist:"{a["name"]}"', type="track", limit=count, market=market)
    top_raw = search_raw.get("tracks", {}).get("items", [])
    # Filter to tracks where this artist is actually credited (search can bleed)
    artist_name_lower = a["name"].lower()
    top_raw = [
        t for t in top_raw
        if any(a2.get("name", "").lower() == artist_name_lower for a2 in t.get("artists", []))
    ][:count]

    track_ids = [t["id"] for t in top_raw if t.get("id")]
    try:
        features_map = get_features_for_spotify_ids(track_ids) if track_ids else {}
    except Exception:
        features_map = {}

    tracks = []
    points = []
    for t in top_raw:
        tid = t.get("id")
        album = t.get("album") or {}
        images = album.get("images") or []
        feat = features_map.get(tid, {})
        v = feat.get("valence")
        e = feat.get("energy")
        formatted = {
            "id": tid,
            "name": t.get("name", ""),
            "artists": [a2["name"] for a2 in t.get("artists", [])],
            "album": album.get("name", ""),
            "image": images[0].get("url") if images else None,
            "url": (t.get("external_urls") or {}).get("spotify"),
            "preview_url": t.get("preview_url"),
            "popularity": t.get("popularity", 0),
            "features": {
                "valence": round(float(v), 3) if v is not None else None,
                "energy": round(float(e), 3) if e is not None else None,
                "tempo": round(float(feat["tempo"]), 1) if feat.get("tempo") is not None else None,
                "danceability": round(float(feat["danceability"]), 2) if feat.get("danceability") is not None else None,
            },
        }
        tracks.append(formatted)
        if v is not None and e is not None:
            points.append({
                "id": tid,
                "name": t.get("name", ""),
                "artists": formatted["artists"],
                "valence": round(float(v), 3),
                "energy": round(float(e), 3),
            })

    fill_previews(tracks)

    return {"artist": artist_info, "tracks": tracks, "points": points}


# Stable Spotify artist IDs for globally popular artists.
# Fetched individually via sp.artist() (batch endpoint is 403 for dev-mode apps).
# Popularity scores are live on Spotify, so the top-10 ranking reflects current trends.
_TRENDING_SEED_IDS = [
    "06HL4z0CvFAxyc27GXpf02",  # Taylor Swift
    "3TVXtAsR1Inumwj472S9r4",  # Drake
    "1Xyo4u8uXC1ZmMpatF05PJ",  # The Weeknd
    "4q3ewBCX7sLwd24euuV69X",  # Bad Bunny
    "6qqNVTkY8uBg9cP3Jd7DAH",  # Billie Eilish
    "7tYKF4w9nC0nq9CsPZTHyP",  # SZA
    "2YZyLoL8N0Wb9xBt1NhZWg",  # Kendrick Lamar
    "74KM79TiuVKeVCqs8QtB0B",  # Sabrina Carpenter
    "246dkjvS1zLTtiykXe5h60",  # Post Malone
    "6M2wZ9GZgrQXHCFfjv46we",  # Dua Lipa
    "66CXWjxzNUsdJxJ2JdwvnR",  # Ariana Grande
    "6eUKZXaKkcviH0Ku9w2n3V",  # Ed Sheeran
    "1uNFoZAHBGtllmzznpCI3s",  # Justin Bieber
    "1McMsnEElThX1knmY4oliG",  # Olivia Rodrigo
    "6KImCVD70vtIoJWnq6nGn3",  # Harry Styles
    "3Nrfpe0tUJi4K4DXYWgMUX",  # Feid
    "0du5cEVh5yTK9QJze8zA0C",  # Bruno Mars
    "5K4W6rqBFWDnAN6FQUkS6x",  # Kanye West
    "1HY2Jd0NmPuamShAr6KMms",  # Lady Gaga
    "5pKCCKE2ajJHZ9KAiaK11H",  # Rihanna
]
_TRENDING_CACHE = {"artists": None, "ts": 0.0}
_TRENDING_TTL = 3600


def trending_artists(limit=10):
    """Fetch live popularity for a curated artist seed list; return top-N sorted by popularity."""
    now = time.time()
    if _TRENDING_CACHE["artists"] and now - _TRENDING_CACHE["ts"] < _TRENDING_TTL:
        return _TRENDING_CACHE["artists"][:limit]

    sp = get_client()
    artists = []
    for aid in _TRENDING_SEED_IDS:
        try:
            a = sp.artist(aid)
        except Exception:
            continue
        artists.append({
            "id": a["id"],
            "name": a["name"],
            "genres": a.get("genres", []),
            "popularity": a.get("popularity", 0),
            "followers": (a.get("followers") or {}).get("total", 0),
            "image": (a.get("images") or [{}])[0].get("url"),
            "url": (a.get("external_urls") or {}).get("spotify"),
        })

    _TRENDING_CACHE["artists"] = artists
    _TRENDING_CACHE["ts"] = now
    return artists[:limit]


def mood_search(valence, energy, count=10, market="US"):
    """Return tracks whose audio features sit closest to a (valence, energy) target."""
    try:
        target_v = float(valence)
        target_e = float(energy)
    except (TypeError, ValueError):
        return {"error": "invalid coordinates"}
    if math.isnan(target_v) or math.isnan(target_e):
        return {"error": "invalid coordinates"}
    target_v = max(0.0, min(1.0, target_v))
    target_e = max(0.0, min(1.0, target_e))

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
            "preview_url": t.get("preview_url"),
            "popularity": t.get("popularity", 0),
            "features": {
                "valence": round(float(feat["valence"]), 3),
                "energy": round(float(feat["energy"]), 3),
                "tempo": round(float(feat["tempo"]), 1) if feat.get("tempo") is not None else None,
                "danceability": round(float(feat["danceability"]), 2) if feat.get("danceability") is not None else None,
            },
        })

    fill_previews(items)

    return {
        "target": {"valence": target_v, "energy": target_e},
        "recommendations": items,
        "candidate_count": len(candidates),
        "feature_coverage": len(features),
    }
