import logging
import os
import re
import tempfile
import threading
import time
from collections import deque

from flask import Flask, jsonify, request, send_from_directory
from spotipy.exceptions import SpotifyException

from analyze import ALLOWED_GENRES, artist_search, genre_search, genre_seed, mood_search, mood_seed, search_by_name, trending_artists
from audio_analyze import analyze_audio

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024  # 30 MB

# Behind Render/Fly/Cloud Run the client IP arrives in X-Forwarded-For.
# Only trust it when explicitly told to, otherwise it's spoofable.
if os.environ.get("TRUST_PROXY"):
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

if not app.debug:
    logging.basicConfig(level=logging.INFO)

_ALLOWED_AUDIO = {"mp3", "wav", "flac", "ogg", "m4a"}
_MARKET_RE = re.compile(r"^[A-Za-z]{2}$")


class _RateLimiter:
    """Per-IP sliding-window limiter. In-memory, so per-process — good enough
    for a single instance; swap for Redis-backed limiting if you scale out."""

    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self._hits = {}
        self._lock = threading.Lock()

    def allow(self, key):
        now = time.time()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            if len(self._hits) > 10000:
                self._hits = {k: v for k, v in self._hits.items() if v}
            return True


_api_limiter = _RateLimiter(limit=120, window_seconds=60)
_upload_limiter = _RateLimiter(limit=6, window_seconds=60)


@app.before_request
def _rate_limit():
    if not request.path.startswith("/api/"):
        return None
    ip = request.remote_addr or "unknown"
    if request.path == "/api/upload/analyze":
        if not _upload_limiter.allow(f"up:{ip}"):
            return jsonify({"error": "too many uploads, slow down"}), 429
    if not _api_limiter.allow(ip):
        return jsonify({"error": "too many requests, slow down"}), 429
    return None


@app.after_request
def _security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return resp


def _market_param():
    market = request.args.get("market", "US").strip().upper()
    return market if _MARKET_RE.match(market) else "US"


def _api_error(e, label):
    """Log the real exception, return a safe message to the client."""
    if isinstance(e, SpotifyException) and e.http_status == 429:
        return jsonify({"error": "Spotify rate limit hit — try again in a few minutes"}), 429
    app.logger.exception(label)
    return jsonify({"error": "something went wrong, try again shortly"}), 500


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/api/mood/seed")
def api_mood_seed():
    market = _market_param()
    try:
        data = mood_seed(market=market)
    except Exception as e:
        return _api_error(e, "mood seed failed")
    return jsonify(data)


@app.route("/api/mood")
def api_mood():
    valence = request.args.get("valence")
    energy = request.args.get("energy")
    if valence is None or energy is None:
        return jsonify({"error": "missing valence or energy"}), 400
    try:
        count = max(1, min(int(request.args.get("count", 10)), 25))
    except ValueError:
        count = 10
    market = _market_param()
    try:
        data = mood_search(valence, energy, count=count, market=market)
    except Exception as e:
        return _api_error(e, "mood search failed")
    if isinstance(data, dict) and data.get("error"):
        return jsonify(data), 400
    return jsonify(data)


@app.route("/api/genre/seed")
def api_genre_seed():
    genre = request.args.get("genre", "").strip().lower()
    if not genre:
        return jsonify({"error": "missing genre"}), 400
    if genre not in ALLOWED_GENRES:
        return jsonify({"error": "unknown genre"}), 400
    market = _market_param()
    try:
        data = genre_seed(genre, market=market)
    except Exception as e:
        return _api_error(e, "genre seed failed")
    return jsonify(data)


@app.route("/api/genre")
def api_genre():
    genre = request.args.get("genre", "").strip().lower()
    valence = request.args.get("valence")
    energy = request.args.get("energy")
    if not genre or valence is None or energy is None:
        return jsonify({"error": "missing genre, valence or energy"}), 400
    if genre not in ALLOWED_GENRES:
        return jsonify({"error": "unknown genre"}), 400
    try:
        count = max(1, min(int(request.args.get("count", 10)), 25))
    except ValueError:
        count = 10
    market = _market_param()
    try:
        data = genre_search(valence, energy, genre, count=count, market=market)
    except Exception as e:
        return _api_error(e, "genre search failed")
    if isinstance(data, dict) and data.get("error"):
        return jsonify(data), 400
    return jsonify(data)


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "missing query"}), 400
    if len(q) > 200:
        return jsonify({"error": "query too long"}), 400
    market = _market_param()
    try:
        count = max(1, min(int(request.args.get("count", 10)), 25))
    except ValueError:
        count = 10
    try:
        data = search_by_name(q, count=count, market=market)
    except Exception as e:
        return _api_error(e, "track search failed")
    if isinstance(data, dict) and data.get("error"):
        return jsonify(data), 404
    return jsonify(data)


@app.route("/api/artist")
def api_artist():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "missing query"}), 400
    if len(q) > 200:
        return jsonify({"error": "query too long"}), 400
    market = _market_param()
    try:
        count = max(1, min(int(request.args.get("count", 10)), 20))
    except ValueError:
        count = 10
    try:
        data = artist_search(q, count=count, market=market)
    except Exception as e:
        return _api_error(e, "artist search failed")
    if isinstance(data, dict) and data.get("error"):
        return jsonify(data), 404
    return jsonify(data)


@app.route("/api/artists/trending")
def api_artists_trending():
    try:
        data = trending_artists(limit=10)
    except Exception as e:
        return _api_error(e, "trending artists failed")
    return jsonify({"artists": data})


@app.route("/api/upload/analyze", methods=["POST"])
def api_upload_analyze():
    if "file" not in request.files:
        return jsonify({"error": "no file uploaded"}), 400
    f = request.files["file"]
    fname = f.filename or ""
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if not ext or ext not in _ALLOWED_AUDIO:
        return jsonify({"error": "unsupported file type (mp3/wav/flac/ogg/m4a)"}), 400

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp_path = tmp.name
        f.save(tmp_path)
    try:
        result = analyze_audio(tmp_path)
    except Exception as e:
        app.logger.exception("audio analysis failed")
        return jsonify({"error": "could not analyze that file — is it a valid audio file?"}), 422
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    result["filename"] = fname
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=port, debug=False)
