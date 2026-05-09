import os

from flask import Flask, jsonify, request, redirect, send_from_directory

from analyze import (
    analyze,
    list_playlists,
    playlist_recommendations,
    playlist_stats,
    playlist_vibe_search,
    VALID_RANGES,
)
from filter_search import filter_search
from search import improved_search
from spotify_client import get_user_client, get_user_oauth

app = Flask(__name__, static_folder="static", static_url_path="")

USER_CACHE_FILE = ".cache-user"


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "missing q"}), 400

    vibe = request.args.get("vibe", "").split()
    try:
        limit = max(1, min(int(request.args.get("limit", 10)), 10))
    except ValueError:
        limit = 10
    market = request.args.get("market", "US")

    try:
        tracks = improved_search(query, vibe_keywords=vibe, limit=limit, market=market)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    results = [
        {
            "name": t["name"],
            "artists": [a["name"] for a in t.get("artists", [])],
            "album": t.get("album", {}).get("name", ""),
            "image": (t.get("album", {}).get("images") or [{}])[-1].get("url"),
            "popularity": t.get("popularity", 0),
            "url": t.get("external_urls", {}).get("spotify", ""),
        }
        for t in tracks
    ]
    return jsonify({"results": results})


@app.route("/login")
def login():
    oauth = get_user_oauth()
    return redirect(oauth.get_authorize_url())


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        return redirect(f"/?tab=mine&auth_error={error}")
    code = request.args.get("code")
    if not code:
        return redirect("/?tab=mine&auth_error=missing_code")

    oauth = get_user_oauth()
    try:
        oauth.get_access_token(code, as_dict=False, check_cache=False)
    except Exception as e:
        return redirect(f"/?tab=mine&auth_error={e}")
    return redirect("/?tab=mine")


@app.route("/logout", methods=["POST"])
def logout():
    if os.path.exists(USER_CACHE_FILE):
        os.remove(USER_CACHE_FILE)
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    sp = get_user_client()
    if sp is None:
        return jsonify({"authenticated": False})
    try:
        me = sp.current_user()
    except Exception:
        return jsonify({"authenticated": False})
    return jsonify(
        {
            "authenticated": True,
            "display_name": me.get("display_name") or me.get("id"),
            "image": (me.get("images") or [{}])[0].get("url") if me.get("images") else None,
            "country": me.get("country"),
            "url": me.get("external_urls", {}).get("spotify", ""),
        }
    )


@app.route("/api/analyze")
def api_analyze():
    time_range = request.args.get("time_range", "medium_term")
    if time_range not in VALID_RANGES:
        time_range = "medium_term"
    try:
        limit = max(5, min(int(request.args.get("limit", 10)), 20))
    except ValueError:
        limit = 10

    try:
        data = analyze(time_range=time_range, limit=limit)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if data is None:
        return jsonify({"error": "not_authenticated"}), 401
    return jsonify(data)


@app.route("/api/playlists")
def api_playlists():
    try:
        data = list_playlists()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if data is None:
        return jsonify({"error": "not_authenticated"}), 401
    return jsonify({"playlists": data})


@app.route("/api/playlists/<playlist_id>/stats")
def api_playlist_stats(playlist_id):
    try:
        data = playlist_stats(playlist_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if data is None:
        return jsonify({"error": "not_authenticated"}), 401
    return jsonify(data)


@app.route("/api/playlists/<playlist_id>/recommendations")
def api_playlist_recommendations(playlist_id):
    try:
        count = max(1, min(int(request.args.get("count", 10)), 25))
    except ValueError:
        count = 10
    try:
        data = playlist_recommendations(playlist_id, count=count)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if data is None:
        return jsonify({"error": "not_authenticated"}), 401
    return jsonify(data)


@app.route("/api/playlists/<playlist_id>/vibe")
def api_playlist_vibe(playlist_id):
    vibe = request.args.get("vibe", "").strip()
    if not vibe:
        return jsonify({"error": "missing vibe"}), 400
    try:
        count = max(1, min(int(request.args.get("count", 10)), 25))
    except ValueError:
        count = 10
    market = request.args.get("market", "US")
    try:
        data = playlist_vibe_search(playlist_id, vibe, count=count, market=market)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if data is None:
        return jsonify({"error": "not_authenticated"}), 401
    if isinstance(data, dict) and data.get("error"):
        return jsonify(data), 400
    return jsonify(data)


def _parse_float(name):
    v = request.args.get(name)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _parse_int(name):
    v = request.args.get(name)
    if v is None or v == "":
        return None
    try:
        return int(v)
    except ValueError:
        return None


@app.route("/api/filter")
def api_filter():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "missing q"}), 400
    vibe = request.args.get("vibe", "").split()

    filters = {
        "tempo_min": _parse_float("tempo_min"),
        "tempo_max": _parse_float("tempo_max"),
        "energy_min": _parse_float("energy_min"),
        "energy_max": _parse_float("energy_max"),
        "danceability_min": _parse_float("danceability_min"),
        "danceability_max": _parse_float("danceability_max"),
        "valence_min": _parse_float("valence_min"),
        "valence_max": _parse_float("valence_max"),
        "acousticness_min": _parse_float("acousticness_min"),
        "acousticness_max": _parse_float("acousticness_max"),
        "key": _parse_int("key"),
        "mode": _parse_int("mode"),
    }

    try:
        limit = max(1, min(int(request.args.get("limit", 10)), 20))
    except ValueError:
        limit = 10
    market = request.args.get("market", "US")

    try:
        outcome = filter_search(query, filters, limit=limit, market=market, vibe_keywords=vibe)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    response = []
    for track, feat, _score in outcome["results"]:
        response.append(
            {
                "name": track["name"],
                "artists": [a["name"] for a in track.get("artists", [])],
                "album": track.get("album", {}).get("name", ""),
                "image": (track.get("album", {}).get("images") or [{}])[-1].get("url"),
                "url": track.get("external_urls", {}).get("spotify", ""),
                "popularity": track.get("popularity", 0),
                "features": {
                    "tempo": round(feat.get("tempo", 0), 1) if feat.get("tempo") is not None else None,
                    "key": feat.get("key"),
                    "mode": feat.get("mode"),
                    "energy": round(feat.get("energy", 0), 2) if feat.get("energy") is not None else None,
                    "danceability": round(feat.get("danceability", 0), 2) if feat.get("danceability") is not None else None,
                    "valence": round(feat.get("valence", 0), 2) if feat.get("valence") is not None else None,
                    "acousticness": round(feat.get("acousticness", 0), 2) if feat.get("acousticness") is not None else None,
                },
            }
        )

    return jsonify(
        {
            "results": response,
            "candidate_count": outcome["candidate_count"],
            "feature_coverage": outcome["feature_coverage"],
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
