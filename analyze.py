from collections import Counter

from spotify_client import get_user_client

VALID_RANGES = ("short_term", "medium_term", "long_term")


def _track_summary(t):
    if not t:
        return None
    return {
        "name": t.get("name", ""),
        "artists": [a["name"] for a in t.get("artists", [])],
        "album": t.get("album", {}).get("name", ""),
        "image": (t.get("album", {}).get("images") or [{}])[-1].get("url"),
        "url": t.get("external_urls", {}).get("spotify", ""),
        "popularity": t.get("popularity", 0),
    }


def _artist_summary(a):
    return {
        "name": a.get("name", ""),
        "image": (a.get("images") or [{}])[-1].get("url"),
        "genres": a.get("genres", []),
        "popularity": a.get("popularity", 0),
        "followers": a.get("followers", {}).get("total", 0),
        "url": a.get("external_urls", {}).get("spotify", ""),
    }


def analyze(time_range="medium_term", limit=10):
    """Pull top tracks, top artists, recently played, and aggregated genres."""
    if time_range not in VALID_RANGES:
        time_range = "medium_term"

    sp = get_user_client()
    if sp is None:
        return None

    top_tracks = sp.current_user_top_tracks(time_range=time_range, limit=limit)["items"]
    top_artists = sp.current_user_top_artists(time_range=time_range, limit=limit)["items"]
    recent = sp.current_user_recently_played(limit=limit)["items"]

    genre_counter = Counter()
    for a in top_artists:
        genre_counter.update(a.get("genres", []))

    avg_popularity_tracks = (
        round(sum(t.get("popularity", 0) for t in top_tracks) / len(top_tracks), 1)
        if top_tracks
        else 0
    )
    avg_popularity_artists = (
        round(sum(a.get("popularity", 0) for a in top_artists) / len(top_artists), 1)
        if top_artists
        else 0
    )

    return {
        "time_range": time_range,
        "top_tracks": [_track_summary(t) for t in top_tracks],
        "top_artists": [_artist_summary(a) for a in top_artists],
        "recent": [_track_summary(p.get("track")) for p in recent if p.get("track")],
        "top_genres": [
            {"genre": g, "count": c} for g, c in genre_counter.most_common(15)
        ],
        "stats": {
            "avg_track_popularity": avg_popularity_tracks,
            "avg_artist_popularity": avg_popularity_artists,
            "unique_genres": len(genre_counter),
        },
    }
