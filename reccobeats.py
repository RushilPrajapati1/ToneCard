import json
import os
import pathlib
import tempfile

import requests

RECCOBEATS_BASE = "https://api.reccobeats.com/v1"
TIMEOUT = 15
RECCOBEATS_BATCH = 40  # ReccoBeats caps at 40 ids per call

_CACHE_PATH = pathlib.Path(__file__).parent / ".reccobeats_cache.json"

# In-memory mirror of the disk cache; loaded once at import.
# Keys are Spotify track IDs; values are ReccoBeats feature dicts.
_mem_cache: dict = {}


def _load_disk_cache() -> None:
    if _CACHE_PATH.exists():
        try:
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                _mem_cache.update(json.load(f))
        except Exception:
            pass


def _save_disk_cache() -> None:
    tmp = _CACHE_PATH.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_mem_cache, f, separators=(",", ":"))
        os.replace(tmp, _CACHE_PATH)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


_load_disk_cache()


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
    have are silently dropped. Results are disk-cached by Spotify ID so repeated
    lookups across server restarts skip the ReccoBeats round-trip entirely.
    """
    uncached = [sid for sid in spotify_ids if sid not in _mem_cache]

    if uncached:
        s2r = _spotify_to_reccobeats_map(uncached)
        if s2r:
            feats = _fetch_features(list(s2r.values()))
            new_entries = {sid: feats[rid] for sid, rid in s2r.items() if rid in feats}
            _mem_cache.update(new_entries)
            if new_entries:
                _save_disk_cache()

    return {sid: _mem_cache[sid] for sid in spotify_ids if sid in _mem_cache}
