import requests

RECCOBEATS_BASE = "https://api.reccobeats.com/v1"
TIMEOUT = 15
RECCOBEATS_BATCH = 40  # ReccoBeats caps at 40 ids per call


def _chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


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
