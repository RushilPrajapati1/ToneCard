import json
import os
import pathlib
import re
from concurrent.futures import ThreadPoolExecutor

import requests

# Spotify zeroed out `preview_url` in Web API responses (progressively restricted
# through 2024). The public embed page still serves the 30s preview MP3 on
# p.scdn.co, so we recover it from there. This is a different host than the Web
# API, so it doesn't count against the app's shared API rate limit.
_EMBED_URL = "https://open.spotify.com/embed/track/{}"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Tonecard/1.0)"}
_TIMEOUT = 8
_MAX_WORKERS = 8

_CACHE_PATH = pathlib.Path(__file__).parent / ".preview_cache.json"

# In-memory mirror of the disk cache; loaded once at import.
# Keys are Spotify track IDs; values are preview URLs, or "" meaning
# "checked, none available" (so we don't re-scrape dead tracks).
_mem_cache: dict = {}

_DIRECT_RE = re.compile(r"https://p\.scdn\.co/mp3-preview/[A-Za-z0-9]+")
_ESCAPED_RE = re.compile(r"https:\\/\\/p\.scdn\.co\\/mp3-preview\\/[A-Za-z0-9]+")


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


def _scrape_preview(track_id):
    """Return the embed-page preview MP3 URL for a Spotify track id, or '' if none."""
    try:
        r = requests.get(_EMBED_URL.format(track_id), headers=_HEADERS, timeout=_TIMEOUT)
        if r.status_code != 200:
            return ""
        text = r.text
        m = _DIRECT_RE.search(text)
        if m:
            return m.group(0)
        m = _ESCAPED_RE.search(text)
        if m:
            return m.group(0).replace("\\/", "/")
    except Exception:
        pass
    return ""


def fill_previews(tracks):
    """Populate `preview_url` on formatted track dicts that lack one.

    Uses the embed-page workaround, fetched concurrently for the uncached ids.
    Disk-cached by Spotify ID (negative results included) so repeated lookups
    skip the round-trip across server restarts. Mutates and returns the list.
    """
    pending = []
    for t in tracks:
        if not isinstance(t, dict) or t.get("preview_url"):
            continue
        tid = t.get("id")
        if not tid:
            continue
        if tid in _mem_cache:
            t["preview_url"] = _mem_cache[tid] or None
        else:
            pending.append(t)

    if pending:
        ids = [t["id"] for t in pending]
        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(ids))) as ex:
            resolved = dict(zip(ids, ex.map(_scrape_preview, ids)))
        for t in pending:
            url = resolved.get(t["id"], "")
            _mem_cache[t["id"]] = url
            t["preview_url"] = url or None
        _save_disk_cache()

    return tracks
