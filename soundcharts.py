import json
import os

import requests

SOUNDCHARTS_BASE = "https://customer.api.soundcharts.com"
TIMEOUT = 15

_CACHE_FILE = "soundcharts_cache.json"
_disk_cache: dict = {}
_cache_loaded = False


def _load_cache():
    global _disk_cache, _cache_loaded
    if _cache_loaded:
        return
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE) as f:
                _disk_cache = json.load(f)
        except Exception:
            _disk_cache = {}
    _cache_loaded = True


def _save_cache():
    try:
        with open(_CACHE_FILE, "w") as f:
            json.dump(_disk_cache, f)
    except Exception:
        pass


def _headers():
    return {
        "x-app-id": os.environ.get("SOUNDCHARTS_APP_ID", ""),
        "x-api-key": os.environ.get("SOUNDCHARTS_API_KEY", ""),
    }


def _extract_features(song_obj):
    """Pull audio feature fields from a SoundCharts song object.

    Response shape: {"type": "song", "object": {..., "audio": {valence, energy, ...}}}
    Audio features live under object["audio"].
    """
    af = song_obj.get("audio") or {}
    return {
        "valence":      af.get("valence"),
        "energy":       af.get("energy"),
        "tempo":        af.get("tempo"),
        "danceability": af.get("danceability"),
        "key":          af.get("key"),
        "mode":         af.get("mode"),
        "acousticness": af.get("acousticness"),
    }


def _fetch_from_api(spotify_id):
    """Fetch one track from SoundCharts by Spotify ID. Returns features dict or None."""
    r = requests.get(
        f"{SOUNDCHARTS_BASE}/api/v2.25/song/by-platform/spotify/{spotify_id}",
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if r.status_code in (404, 422):
        return None
    r.raise_for_status()
    body = r.json()
    # Response: {"type": "song", "object": {..., "audio": {...}}, "errors": []}
    song = body.get("object") or {}
    return _extract_features(song)


def get_features_for_spotify_ids(spotify_ids):
    """Fetch SoundCharts audio features for a list of Spotify track IDs.

    Results are persisted to disk so each track ID is only ever fetched once,
    protecting the 1,000-call free-tier budget. Tracks not in SoundCharts are
    cached as None to prevent repeat calls.

    Returns dict mapping spotify_id -> features dict.
    """
    _load_cache()

    uncached = [sid for sid in spotify_ids if sid not in _disk_cache]
    new_entries = 0

    for sid in uncached:
        try:
            feat = _fetch_from_api(sid)
            _disk_cache[sid] = feat   # None means "not in SoundCharts" — still cache it
            new_entries += 1
        except Exception:
            # Network / auth errors: don't cache, will retry next time
            continue

    if new_entries:
        _save_cache()

    return {
        sid: _disk_cache[sid]
        for sid in spotify_ids
        if _disk_cache.get(sid) and _disk_cache[sid].get("valence") is not None
    }
