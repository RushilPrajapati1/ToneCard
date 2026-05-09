import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from filter_search import (
    _spotify_to_reccobeats_map,
    get_features_for_spotify_ids,
    reccobeats_recommendations,
    spotify_id_from_href,
)
from search import _search_tracks
from spotify_client import get_client, get_user_client
from vibe_profile import build_vibe_profile, text_match_score

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
        genre_counter.update(a.get("genres") or [])

    track_ids = [t["id"] for t in top_tracks if t.get("id")]
    try:
        features_by_id = get_features_for_spotify_ids(track_ids) if track_ids else {}
    except Exception:
        features_by_id = {}

    def _avg(key, ndigits):
        vals = [f.get(key) for f in features_by_id.values() if f.get(key) is not None]
        return round(sum(vals) / len(vals), ndigits) if vals else None

    return {
        "time_range": time_range,
        "top_tracks": [_track_summary(t) for t in top_tracks],
        "top_artists": [_artist_summary(a) for a in top_artists],
        "recent": [_track_summary(p.get("track")) for p in recent if p.get("track")],
        "top_genres": [
            {"genre": g, "count": c} for g, c in genre_counter.most_common(15)
        ],
        "stats": {
            "avg_tempo": _avg("tempo", 1),
            "avg_energy": _avg("energy", 2),
            "avg_danceability": _avg("danceability", 2),
            "feature_coverage": len(features_by_id),
            "feature_total": len(track_ids),
        },
    }


def list_playlists():
    """Return all playlists the user owns or follows."""
    sp = get_user_client()
    if sp is None:
        return None

    items = []
    offset = 0
    while True:
        page = sp.current_user_playlists(limit=50, offset=offset)
        items.extend(page.get("items") or [])
        if not page.get("next"):
            break
        offset += 50

    return [
        {
            "id": p["id"],
            "name": p.get("name", ""),
            "image": (p.get("images") or [{}])[0].get("url"),
            "track_count": (p.get("tracks") or {}).get("total", 0),
            "owner": (p.get("owner") or {}).get("display_name") or "",
            "url": (p.get("external_urls") or {}).get("spotify", ""),
        }
        for p in items
        if p
    ]


PLAYLIST_TRACK_CAP = 100  # bound the work for very large playlists


def _playlist_track_ids(sp, playlist_id, max_tracks=PLAYLIST_TRACK_CAP):
    track_ids = []
    offset = 0
    while len(track_ids) < max_tracks:
        page = sp.playlist_items(
            playlist_id,
            limit=100,
            offset=offset,
            fields="items(item(id,type),track(id,type)),next",
        )
        page_items = page.get("items") or []
        if not page_items:
            break
        for it in page_items:
            t = it.get("item") or it.get("track") or {}
            if t.get("type") != "track":
                continue
            tid = t.get("id")
            if tid:
                track_ids.append(tid)
                if len(track_ids) >= max_tracks:
                    break
        if not page.get("next"):
            break
        offset += 100
    return track_ids


def _avg_feature(features_by_id, key, ndigits):
    vals = [f.get(key) for f in features_by_id.values() if f.get(key) is not None]
    return round(sum(vals) / len(vals), ndigits) if vals else None


def playlist_stats(playlist_id, max_tracks=PLAYLIST_TRACK_CAP):
    """Average tempo / energy / danceability over (up to) the first max_tracks."""
    sp = get_user_client()
    if sp is None:
        return None

    track_ids = _playlist_track_ids(sp, playlist_id, max_tracks)

    try:
        features_by_id = get_features_for_spotify_ids(track_ids) if track_ids else {}
    except Exception:
        features_by_id = {}

    return {
        "track_count": len(track_ids),
        "feature_coverage": len(features_by_id),
        "max_tracks": max_tracks,
        "stats": {
            "avg_tempo": _avg_feature(features_by_id, "tempo", 1),
            "avg_energy": _avg_feature(features_by_id, "energy", 2),
            "avg_danceability": _avg_feature(features_by_id, "danceability", 2),
        },
    }


def _fetch_tracks_parallel(track_ids, workers=8):
    """Spotify's /v1/tracks?ids= batch is 403 for new apps, so fan out single fetches."""
    if not track_ids:
        return {}
    sp = get_client()

    def _one(tid):
        try:
            return tid, sp.track(tid)
        except Exception:
            return tid, None

    out = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for tid, t in pool.map(_one, track_ids):
            if t:
                out[tid] = t
    return out


