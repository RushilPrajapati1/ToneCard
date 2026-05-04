# Spotify Search APP

A small Flask + React web app for Spotify with three modes:

1. **Search** — vibe-keyword re-ranking on top of Spotify search.
2. **Filter** — search by audio features Spotify's UI doesn't expose: BPM, key, mode, energy, danceability, valence, acousticness. Audio features come from [ReccoBeats](https://reccobeats.com), since Spotify deprecated `/audio-features` for new apps in late 2024.
3. **My Music** — OAuth into your account to see top tracks, top artists, top genres, and recent plays.

A CLI for the basic search is also included.

## Prerequisites

- Python 3.9+
- A Spotify developer app (free): https://developer.spotify.com/dashboard

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your Spotify app credentials.** Copy `.env.example` to `.env` and fill in your `CLIENT_ID` / `CLIENT_SECRET` from https://developer.spotify.com/dashboard:

   ```bash
   cp .env.example .env
   # then edit .env and paste your real values
   ```

   The `.env` file is gitignored. The app loads it automatically via `python-dotenv`. Alternatively, export the vars directly:

   ```bash
   export SPOTIFY_CLIENT_ID=...
   export SPOTIFY_CLIENT_SECRET=...
   ```

4. **Add the OAuth redirect URI.** The "My Music" tab logs into your personal Spotify account, so your Spotify app needs a redirect URI registered. In the Spotify Developer Dashboard:

   - Open your app → **Edit Settings** → **Redirect URIs**
   - Add: `http://127.0.0.1:5050/callback`
   - **Save**

   Without this, the Connect Spotify flow will fail with `INVALID_CLIENT: Invalid redirect URI`.

   The OAuth scopes used are `user-top-read`, `user-read-recently-played`, `user-library-read`, and `user-read-private`.

## Run the web app

```bash
python app.py
```

Then open http://127.0.0.1:5050 in your browser. You'll see two tabs:

- **Search** — vibe-keyword search (no login required).
- **Filter** — set ranges for BPM, energy, danceability, valence, acousticness, plus optional key and mode. Backend pulls 50 candidates from Spotify, fetches audio features from ReccoBeats, drops anything outside your filters, and ranks by closeness to the range midpoints. Each result shows the matched feature values inline.
- **My Music** — click **Connect Spotify** to authorize. After redirect, you'll see your top tracks, top artists, top genres (chips), recent plays, and aggregate stats. A time-range selector switches between *Last 4 weeks*, *Last 6 months*, and *All time*.

Click **Disconnect** to clear the cached token (`.cache-user`).

## Run the CLI (search only)

```bash
python main.py "rainy day jazz"
```

Re-rank by vibe keywords:

```bash
python main.py "rainy day jazz" --vibe chill lofi mellow
```

All options:

```bash
python main.py "<query>" [--vibe kw1 kw2 ...] [--limit N] [--market US]
```

- `query` — required search string
- `--vibe` — keywords used to re-rank results (matched against track/artist/album names)
- `--limit` — number of results to print (default: 10)
- `--market` — ISO market code (default: `US`)

## API endpoints (web app)

| Method | Path             | Purpose                                                             |
| ------ | ---------------- | ------------------------------------------------------------------- |
| GET    | `/api/search`    | Vibe search. Query params: `q`, `vibe`, `limit`, `market`.          |
| GET    | `/api/filter`    | Audio-feature filter. Params: `q`, `tempo_min/max`, `energy_min/max`, `danceability_min/max`, `valence_min/max`, `acousticness_min/max`, `key` (0–11), `mode` (0/1), `limit`. |
| GET    | `/login`         | Start Spotify OAuth flow.                                           |
| GET    | `/callback`      | OAuth redirect target — caches token to `.cache-user`.              |
| POST   | `/logout`        | Delete cached user token.                                           |
| GET    | `/api/me`        | Current authenticated user (or `{authenticated: false}`).           |
| GET    | `/api/analyze`   | Top tracks/artists/genres/recents. `time_range`, `limit` params.    |

## Files

- `app.py` — Flask server (search + filter + analyze endpoints, OAuth)
- `spotify_client.py` — Spotipy clients (client-credentials and user OAuth)
- `search.py` — vibe search and re-rank logic
- `filter_search.py` — Spotify search + ReccoBeats audio-feature filter/rank
- `analyze.py` — pulls user listening data and aggregates genres/stats
- `main.py` — CLI for search
- `static/index.html` — single-page React UI (Search + Filter + My Music tabs)

## Notes

- `.env`, `.cache` (client-credentials token), and `.cache-user` (your OAuth token) are all gitignored — your secret never enters git history.
- If you fork this repo, copy `.env.example` to `.env` and fill in your own Spotify app credentials.
