from flask import Flask, jsonify, request, send_from_directory

from analyze import genre_search, genre_seed, mood_search, mood_seed

app = Flask(__name__, static_folder="static", static_url_path="")


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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
