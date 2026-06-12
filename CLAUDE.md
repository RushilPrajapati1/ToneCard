# Project context for Claude

Tonecard is a small Flask + single-file React app: a public mood-discovery UI on top of the Spotify Web API and ReccoBeats. The README is for end users; this file is for you. It captures the things you'd otherwise have to discover by reading the code or by repeating mistakes the user has already made.

## What this app does (quick map)

Two tabs in `static/index.html` — public, no login:

- **Atlas (Mood tab)** — interactive valence × energy SVG plane. The dim dots are a cached "seed pool" of tracks (ten broad-mood Spotify queries, deduped, ReccoBeats-enriched, 1-hour TTL). Clicking anywhere fetches tracks closest to that (valence, energy) point from the same pool. Genre filter chips (All / Pop / Hip-Hop / Rock / R&B / Electronic / Jazz / Classical / Latin / Punjabi / Metal / Country / Indie) narrow the pool. Preset buttons (Still + heavy / Still + bright / Wired + heavy / Wired + bright / Dead center) shortcut to common points. Keyboard accessible: arrow keys move the pin, Shift for larger steps, Enter/Space to search. An upload button lets the user drop an audio file — the app estimates valence, energy, and tempo via librosa and pins that point.

- **Lookup (Search tab)** — toggle between Track and Artist modes. In Track mode, type a song name and the UI finds the closest track in the mood pool and shows its neighbors. In Artist mode, type an artist name and the UI returns an artist card (avatar, genres, popularity, follower count) plus the artist's top tracks scattered on the mood plane.

Every track row has a ▶ button that plays a 30-second preview inline (single audio element, one at a time) — see the preview note under Conventions.

A dark/light toggle sits in the topbar (persisted to `localStorage["tonecard-theme"]`, no-flash via inline script before React loads). There's no CLI.

## Critical constraints (do not forget these)

1. **The app is public — Client Credentials only.** No OAuth, no user scopes, no `.cache-user`, no per-user data. If you're tempted to add a feature that requires the user's playlists, top tracks, library, or playback state, stop — that's a whole different app. Earlier iterations (My Music / Stats / per-playlist tools, then Search / Filter tabs) were deliberately removed; don't reintroduce them without an explicit ask.
2. **Spotify's `/audio-features` is unavailable** for this app's dev-mode credentials (progressively restricted, big cut in Feb 2026). All audio features come from **ReccoBeats**. Never recommend `sp.audio_features()` or `/v1/audio-features` — it will 403.
3. **These Spotify endpoints are all 403 for dev-mode Client Credentials apps** — do not use them:
   - `/v1/tracks?ids=` (batch tracks)
   - `/v1/artists?ids=` (batch artists)
   - `/v1/artists/{id}/top-tracks` (artist top tracks — use `sp.search(type='track', q='artist:"Name"')` instead)
   - `/v1/playlists/{id}/tracks` (playlist items)
   - `/v1/browse/featured-playlists`
   - `/v1/browse/new-releases`
   Also, `sp.search(type='artist')` returns a stripped object with no `popularity`, `genres`, or `followers` — only `id`, `name`, `images`, `external_urls`. For full artist data use `sp.artist(id)` (single lookup only).
4. **Spotipy is configured with `retries=0, status_retries=0, requests_timeout=10`** in `spotify_client.py`. This is intentional. Default spotipy will quietly sleep on a 429 for whatever the `Retry-After` header says (we saw 6101 s once), hanging the entire Flask request. With `retries=0`, 429s surface immediately and the UI shows the error inline. Don't change this without thinking it through.
5. **The Flask dev server runs with `debug=False`** (bottom of `app.py`). Python file changes require restarting the process — they do not auto-reload. HTML/CSS/JSX changes only need a browser refresh (Babel standalone compiles in-browser).
6. **DJ feature is not in the Web API.** If the user asks about Spotify DJ, the answer is "no public endpoint, never has been." Don't dig.

## Files and what they own

