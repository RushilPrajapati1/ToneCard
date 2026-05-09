from spotify_client import get_client
from filter_search import get_features_for_spotify_ids
from vibe_profile import build_vibe_profile, feature_closeness_score, text_match_score


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


def _vibe_score(track, features, profile):
    haystack = track["name"].lower()
    haystack += " " + " ".join(a["name"].lower() for a in track.get("artists", []))
    if track.get("album"):
        haystack += " " + track["album"].get("name", "").lower()

    text_score = text_match_score(haystack, profile["tokens"])
    feature_score = feature_closeness_score(features or {}, profile["targets"])
    popularity_score = max(track.get("popularity", 0), 0) / 100.0

    # Weight text + audio equally; keep a mild popularity tie-breaker.
    return (0.45 * text_score) + (0.45 * feature_score) + (0.10 * popularity_score)


def improved_search(query, vibe_keywords=None, limit=10, market="US"):
    """Search Spotify and rank by vibe text + audio profile closeness."""
    candidate_pool = max(min(limit * 4, 50), limit)
    raw = _search_tracks(query, total=candidate_pool, market=market)
    if not raw:
        return []

    profile = build_vibe_profile(vibe_keywords)
    if not profile:
        raw.sort(key=lambda t: t.get("popularity", 0), reverse=True)
        return raw[:limit]

    spotify_ids = [t.get("id") for t in raw if t.get("id")]
    features_by_id = get_features_for_spotify_ids(spotify_ids) if spotify_ids else {}

    raw.sort(
        key=lambda t: _vibe_score(
            t,
            features_by_id.get(t.get("id")),
            profile,
        ),
        reverse=True,
    )

    return raw[:limit]
