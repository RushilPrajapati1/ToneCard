# Tonecard — Spotify vibe search & listening stats

A small Flask + React app for digging into your Spotify listening. Three tabs:

1. **My Music** — your playlists with one-click analysis (avg BPM / energy / dance), "Find similar" recommendations seeded from each playlist, and **By vibe** search anchored to a playlist's audio profile (e.g. type `spanish trap` against your UK playlist and get tracks that fit both the word *and* the playlist's BPM/energy/dance).
2. **Mood** — an interactive 2D plane of valence (sad ↔ happy) × energy (calm ↔ intense). Dim dots are your top tracks, plotted from real audio features. Click anywhere on the plane to surface tracks closest to that mood.
3. **Stats** — top tracks, top artists, top genres, recent plays, and aggregate listening-shape stats. Time range switches between 4w / 6m / all-time.

There's also a dark-mode toggle in the topbar (system-preference default, persisted to `localStorage`) and a CLI for basic search.

> Audio features come from [ReccoBeats](https://reccobeats.com). Spotify has progressively restricted `/audio-features` for new apps; ReccoBeats fills the gap with the same shape of data (tempo, energy, danceability, valence, acousticness, instrumentalness, speechiness, liveness — everything except loudness).

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

3. **Configure Spotify credentials.** Copy `.env.example` to `.env` and paste in `CLIENT_ID` / `CLIENT_SECRET` from your developer dashboard:

   ```bash
   cp .env.example .env
   # edit .env and paste your real values
   ```

   `.env` is gitignored and loaded automatically via `python-dotenv`. Alternatively, export them directly:

   ```bash
   export SPOTIFY_CLIENT_ID=...
   export SPOTIFY_CLIENT_SECRET=...
   ```

4. **Register the OAuth redirect URI.** My Music / Mood / Stats all log into your personal Spotify account, so:

   - Open your app in the Spotify Developer Dashboard → **Edit Settings** → **Redirect URIs**
   - Add: `http://127.0.0.1:5050/callback`
   - **Save**

   Without this you'll see `INVALID_CLIENT: Invalid redirect URI`. Scopes used: `user-top-read`, `user-read-recently-played`, `user-library-read`, `user-read-private`, `playlist-read-private`, `playlist-read-collaborative`.

## Run the web app

```bash
python app.py
```

Then open http://127.0.0.1:5050. Click **Connect Spotify** on any tab to authorize.

The dev server runs with `debug=False` — when you change Python files, restart the process to pick them up. The single-page React UI in `static/index.html` reloads on browser refresh (it's compiled in-browser via Babel standalone).

Click **Disconnect** to clear the cached OAuth token (`.cache-user`).

## Run the CLI (search only)

```bash
python main.py "rainy day jazz"
```

Re-rank by vibe keywords:

```bash
python main.py "rainy day jazz" --vibe chill lofi mellow
```

Options: `python main.py "<query>" [--vibe kw1 kw2 ...] [--limit N] [--market US]`.

## API endpoints

| Method | Path                                          | Purpose |
| ------ | --------------------------------------------- | ------- |
| GET    | `/api/me`                                     | Current authenticated user (or `{authenticated: false}`). |
| GET    | `/login` / `/callback`                        | Start OAuth / receive redirect (caches token to `.cache-user`). |
| POST   | `/logout`                                     | Delete the cached user token. |
| GET    | `/api/search?q=&vibe=&limit=&market=`         | Vibe-aware Spotify search, re-ranked by text + audio profile. |
| GET    | `/api/filter?q=&tempo_min=&...`               | Spotify search → ReccoBeats features → range filter. Params: `tempo_min/max`, `energy_min/max`, `danceability_min/max`, `valence_min/max`, `acousticness_min/max`, `key` (0–11), `mode` (0/1), `vibe`, `limit`. |
| GET    | `/api/analyze?time_range=&limit=`             | Top tracks/artists/genres/recents + listening-shape stats. |
| GET    | `/api/playlists`                              | All playlists the user owns or follows. |
| GET    | `/api/playlists/<id>/stats`                   | Avg tempo / energy / danceability over the first 100 tracks. |
| GET    | `/api/playlists/<id>/recommendations?count=`  | Tracks similar to the playlist (ReccoBeats seeded). |
| GET    | `/api/playlists/<id>/vibe?vibe=&count=`       | Vibe-text search ranked by closeness to the playlist's audio profile. |
| GET    | `/api/mood/history`                           | Your top tracks plotted as `(valence, energy)` points. |
| GET    | `/api/mood?valence=&energy=&count=`           | Tracks closest to a clicked `(valence, energy)` target. |

## Files

- `app.py` — Flask routes (OAuth + all endpoints above).
- `spotify_client.py` — Spotipy clients (client-credentials + user OAuth). Configured with `retries=0` so 429s fail fast instead of silently sleeping for an hour.
- `search.py` — `improved_search`: Spotify search → vibe-keyword + audio-feature re-rank.
- `filter_search.py` — ReccoBeats audio-feature fetch, recommendations API, range filter.
- `analyze.py` — user listening, playlist stats, playlist recommendations, vibe search anchored to a playlist, mood history, mood search.
- `vibe_profile.py` — vibe presets (chill / hype / focus / etc.), feature specs, text-match + closeness scoring helpers.
- `feature_vectors.py` — track-to-vector normalization, centroid, weighted Euclidean distance and cosine similarity. Used by playlist-anchored ranking in `analyze.py`.
- `main.py` — CLI wrapper around `improved_search`.
- `static/index.html` — single-page React UI (Babel standalone, no build step). Tabs, dark-mode toggle, mood plane SVG, all in one file.

## Notes

- `.env`, `.cache` (client-credentials token), and `.cache-user` (your OAuth token) are gitignored.
- If you fork this repo, copy `.env.example` to `.env` and fill in your own Spotify credentials.
- Spotify's per-app rate limit is a 30-second rolling window. Heavy use of "Find similar" (which still does per-track Spotify lookups for album art) can hit 429 — the app surfaces those inline now rather than hanging.
