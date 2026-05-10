"""
Feature vectorization for track similarity scoring.

Each ReccoBeats audio-feature dict gets mapped into a fixed-order vector in
[0, 1]^8 using the spans declared in vibe_profile.FEATURE_SPECS. Once tracks
are vectors, similarity is just standard linear-algebra: take the centroid of
a playlist, compute distance from each candidate to that centroid, sort.

Two metrics are exposed:

  euclidean_distance(v1, v2, weights=...)
      Absolute-value matching. A 90 BPM track is *not* similar to a 180 BPM
      track even if other features are proportional. This is the right metric
      for "find tracks that fit the BPM/energy/feel of this playlist."

  cosine_similarity(v1, v2)
      Shape matching. A track that is "high energy + high dance + low acoustic"
      matches another with the same proportions even at different magnitudes.
      Useful when you care about the *ratio* of features rather than absolute
      values. Mostly here for comparison.

Missing features are filled with 0.5 (the neutral midpoint). This keeps a
single missing dimension from dominating the distance — both the candidate
and the centroid will fall back to the same value for any feature ReccoBeats
didn't return, so that dim contributes ~0 to the score.
"""
import math

from vibe_profile import FEATURE_SPECS

# Vectors are always laid out in this order. Don't reorder — callers index
# by position in some places (e.g. centroid arithmetic).
FEATURE_DIMS = (
    "tempo",
    "energy",
    "danceability",
    "valence",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "liveness",
)

# Per-dimension weights for the default vibe-search distance. Tempo / energy
# / danceability move the needle most for "does this track fit the playlist";
# the niche features (instrumentalness, speechiness, liveness) get small
# weights so they only break ties.
DEFAULT_WEIGHTS = {
    "tempo": 1.5,
    "energy": 1.3,
    "danceability": 1.3,
    "valence": 1.0,
    "acousticness": 0.8,
    "instrumentalness": 0.6,
    "speechiness": 0.4,
    "liveness": 0.4,
}


def _normalize(value, lo, hi):
    if value is None:
        return None
    span = hi - lo
    if span <= 0:
        return None
    return max(0.0, min(1.0, (float(value) - lo) / span))


def track_to_vector(features, fill_missing=0.5):
    """Map a ReccoBeats features dict to an 8-D vector in [0, 1]^8."""
    if not features:
        return [fill_missing] * len(FEATURE_DIMS)
    vec = []
    for key in FEATURE_DIMS:
        lo, hi = FEATURE_SPECS[key]
        n = _normalize(features.get(key), lo, hi)
        vec.append(fill_missing if n is None else n)
    return vec


def centroid(vectors):
    """Element-wise mean across a non-empty list of equal-length vectors."""
    vectors = list(vectors)
    if not vectors:
        return None
    dims = len(vectors[0])
    out = [0.0] * dims
    for v in vectors:
        for i in range(dims):
            out[i] += v[i]
    n = len(vectors)
    return [x / n for x in out]


def _weight_vec(weights):
    if not weights:
        return [1.0] * len(FEATURE_DIMS)
    return [float(weights.get(k, 1.0)) for k in FEATURE_DIMS]


def euclidean_distance(v1, v2, weights=None):
    """Weighted Euclidean distance. Lower = more similar. 0 = identical."""
    w = _weight_vec(weights)
    s = 0.0
    for a, b, weight in zip(v1, v2, w):
        d = a - b
        s += weight * d * d
    return math.sqrt(s)


def cosine_similarity(v1, v2):
    """Cosine similarity in [-1, 1]. Higher = more similar."""
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def cosine_distance(v1, v2):
    """1 - cosine_similarity. Lower = more similar."""
    return 1.0 - cosine_similarity(v1, v2)


def closeness_score(v1, v2, weights=None):
    """Map weighted Euclidean distance to a [0, 1] similarity score.

    Highest possible weighted distance between two vectors in [0, 1]^n is
    sqrt(sum(weights)), so we normalize by that and flip so 1.0 = identical,
    0.0 = maximally far.
    """
    w = _weight_vec(weights)
    max_d = math.sqrt(sum(w))
    if max_d <= 0:
        return 0.0
    d = euclidean_distance(v1, v2, weights=weights)
    return max(0.0, 1.0 - d / max_d)