- `app.py` — Flask routes only, no business logic. Also owns the production hardening: per-IP sliding-window rate limiting (120/min on `/api/*`, 6/min on uploads; in-memory, per-process), security headers, a `_api_error()` helper that logs the real exception and returns a generic message (never echo `str(e)` to clients — it leaks internals; Spotify 429s get a friendly 429), `market` validated to two letters (falls back to `US`), and `genre` on the `/api/genre*` endpoints validated against `ALLOWED_GENRES` from `analyze.py` (mirrors the UI chips — arbitrary genre strings were a rate-limit/memory DoS vector). `ProxyFix` is applied when `TRUST_PROXY=1` so rate limiting sees real client IPs behind a load balancer. Routes:
  - `/` — serves `static/index.html`
  - `/api/mood/seed` — returns the full seed pool as `{id, name, artists, valence, energy}` points
  - `/api/mood` — query params `valence`, `energy`, `count` (1–25), `market` (default US). Returns nearest tracks by mood.
  - `/api/genre/seed` — query param `genre`. Returns genre-specific pool points.
  - `/api/genre` — query params `genre`, `valence`, `energy`, `count`, `market`. Nearest tracks within genre pool.
  - `/api/search` — query params `q`, `count`, `market`. Find a song by name → returns target track, similar neighbors, genre pool visualization.
  - `/api/artist` — query params `q`, `count` (1–20), `market`. Find artist → returns artist profile, top tracks with features, mood plane points.
  - `/api/artists/trending` — returns top 10 artists from a curated seed list (cached 1 hour).
  - `/api/upload/analyze` (POST) — upload audio file (mp3/wav/flac/ogg/m4a, max 30 MB). Returns estimated `{valence, energy, tempo}`.
  - `/healthz` — health check for deploy platforms (no rate limit, no Spotify calls).

- `spotify_client.py` — single client-credentials Spotipy client. Includes proxy-env hardening (some local network setups break Spotify auth via global `HTTP_PROXY`/`NO_PROXY`).

