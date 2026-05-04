import os

from flask import Flask, jsonify, request, redirect, send_from_directory

from analyze import analyze, VALID_RANGES
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
