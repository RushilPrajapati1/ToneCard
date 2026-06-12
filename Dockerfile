# Tonecard — Flask + librosa. ffmpeg is needed so librosa/audioread can decode
# mp3 and m4a uploads (wav/flac/ogg are handled by the bundled libsndfile).
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py analyze.py audio_analyze.py previews.py reccobeats.py spotify_client.py gunicorn.conf.py ./
COPY static/ static/

# Non-root user; it still needs to own /app so the disk caches
# (.reccobeats_cache.json, .preview_cache.json) can be written.
RUN useradd --create-home tonecard && chown -R tonecard /app
USER tonecard

ENV TRUST_PROXY=1
EXPOSE 5050

CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