- `analyze.py` — all recommendation logic. Key functions:
  - `_search_tracks(query, total, market)` — paginated Spotify search helper
  - `_load_mood_pool(market)` / `_load_genre_pool(genre, market)` — lazy-load and cache pools with TTL check
  - `mood_seed(market)` — returns mood pool points (ten broad-mood queries × 20 results each, deduped, ReccoBeats-enriched, keyed by market, 1-hour TTL)
  - `genre_seed(genre, market)` — genre-specific pool (60 tracks, same TTL pattern)
  - `mood_search(valence, energy, count, market)` — ranks mood pool by Euclidean distance; returns top `count` tracks with full metadata
  - `genre_search(valence, energy, genre, count, market)` — same as mood_search but within genre pool
  - `search_by_name(q, count, market)` — finds a track, extracts its features, loads its genre pool, returns target + similar neighbors + pool points
  - `artist_search(query, count, market)` — finds artist, searches for their tracks via `sp.search(type='track', q='artist:"Name"')` (NOT `artist_top_tracks` — that's 403), enriches with ReccoBeats, returns artist profile + tracks + mood plane points
  - `trending_artists(limit)` — fetches 20 curated artist IDs via `sp.artist()` (single), caches 1 hour
  - `_fmt_track(t, f)` — shared track-formatting helper
  - The four track-returning functions (`mood_search`, `genre_search`, `search_by_name`, `artist_search`) call `fill_previews(...)` from `previews.py` on the returned list before responding, so each row gets a working `preview_url`.

- `reccobeats.py` — ReccoBeats glue: `_chunked` (40-ID batches), `_spotify_to_reccobeats_map`, `_fetch_features`, `get_features_for_spotify_ids` (the only public function). ReccoBeats feature keys: `valence`, `energy`, `tempo`, `danceability`, `key`, `mode`, `acousticness`. Features are disk-cached by Spotify ID in `.reccobeats_cache.json` (in-memory mirror loaded at import), so lookups survive server restarts and the hourly pool TTL.

- `previews.py` — preview-URL recovery. Spotify zeroed out `preview_url` in Web API responses, but the public embed page (`open.spotify.com/embed/track/{id}`) still serves the real `p.scdn.co/mp3-preview/...` clip. `fill_previews(tracks)` scrapes it for any track lacking a preview, fetched concurrently (8 workers) for the returned set only (≤25 tracks, never the whole pool), and disk-caches by Spotify ID in `.preview_cache.json` — including negative results (`""`) so dead tracks aren't re-scraped. This is a different host than the Web API, so it doesn't count against the shared API rate limit.

- `audio_analyze.py` — librosa-based local audio analysis. `analyze_audio(filepath)` loads the first 90 seconds of a file, computes:
  - **Energy**: RMS-based, normalized `rms_mean / 0.18` clipped [0, 1]
  - **Tempo**: librosa beat tracking (BPM)
  - **Valence**: heuristic — `0.50 × mode_prob + 0.25 × tempo_factor + 0.25 × brightness` (Krumhansl major/minor profiles, tempo factor, spectral centroid 500–4500 Hz)

- `static/index.html` — entire single-page React UI in one file. No build step, Babel standalone compiles in-browser. Components: `App`, `MoodTab`, `SearchTab`, `MoodPlane`, `ArtistView`, `TrackRow`, `SkeletonList`. Also contains all CSS and demo data (`DEMO_TRACKS`, `DEMO_FEAT`, `DEMO_SEED`, `DEMO_ARTIST`, `DEMO_SEARCH`, `DEMO_TRENDING`).

- `gunicorn.conf.py`, `Dockerfile`, `.dockerignore`, `render.yaml`, `DEPLOY.md` — production deployment. Gunicorn runs 1 worker × 8 threads (threads, not workers: the pool caches and rate limiter are per-process, and more processes multiply Spotify API usage against the global per-app limit). The Docker image installs ffmpeg so librosa can decode mp3/m4a uploads. Keep deployments to a single instance unless shared caching is added first. See `DEPLOY.md` for Render/Fly/Cloud Run specifics.

- `soundcharts.py` — unused. Can be deleted. Left over from a brief SoundCharts experiment that was reverted.

## Conventions / patterns

- **Pool builds are serialized behind locks** (`_pool_lock`, `_genre_lock` in `analyze.py`) so concurrent requests can't stampede the seed searches under a threaded server, and `_GENRE_CACHE` is bounded (`_GENRE_CACHE_MAX = 64`, oldest-evicted) because `search_by_name` keys it by arbitrary Spotify artist genres. The two disk caches take a snapshot under a lock and write through a unique temp file + atomic `os.replace`.
- **Mood pool is cached for an hour** (`_POOL_TTL_SECONDS = 3600` in `analyze.py`) keyed by `market`. The first request after expiry pays the full cost (ten Spotify searches + one ReccoBeats batch). Genre pools follow the same pattern (keyed by `genre+market`). If you change the seed queries or count, expect a one-time latency spike on the next click.
- **Mood uses Euclidean over `(valence, energy)` only.** Cosine would treat unrelated dimensions as if they shared a direction; absolute distance matters here (a happy-calm track is not "similar" to a happy-intense one even if the angle is close). Don't switch the metric.
- **Demo-mode fallback in fetches.** `safeFetch` in `static/index.html` sets `err.demo = true` on network failure (no `e.status`). Each fetcher catches this and substitutes hardcoded demo data so the UI is always navigable. Real API errors (with `e.status`) need explicit handling — easy to forget, and silent failures *will* happen if you don't.
- **Dark mode** uses `data-theme="dark"` on `<html>`. CSS variables flip in `:root[data-theme="dark"]`. New colors should be variables, not hardcoded oklch — otherwise they won't invert. CSS variables include `--bg`, `--surface`, `--ink`, `--accent`, `--line`, etc.
- **Spotify track IDs and ReccoBeats track IDs are different.** Use `_spotify_to_reccobeats_map` to convert. ReccoBeats metadata returns Spotify URLs in `meta["href"]`; the map function parses them.
- **`preview_url` is always `null` from the Web API now** — never trust it directly. `previews.py`'s `fill_previews()` backfills it from the embed page. The frontend `TrackRow` gates its ▶ button on `t.preview_url`, so if you add a new endpoint that returns tracks and forget to call `fill_previews`, the play button silently won't render. The `<audio>` element points straight at `p.scdn.co` (a media element, so no CORS issue).
- **Fonts**: "Space Grotesk" (body), "IBM Plex Mono" (UI detail/labels).
- **Accessibility**: ARIA labels and live regions are in place; `prefers-reduced-motion` disables transitions; keyboard nav on the mood plane uses arrow keys (+ Shift for larger steps), Enter/Space to fire a search. Don't strip these when editing the HTML.

## Operational notes

- **Restart Flask after Python edits** (Windows, PowerShell):
  ```powershell
  Stop-Process -Id (Get-NetTCPConnection -LocalPort 5050 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue; cd "c:\Users\rushi\vscode projects\Spotifiy_Vibe"; .\venv\Scripts\Activate.ps1; python app.py
  ```
  The user has asked for this several times — it's fine to just do it without confirming.
- **Restart Flask after Python edits** (macOS — there's also a checkout at `/Users/rushi/Spotify Search APP`):
  ```bash
  lsof -ti :5050 | xargs kill -9 2>/dev/null; ./venv/bin/python app.py
  ```
  Note the macOS `./venv` can lag `requirements.txt` — if `app.py` won't boot with `ModuleNotFoundError: numpy`, the venv is missing `librosa` (which pulls numpy); `./venv/bin/pip install "librosa>=0.10.0"` fixes it.
- **`.env`, `.cache`** are gitignored, as are the on-disk caches `.reccobeats_cache.json` and `.preview_cache.json`. Don't commit them. Required keys: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`. See `.env.example`.
- **Per-app rate limit is global.** If the user hits it, even a different chat session can't dodge it — same `CLIENT_ID`. The only escape is wait (~100 min) or rotate to a second Spotify app. The mood-pool cache is the main defense — without it, every Mood click would re-run ten searches.
- **librosa is a heavyweight dependency.** `audio_analyze.py` imports it at module level, adding ~1–2 s cold-start on first import. That's expected.

## Things the user has explicitly chosen / rejected

- **Mood-only, public, no-login app.** OAuth + My Music + Stats + per-playlist tools were removed first; Search and Filter tabs were removed after that. The app now has Atlas (mood) + Lookup (search/artist) tabs — don't propose re-adding the old removed tabs without a direct ask.
- **Mood plane uses Euclidean, not cosine** — discussed and decided.
- **Mood seed pool is search-derived, not editorially curated.** Ten broad-mood queries (`happy upbeat`, `sad emotional`, `chill mellow`, `energetic dance`, `melancholy slow`, `uplifting anthem`, `dark ambient`, `aggressive intense`, `romantic slow`, `party hype`) give plane coverage without hand-picking tracks. If coverage feels uneven, expand the query list before reaching for a static seed list.
- **SoundCharts was tried and reverted** — user chose to stay on ReccoBeats.

## Open ideas the user is weighing (don't presume)

- Expanding the mood seed pool (more queries, larger per-query pull) to make the plane denser.
- Persisting the Spotify *candidate* lists (not just ReccoBeats features) to disk, so the pool survives restarts without re-running the seed searches.
- Parallelizing the cold-start pool build (the ten seed searches currently run sequentially).
- Surfacing cold-start latency in the UI (the first Mood click can take many seconds with only a skeleton showing).

Already shipped (were open ideas): 30-second preview playback per row (`previews.py` + `TrackRow` ▶ button), disk-caching ReccoBeats features (`.reccobeats_cache.json`), and production deploy scaffolding (Dockerfile + gunicorn + `render.yaml` + `DEPLOY.md` — not yet actually deployed anywhere).

## Gotchas worth flagging if you trip on them

- The user once accidentally edited the README "Run the web app" line to `pip install -r requirements.txt` mid-edit. Watch for stray edits in unrelated files before committing — diff before staging.
- Babel-standalone compiles `static/index.html` in-browser, so a JSX syntax error doesn't fail at build time — it just blanks the page. If the UI goes empty after an HTML edit, open the devtools console first.
- The Mood pool depends on Spotify search returning anything for the seed queries in the given `market`. An obscure market with no hits will produce an empty pool and the plane will render zero dots. Default market is `US`.
- `reccobeats.py` is the renamed `filter_search.py` — older git history will show the old name. The module has no `filter_search` function anymore; it's purely ReccoBeats glue.
- The mood presets are labeled **Still / Wired** (energy axis) and **Heavy / Bright** (valence axis) in the UI. Don't revert to old names like "Calm" or "Intense".
- `audio_analyze.py` uses only the first 90 seconds of the uploaded file for speed. Valence estimation is a heuristic (major/minor key + tempo + brightness) — it will be imprecise on complex or atonal material. Don't over-engineer it; it's a directional signal, not a ground truth.
- `artist_search()` uses `sp.search(type='track', q='artist:"Name"')` for the track list because `sp.artist_top_tracks()` is 403 for dev-mode apps. The search result is filtered to only include tracks where the artist name matches exactly.
