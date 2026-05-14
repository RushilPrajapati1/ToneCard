import numpy as np
import librosa


_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _mode_probability(y, sr):
    """Return probability [0,1] that the track is in a major key (Krumhansl profiles)."""
    chroma = np.mean(librosa.feature.chroma_cqt(y=y, sr=sr), axis=1)
    best_maj = best_min = -np.inf
    for s in range(12):
        rolled = np.roll(chroma, s)
        c_maj = np.corrcoef(rolled, _MAJOR)[0, 1]
        c_min = np.corrcoef(rolled, _MINOR)[0, 1]
        if not np.isnan(c_maj):
            best_maj = max(best_maj, c_maj)
        if not np.isnan(c_min):
            best_min = max(best_min, c_min)
    if best_maj == -np.inf and best_min == -np.inf:
        return 0.5
    total = best_maj + best_min
    return float(best_maj / total) if total > 0 else 0.5


def analyze_audio(filepath):
    """
    Analyze an audio file and return estimated valence, energy, and tempo.

    Only the first 90 s are loaded to keep latency reasonable. Valence is a
    heuristic combining key mode, tempo, and spectral brightness — it won't
    match Spotify/ReccoBeats exactly but gives a musically grounded position
    on the mood plane.
    """
    y, sr = librosa.load(filepath, sr=22050, mono=True, duration=90)

    # Energy: mean RMS, normalized so ~0.18 RMS ≈ 1.0
    rms_mean = float(np.mean(librosa.feature.rms(y=y)[0]))
    energy = float(np.clip(rms_mean / 0.18, 0.0, 1.0))

    # Tempo
    tempo_raw, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo_raw)[0])
    tempo_factor = float(np.clip((tempo - 60.0) / 120.0, 0.0, 1.0))

    # Mode probability (major = higher valence)
    mode_prob = _mode_probability(y, sr)

    # Spectral brightness (centroid, normalized 500-4500 Hz range)
    centroid_mean = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
    brightness = float(np.clip((centroid_mean - 500.0) / 4000.0, 0.0, 1.0))

    # Valence heuristic: mode dominates, tempo and brightness add nuance
    valence = 0.50 * mode_prob + 0.25 * tempo_factor + 0.25 * brightness

    return {
        "valence": round(float(np.clip(valence, 0.0, 1.0)), 3),
        "energy": round(energy, 3),
        "tempo": round(tempo, 1),
    }
