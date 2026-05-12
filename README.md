# Tonecard — mood discovery

A small Flask + React app for finding tracks by mood. No login, no account — it runs on Spotify's [Client Credentials](https://developer.spotify.com/documentation/web-api/concepts/authorization#client-credentials-flow) flow, so anyone can open it and start digging.

A single tab: an interactive 2D plane of valence (sad ↔ happy) × energy (calm ↔ intense). A curated seed set of tracks plots as dim dots; click anywhere on the plane (or tap a preset) to surface tracks closest to that mood, ranked by ReccoBeats audio features.

There's also a dark-mode toggle in the topbar (system-preference default, persisted to `localStorage`).

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

   Tonecard uses Spotify's **Client Credentials** flow — no redirect URI, no scopes, no per-user login.

## Run the web app

```bash
python app.py
```

Then open http://127.0.0.1:5050.

The dev server runs with `debug=False` — when you change Python files, restart the process to pick them up. The single-page React UI in `static/index.html` reloads on browser refresh (it's compiled in-browser via Babel standalone).

## API endpoints

| Method | Path                                     | Purpose |
| ------ | ---------------------------------------- | ------- |
| GET    | `/api/mood/seed`                         | The curated track set plotted on the mood plane as `(valence, energy)` points. |
| GET    | `/api/mood?valence=&energy=&count=`      | Tracks closest to a clicked `(valence, energy)` target. |

## Files

- `app.py` — Flask routes.
- `spotify_client.py` — Spotipy client-credentials client. Configured with `retries=0` so 429s fail fast instead of silently sleeping for an hour.
- `analyze.py` — mood-plane seed pool + mood search. Contains the paginated Spotify search helper used to build the pool.
- `reccobeats.py` — ReccoBeats glue: Spotify ID → ReccoBeats ID lookup, audio-feature fetch.
- `static/index.html` — single-page React UI (Babel standalone, no build step). Mood plane SVG, dark-mode toggle, all in one file.

## Notes

- `.env` and `.cache` (the client-credentials token) are gitignored.
- If you fork this repo, copy `.env.example` to `.env` and fill in your own Spotify credentials.
- Spotify's per-app rate limit is a 30-second rolling window shared across all callers of the same `CLIENT_ID`. The mood-seed pool is cached for an hour to keep clicks cheap; the first click after the cache expires re-runs six Spotify searches.
