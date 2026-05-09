import re


FEATURE_SPECS = {
    "tempo": (40.0, 220.0),
    "energy": (0.0, 1.0),
    "danceability": (0.0, 1.0),
    "valence": (0.0, 1.0),
    "acousticness": (0.0, 1.0),
    "instrumentalness": (0.0, 1.0),
    "speechiness": (0.0, 1.0),
    "liveness": (0.0, 1.0),
}

DEFAULT_TARGETS = {
    "tempo": 115.0,
    "energy": 0.55,
    "danceability": 0.55,
    "valence": 0.5,
    "acousticness": 0.35,
    "instrumentalness": 0.2,
    "speechiness": 0.1,
    "liveness": 0.15,
}

VIBE_PRESETS = {
    "chill": {"energy": 0.28, "danceability": 0.45, "acousticness": 0.65, "valence": 0.42, "tempo": 88.0},
    "calm": {"energy": 0.22, "danceability": 0.35, "acousticness": 0.7, "tempo": 80.0},
    "focus": {"instrumentalness": 0.72, "speechiness": 0.05, "energy": 0.35, "valence": 0.45},
    "study": {"instrumentalness": 0.75, "speechiness": 0.04, "energy": 0.32, "tempo": 95.0},
    "sleep": {"energy": 0.12, "valence": 0.35, "acousticness": 0.8, "tempo": 70.0},
    "sad": {"valence": 0.2, "energy": 0.3, "acousticness": 0.6, "tempo": 85.0},
    "happy": {"valence": 0.82, "energy": 0.72, "danceability": 0.7, "tempo": 122.0},
    "party": {"energy": 0.88, "danceability": 0.85, "valence": 0.76, "tempo": 128.0},
    "hype": {"energy": 0.9, "danceability": 0.78, "valence": 0.68, "tempo": 136.0},
    "workout": {"energy": 0.9, "danceability": 0.76, "tempo": 140.0},
    "gym": {"energy": 0.9, "danceability": 0.75, "tempo": 138.0},
    "cozy": {"acousticness": 0.7, "energy": 0.3, "valence": 0.52, "tempo": 92.0},
    "romantic": {"valence": 0.62, "energy": 0.38, "acousticness": 0.55, "tempo": 96.0},
    "ambient": {"instrumentalness": 0.85, "energy": 0.18, "speechiness": 0.03, "tempo": 78.0},
    "lofi": {"instrumentalness": 0.8, "energy": 0.3, "acousticness": 0.55, "tempo": 88.0},
}

TOKEN_PATTERN = re.compile(r"[a-z0-9#]+")


def normalize_vibe_keywords(vibe_keywords):
    if not vibe_keywords:
        return []
    if isinstance(vibe_keywords, str):
        raw = vibe_keywords
    else:
        raw = " ".join(vibe_keywords)
    return TOKEN_PATTERN.findall(raw.lower())


def build_vibe_profile(vibe_keywords):
    tokens = normalize_vibe_keywords(vibe_keywords)
    if not tokens:
        return None

    sums = {k: DEFAULT_TARGETS[k] for k in DEFAULT_TARGETS}
    counts = {k: 1.0 for k in DEFAULT_TARGETS}

    for token in tokens:
        preset = VIBE_PRESETS.get(token)
        if not preset:
            continue
        for key, value in preset.items():
            if key in sums:
                sums[key] += value
                counts[key] += 1.0

    targets = {k: sums[k] / counts[k] for k in sums}
    return {"tokens": tokens, "targets": targets}


def text_match_score(text_haystack, tokens):
    if not tokens:
        return 0.0
    haystack = (text_haystack or "").lower()
    if not haystack:
        return 0.0
    hits = sum(1 for token in tokens if token in haystack)
    return hits / max(len(tokens), 1)


def feature_closeness_score(features, targets):
    if not targets or not features:
        return 0.0

    total = 0.0
    used = 0
    for key, target in targets.items():
        value = features.get(key)
        if value is None:
            continue
        lo, hi = FEATURE_SPECS[key]
        span = hi - lo
        if span <= 0:
            continue
        closeness = 1.0 - min(abs(float(value) - float(target)) / span, 1.0)
        total += closeness
        used += 1
    return total / used if used else 0.0