def playlist_recommendations(playlist_id, count=10, candidate_size=30):
    """Find tracks with similar tempo/energy/danceability to the given playlist."""
    sp = get_user_client()
    if sp is None:
        return None

    track_ids = _playlist_track_ids(sp, playlist_id)
    if not track_ids:
        return {"recommendations": [], "playlist_stats": None}

    pl_features = get_features_for_spotify_ids(track_ids)
    avg_tempo = _avg_feature(pl_features, "tempo", 1)
    avg_energy = _avg_feature(pl_features, "energy", 2)
    avg_dance = _avg_feature(pl_features, "danceability", 2)

    seed_pool = [tid for tid in track_ids if tid in pl_features] or track_ids
    seeds = random.sample(seed_pool, min(5, len(seed_pool)))
    s2r = _spotify_to_reccobeats_map(seeds)
    recco_seed_ids = list(s2r.values())
    if not recco_seed_ids:
        return {
            "recommendations": [],
            "playlist_stats": {
                "avg_tempo": avg_tempo, "avg_energy": avg_energy, "avg_danceability": avg_dance
            },
        }

    raw = reccobeats_recommendations(recco_seed_ids, size=candidate_size)

    in_playlist = set(track_ids)
    cand_meta = {}
    for c in raw:
        sid = spotify_id_from_href(c.get("href"))
        if not sid or sid in in_playlist or sid in cand_meta:
            continue
        cand_meta[sid] = c

    cand_ids = list(cand_meta.keys())
    if not cand_ids:
        return {
            "recommendations": [],
            "playlist_stats": {
                "avg_tempo": avg_tempo, "avg_energy": avg_energy, "avg_danceability": avg_dance
            },
        }

    cand_features = get_features_for_spotify_ids(cand_ids)

    sp_tracks = _fetch_tracks_parallel(cand_ids)

    def _distance(feat):
        d = 0.0
        if avg_tempo is not None and feat.get("tempo") is not None:
            d += abs(feat["tempo"] - avg_tempo) / 200.0
        if avg_energy is not None and feat.get("energy") is not None:
            d += abs(feat["energy"] - avg_energy)
        if avg_dance is not None and feat.get("danceability") is not None:
            d += abs(feat["danceability"] - avg_dance)
        return d

    items = []
    for sid, meta in cand_meta.items():
        feat = cand_features.get(sid)
        if not feat:
            continue
        track = sp_tracks.get(sid) or {}
        items.append({
            "id": sid,
            "name": track.get("name") or meta.get("trackTitle", ""),
            "artists": [a["name"] for a in (track.get("artists") or meta.get("artists") or [])],
            "album": (track.get("album") or {}).get("name", ""),
            "image": ((track.get("album") or {}).get("images") or [{}])[-1].get("url"),
            "url": meta.get("href") or (track.get("external_urls") or {}).get("spotify", ""),
            "features": {
                "tempo": round(feat["tempo"], 1) if feat.get("tempo") is not None else None,
                "energy": round(feat["energy"], 2) if feat.get("energy") is not None else None,
                "danceability": round(feat["danceability"], 2) if feat.get("danceability") is not None else None,
            },
            "_score": _distance(feat),
        })

    items.sort(key=lambda x: x["_score"])
    for x in items:
        x.pop("_score", None)

    return {
        "recommendations": items[:count],
        "playlist_stats": {
            "avg_tempo": avg_tempo,
            "avg_energy": avg_energy,
            "avg_danceability": avg_dance,
        },
        "candidate_count": len(cand_meta),
        "feature_coverage": len(cand_features),
    }


def playlist_vibe_search(playlist_id, vibe, count=10, candidate_size=40, market="US"):
    """Search Spotify by vibe text, biased toward the playlist's audio profile."""
    vibe = (vibe or "").strip()
    if not vibe:
        return {"error": "missing vibe"}

    sp = get_user_client()
    if sp is None:
        return None

    track_ids = _playlist_track_ids(sp, playlist_id)
    pl_features = get_features_for_spotify_ids(track_ids) if track_ids else {}
    avg_tempo = _avg_feature(pl_features, "tempo", 1)
    avg_energy = _avg_feature(pl_features, "energy", 2)
    avg_dance = _avg_feature(pl_features, "danceability", 2)

    raw = _search_tracks(vibe, total=candidate_size, market=market)
    in_playlist = set(track_ids)
    candidates = [t for t in raw if t.get("id") and t["id"] not in in_playlist]

    cand_ids = [t["id"] for t in candidates]
    cand_features = get_features_for_spotify_ids(cand_ids) if cand_ids else {}

    profile = build_vibe_profile([vibe])
    tokens = profile["tokens"] if profile else []

    has_pl_targets = any(v is not None for v in (avg_tempo, avg_energy, avg_dance))

    def _score(track):
        feat = cand_features.get(track["id"]) or {}
        haystack = track.get("name", "").lower()
        haystack += " " + " ".join(a["name"].lower() for a in track.get("artists", []))
        if track.get("album"):
            haystack += " " + (track["album"].get("name") or "").lower()
        text_score = text_match_score(haystack, tokens)

        d = 0.0
        n = 0
        if avg_tempo is not None and feat.get("tempo") is not None:
            d += abs(feat["tempo"] - avg_tempo) / 100.0; n += 1
        if avg_energy is not None and feat.get("energy") is not None:
            d += abs(feat["energy"] - avg_energy); n += 1
        if avg_dance is not None and feat.get("danceability") is not None:
            d += abs(feat["danceability"] - avg_dance); n += 1
        playlist_score = max(0.0, 1.0 - (d / n)) if n else 0.0

        popularity_score = max(track.get("popularity", 0), 0) / 100.0

        if has_pl_targets:
            return (0.45 * text_score) + (0.45 * playlist_score) + (0.10 * popularity_score)
        return (0.75 * text_score) + (0.25 * popularity_score)

    candidates.sort(key=_score, reverse=True)

    items = []
    for t in candidates[:count]:
        feat = cand_features.get(t["id"]) or {}
        items.append({
            "id": t["id"],
            "name": t.get("name", ""),
            "artists": [a["name"] for a in t.get("artists", [])],
            "album": (t.get("album") or {}).get("name", ""),
            "image": ((t.get("album") or {}).get("images") or [{}])[-1].get("url"),
            "url": (t.get("external_urls") or {}).get("spotify", ""),
            "popularity": t.get("popularity", 0),
            "features": {
                "tempo": round(feat["tempo"], 1) if feat.get("tempo") is not None else None,
                "energy": round(feat["energy"], 2) if feat.get("energy") is not None else None,
                "danceability": round(feat["danceability"], 2) if feat.get("danceability") is not None else None,
            },
        })

    return {
        "vibe": vibe,
        "recommendations": items,
        "playlist_stats": {
            "avg_tempo": avg_tempo,
            "avg_energy": avg_energy,
            "avg_danceability": avg_dance,
        },
        "candidate_count": len(candidates),
        "feature_coverage": len(cand_features),
    }
