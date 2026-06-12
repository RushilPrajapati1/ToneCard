"""Gunicorn config for Tonecard.

Threads (not extra workers) because the app is I/O-bound on Spotify/ReccoBeats
calls, and the in-memory pool caches and rate limiter are per-process — fewer
processes means warmer caches and a tighter effective rate limit.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5050')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "8"))
# Cold-start pool builds and librosa uploads can legitimately take a while.
timeout = 120
accesslog = "-"
errorlog = "-"
