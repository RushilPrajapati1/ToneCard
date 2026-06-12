# Deploying Tonecard

The app ships as a single Docker image (Flask + gunicorn + ffmpeg for upload
analysis). Any container host works; instructions for the three usual suspects
below. All of them need just two secrets: `SPOTIFY_CLIENT_ID` and
`SPOTIFY_CLIENT_SECRET`.

## Things to know before deploying

- **One instance is the right size.** The mood-pool cache, rate limiter, and
  disk caches are per-process. Scaling out multiplies your Spotify API usage
  (the per-app rate limit is global), so keep it to a single instance unless
  you add shared caching (Redis) first.
- **Disk caches are ephemeral in containers.** `.reccobeats_cache.json` and
  `.preview_cache.json` rebuild themselves after a restart — first clicks are
  slower, nothing breaks. Mount a persistent disk at `/app` if you want them
  to survive (optional).
- **`TRUST_PROXY=1`** must be set when running behind a load balancer (all
  three hosts below) so per-IP rate limiting sees real client IPs instead of
  the proxy's. The Dockerfile sets it by default; unset it if you ever run
  the container directly exposed.
- **Consider a second Spotify app** (separate client ID) for production so
  local development can't burn the production rate limit.
- Health check endpoint: `GET /healthz`.

## Local production-style run

```bash
docker build -t tonecard .
docker run --rm -p 5050:5050 --env-file .env tonecard
```

## Render (simplest)

`render.yaml` is checked in, so this is a blueprint deploy:

1. Push the repo to GitHub.
2. In the Render dashboard: **New → Blueprint**, pick the repo.
3. When prompted, fill in `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
4. Deploy. Render builds the Dockerfile and routes traffic to `$PORT`
   automatically.

## Fly.io

```bash
fly launch --no-deploy        # generates fly.toml from the Dockerfile; accept defaults, 1 machine
fly secrets set SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=...
fly deploy
```

In the generated `fly.toml`, set `internal_port = 5050` under `[http_service]`
(or set a `PORT` env var to match), and keep `min_machines_running = 0` only if
you're okay with cold starts — the librosa import plus pool build makes the
first request after a wake noticeably slow.

## Google Cloud Run

```bash
gcloud run deploy tonecard \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --max-instances 1 \
  --memory 1Gi \
  --set-env-vars TRUST_PROXY=1 \
  --set-secrets SPOTIFY_CLIENT_ID=spotify-client-id:latest,SPOTIFY_CLIENT_SECRET=spotify-client-secret:latest
```

(Create the two secrets in Secret Manager first, or use `--set-env-vars` for a
quick test — secrets are the right call for anything public.) Cloud Run
provides `PORT` automatically; gunicorn reads it. `--max-instances 1` keeps the
Spotify rate-limit math sane.

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `SPOTIFY_CLIENT_ID` | yes | — | Spotify app credentials |
| `SPOTIFY_CLIENT_SECRET` | yes | — | Spotify app credentials |
| `PORT` | no | `5050` | Listen port (gunicorn binds `0.0.0.0:$PORT`) |
| `TRUST_PROXY` | behind a proxy | unset | Trust `X-Forwarded-For` for rate limiting |
| `WEB_CONCURRENCY` | no | `1` | Gunicorn workers (keep at 1, see above) |
| `GUNICORN_THREADS` | no | `8` | Threads per worker |
