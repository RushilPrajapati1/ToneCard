# Project context for Claude

Tonecard is a small Flask + single-file React app: a public mood-discovery UI on top of the Spotify Web API and ReccoBeats. The README is for end users; this file is for you. It captures the things you'd otherwise have to discover by reading the code or by repeating mistakes the user has already made.

## What this app does (quick map)

One UI surface in `static/index.html` — public, no login:

- **Mood** — interactive valence × energy SVG plane. The dim dots are a cached "seed pool" of tracks (six broad-mood Spotify queries, deduped, ReccoBeats-enriched, 1-hour TTL). Clicking anywhere fetches tracks closest to that (valence, energy) point from the same pool. Preset buttons (Calm + sad / Calm + happy / Intense + sad / Intense + happy / Center) shortcut to common points.

A dark/light toggle sits in the topbar (persisted to `localStorage["tonecard-theme"]`, no-flash via inline script before React loads). There's no CLI anymore.

## Critical constraints (do not forget these)

1. **The app is public — Client Credentials only.** No OAuth, no user scopes, no `.cache-user`, no per-user data. If you're tempted to add a feature that requires the user's playlists, top tracks, library, or playback state, stop — that's a whole different app. Earlier iterations (My Music / Stats / per-playlist tools, then Search / Filter tabs) were deliberately removed; don't reintroduce them without an explicit ask.
2. **Spotify's `/audio-features` is unavailable** for this app's dev-mode credentials (progressively restricted, big cut in Feb 2026). All audio features come from **ReccoBeats**. Never recommend `sp.audio_features()` or `/v1/audio-features` — it will 403.
3. **Spotify's `/v1/tracks?ids=` batch endpoint is also 403 for dev-mode apps.** Current codepaths don't rely on it. If you ever need richer per-track metadata, prefer fields off the search result itself, or fan out single `sp.track(tid)` calls *very* sparingly — 8-worker parallel fan-out has rate-limited the whole app for ~100 minutes in the past.
4. **Spotipy is configured with `retries=0, status_retries=0, requests_timeout=10`** in `spotify_client.py`. This is intentional. Default spotipy will quietly sleep on a 429 for whatever the `Retry-After` header says (we saw 6101 s once), hanging the entire Flask request. With `retries=0`, 429s surface immediately and the UI shows the error inline. Don't change this without thinking it through.
5. **The Flask dev server runs with `debug=False`** (bottom of `app.py`). Python file changes require restarting the process — they do not auto-reload. HTML/CSS/JSX changes only need a browser refresh (Babel standalone compiles in-browser).
6. **DJ feature is not in the Web API.** If the user asks about Spotify DJ, the answer is "no public endpoint, never has been." Don't dig.

## Files and what they own

- `app.py` — Flask routes only: `/`, `/api/mood/seed`, `/api/mood`. No business logic.
- `spotify_client.py` — single client-credentials Spotipy client. Includes proxy-env hardening (some local network setups break Spotify auth via global `HTTP_PROXY`/`NO_PROXY`).
- `analyze.py` — mood-plane logic. `_search_tracks` is the paginated Spotify search helper. `_load_mood_pool` caches the seed pool (six broad-mood Spotify queries × 20 results each, deduped, ReccoBeats features fetched once, keyed by `market`, 1-hour TTL). `mood_seed` returns the pool as `(valence, energy)` points; `mood_search` ranks the same pool by Euclidean distance to a target point.
- `reccobeats.py` — ReccoBeats glue: `_chunked`, `_spotify_to_reccobeats_map`, `_fetch_features`, `get_features_for_spotify_ids` (the only public function — what `analyze.py` imports).
- `static/index.html` — entire single-page React UI in one file. No build step, Babel standalone compiles in-browser. App + MoodTab + MoodPlane + TrackRow + SkeletonList + CSS + demo data, all here.

## Conventions / patterns

- **Mood pool is cached for an hour** (`_POOL_TTL_SECONDS = 3600` in `analyze.py`) keyed by `market`. The first request after expiry pays the full cost (six Spotify searches + one ReccoBeats batch). If you change the seed queries or count, expect a one-time latency spike on the next click.
- **Mood uses Euclidean over `(valence, energy)` only.** Cosine would treat unrelated dimensions as if they shared a direction; absolute distance matters here (a happy-calm track is not "similar" to a happy-intense one even if the angle is close). Don't switch the metric.
- **Demo-mode fallback in fetches.** `safeFetch` in `static/index.html` sets `err.demo = true` on network failure (no `e.status`). Each fetcher catches this and substitutes hardcoded demo data so the UI is always navigable. Real API errors (with `e.status`) need explicit handling — easy to forget, and silent failures *will* happen if you don't.
- **Dark mode** uses `data-theme="dark"` on `<html>`. CSS variables flip in `:root[data-theme="dark"]`. New colors should be variables, not hardcoded oklch — otherwise they won't invert.
- **Spotify track IDs and ReccoBeats track IDs are different.** Use `_spotify_to_reccobeats_map` to convert. ReccoBeats metadata returns Spotify URLs in `meta["href"]`; the map function parses them.

## Operational notes

- **Restart Flask after Python edits**: `lsof -ti:5050 | xargs kill; (cd "/Users/rushi/Spotify Search APP" && source venv/bin/activate && python app.py)`. The user has asked me to do this several times — it's fine to just do it without confirming.
- **`.env`, `.cache`** are gitignored. Don't commit them. (There is no `.cache-user` anymore.)
- **Per-app rate limit is global.** If the user hits it, even a different chat session can't dodge it — same `CLIENT_ID`. The only escape is wait (~100 min) or rotate to a second Spotify app. The mood-pool cache is the main defense — without it, every Mood click would re-run six searches.

## Things the user has explicitly chosen / rejected

- **Mood-only, public, no-login app.** OAuth + My Music + Stats + per-playlist tools were removed first; Search and Filter tabs were removed after that. Don't propose re-adding any of them without a direct ask.
- **Mood plane uses Euclidean, not cosine** — discussed and decided.
- **Mood seed pool is search-derived, not editorially curated.** Six broad-mood queries (`happy upbeat`, `sad emotional`, `chill mellow`, `energetic dance`, `melancholy slow`, `uplifting anthem`) give plane coverage without hand-picking tracks. If coverage feels uneven, expand the query list before reaching for a static seed list.

## Open ideas the user is weighing (don't presume)

- 30-second `preview_url` audio playback per row.
- Caching ReccoBeats features to disk so the pool survives across server restarts and beyond the hourly TTL.
- Expanding the mood seed pool (more queries, larger per-query pull) to make the plane denser.
- Production deploy (Render / Fly / Cloud Run) — easier now that there's no per-user state.

## Gotchas worth flagging if you trip on them

- The user once accidentally edited the README "Run the web app" line to `pip install -r requirements.txt` mid-edit. Watch for stray edits in unrelated files before committing — diff before staging.
- Babel-standalone compiles `static/index.html` in-browser, so a JSX syntax error doesn't fail at build time — it just blanks the page. If the UI goes empty after an HTML edit, open the devtools console first.
- The Mood pool depends on Spotify search returning anything for the seed queries in the given `market`. An obscure market with no hits will produce an empty pool and the plane will render zero dots. Default market is `US`.
- `reccobeats.py` is the renamed `filter_search.py` — older git history will show the old name. The module has no `filter_search` function anymore; it's purely ReccoBeats glue.
