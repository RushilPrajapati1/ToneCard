import os
import tempfile

from flask import Flask, jsonify, request, send_from_directory

from analyze import artist_search, genre_search, genre_seed, mood_search, mood_seed, search_by_name, trending_artists
from audio_analyze import analyze_audio

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024  # 30 MB

_ALLOWED_AUDIO = {"mp3", "wav", "flac", "ogg", "m4a"}


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/mood/seed")
def api_mood_seed():
    market = request.args.get("market", "US")
    try:
        data = mood_seed(market=market)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
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
    market = request.args.get("market", "US")
    try:
        data = mood_search(valence, energy, count=count, market=market)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if isinstance(data, dict) and data.get("error"):
        return jsonify(data), 400
    return jsonify(data)


@app.route("/api/genre/seed")
def api_genre_seed():
    genre = request.args.get("genre", "").strip()
    if not genre:
        return jsonify({"error": "missing genre"}), 400
    market = request.args.get("market", "US")
    try:
        data = genre_seed(genre, market=market)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(data)


@app.route("/api/genre")
def api_genre():
    genre = request.args.get("genre", "").strip()
    valence = request.args.get("valence")
    energy = request.args.get("energy")
    if not genre or valence is None or energy is None:
        return jsonify({"error": "missing genre, valence or energy"}), 400
    try:
        count = max(1, min(int(request.args.get("count", 10)), 25))
    except ValueError:
        count = 10
    market = request.args.get("market", "US")
    try:
        data = genre_search(valence, energy, genre, count=count, market=market)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if isinstance(data, dict) and data.get("error"):
        return jsonify(data), 400
    return jsonify(data)


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "missing query"}), 400
    market = request.args.get("market", "US")
    try:
        count = max(1, min(int(request.args.get("count", 10)), 25))
    except ValueError:
        count = 10
    try:
        data = search_by_name(q, count=count, market=market)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if isinstance(data, dict) and data.get("error"):
        return jsonify(data), 404
    return jsonify(data)


@app.route("/api/artist")
def api_artist():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "missing query"}), 400
    market = request.args.get("market", "US")
    try:
        count = max(1, min(int(request.args.get("count", 10)), 20))
    except ValueError:
        count = 10
    try:
        data = artist_search(q, count=count, market=market)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if isinstance(data, dict) and data.get("error"):
        return jsonify(data), 404
    return jsonify(data)


@app.route("/api/artists/trending")
def api_artists_trending():
    try:
        data = trending_artists(limit=10)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
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
        return jsonify({"error": f"analysis failed: {e}"}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    result["filename"] = fname
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
