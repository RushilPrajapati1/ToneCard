from spotify_client import get_client


def _search_tracks(query, limit=10, market="US"):
    sp = get_client()
    results = sp.search(q=query, type="track", limit=min(limit, 10), market=market)
    return results["tracks"]["items"]


def _vibe_score(track, vibe_keywords):
    haystack = track["name"].lower()
    haystack += " " + " ".join(a["name"].lower() for a in track.get("artists", []))
    if track.get("album"):
        haystack += " " + track["album"].get("name", "").lower()

    keyword_hits = sum(10 for kw in vibe_keywords if kw.lower() in haystack)
    popularity = track.get("popularity", 0) * 0.1
    return keyword_hits + popularity


def improved_search(query, vibe_keywords=None, limit=10, market="US"):
    """Search Spotify and re-rank results by vibe keyword matches + popularity.

    vibe_keywords match against track name, artist name, and album name.
    """
    raw = _search_tracks(query, limit=10, market=market)
    if not raw:
        return []

    if vibe_keywords:
        raw.sort(key=lambda t: _vibe_score(t, vibe_keywords), reverse=True)
    else:
        raw.sort(key=lambda t: t.get("popularity", 0), reverse=True)

    return raw[:limit]
