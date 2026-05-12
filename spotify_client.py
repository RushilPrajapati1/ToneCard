import os

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

_client = None


def _ensure_spotify_no_proxy():
    """Avoid broken global proxies for Spotify token calls."""
    required_hosts = {"accounts.spotify.com", "api.spotify.com", "open.spotify.com"}

    current = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    entries = {h.strip() for h in current.split(",") if h.strip()}
    merged = entries | required_hosts
    value = ",".join(sorted(merged))

    os.environ["NO_PROXY"] = value
    os.environ["no_proxy"] = value


def _disable_proxy_env_for_spotify():
    """Hard-disable env proxy variables that break local Spotify auth flows."""
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        if key in os.environ:
            os.environ.pop(key, None)


def _require_credentials():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "Missing Spotify credentials. Set SPOTIFY_CLIENT_ID and "
            "SPOTIFY_CLIENT_SECRET in your environment or in a .env file. "
            "See .env.example."
        )


def get_client():
    global _client
    if _client is not None:
        return _client

    _ensure_spotify_no_proxy()
    _disable_proxy_env_for_spotify()
    _require_credentials()
    auth = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    _client = spotipy.Spotify(auth_manager=auth, retries=0, status_retries=0, requests_timeout=10)
    return _client
