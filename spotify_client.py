import os

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:5050/callback")
USER_SCOPES = "user-top-read user-read-recently-played user-library-read user-read-private"

_client = None
_user_oauth = None


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

    _require_credentials()
    auth = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    _client = spotipy.Spotify(auth_manager=auth)
    return _client


def get_user_oauth():
    global _user_oauth
    if _user_oauth is not None:
        return _user_oauth

    _require_credentials()
    _user_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=USER_SCOPES,
        cache_path=".cache-user",
        open_browser=False,
    )
    return _user_oauth


def get_user_client():
    oauth = get_user_oauth()
    token = oauth.get_cached_token()
    if not token:
        return None
    return spotipy.Spotify(auth=token["access_token"])
