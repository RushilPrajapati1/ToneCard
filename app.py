from flask import Flask, jsonify, request, send_from_directory

from analyze import mood_search, mood_seed

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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
