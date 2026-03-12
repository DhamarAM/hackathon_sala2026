"""
backend/stage5_soundscape.py — Stage 5: Soundscape characterization.

Computes ocean-adapted acoustic indices for each WAV clip.
No GPU required. Uses scikit-maad for entropies and computes power bands
customized for marine context (not terrestrial defaults).

Metrics per clip:
  ndsi_underwater   — BIO / (ANTHRO + BIO) ratio; > 0.5 = biology-dominated
  band_power_low    — relative energy at 50–2000 Hz  (boats, fish)
  band_power_mid    — relative energy at 2–10 kHz    (shrimp, low dolphins)
  band_power_high   — relative energy at 10–48 kHz   (echolocation, dolphins)
  temporal_entropy  — temporal diversity of the signal (maad.features.temporal_entropy)
  spectral_entropy  — spectral diversity               (maad.features.spectral_entropy)
  dominant_band     — LOW | MID | HIGH (which has the most energy)
  boat_score        — boat noise proxy (normalized band_power_low, 50–500 Hz)

Usage:
    from backend.pipeline.stage3_soundscape import run_soundscape
    soundscape = run_soundscape(clip_paths, output_dir=Path("outputs/soundscape"))
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np

from backend.config import (
    SOUNDSCAPE_ANTHRO_HZ, SOUNDSCAPE_BIO_LOW_HZ, SOUNDSCAPE_BIO_BAND_HZ,
    SOUNDSCAPE_MID_HZ, SOUNDSCAPE_HIGH_HZ,
    SOUNDSCAPE_WELCH_NPERSEG, SOUNDSCAPE_BOAT_SCALE,
)

logger = logging.getLogger(__name__)


def _load_wav(path: Path):
    """Loads WAV with librosa; returns (y, sr)."""
    import librosa
    y, sr = librosa.load(str(path), sr=None, mono=True)
    return y, sr


def _band_power(psd: np.ndarray, freqs: np.ndarray, low: float, high: float) -> float:
    """Integrated power in a frequency band."""
    mask = (freqs >= low) & (freqs <= high)
    if not mask.any():
        return 0.0
    return float(np.sum(psd[mask]))


def _compute_metrics(y: np.ndarray, sr: int) -> dict:
    """Computes acoustic metrics for an audio array."""
    from scipy.signal import welch

    nperseg = min(len(y), SOUNDSCAPE_WELCH_NPERSEG)
    freqs, psd = welch(y, fs=sr, nperseg=nperseg)

    total_power = np.sum(psd) + 1e-12

    # Relative band power
    p_anthro = _band_power(psd, freqs, *SOUNDSCAPE_ANTHRO_HZ)   / total_power
    p_bio    = _band_power(psd, freqs, *SOUNDSCAPE_BIO_BAND_HZ) / total_power
    p_low    = _band_power(psd, freqs, *SOUNDSCAPE_BIO_LOW_HZ)  / total_power
    p_mid    = _band_power(psd, freqs, *SOUNDSCAPE_MID_HZ)      / total_power
    p_high   = _band_power(psd, freqs, *SOUNDSCAPE_HIGH_HZ)     / total_power

    # Underwater NDSI: biology vs (noise + biology) ratio
    denom = p_anthro + p_bio
    ndsi = float((p_bio - p_anthro) / denom) if denom > 1e-12 else 0.0
    ndsi = float(np.clip(ndsi, -1.0, 1.0))

    # Entropies with scikit-maad (if available), otherwise scipy fallback
    temporal_entropy = _temporal_entropy(y)
    spectral_entropy = _spectral_entropy(psd)

    # Dominant band
    bands = {'LOW': p_low, 'MID': p_mid, 'HIGH': p_high}
    dominant_band = max(bands, key=bands.get)

    # boat_score: low power normalized to [0,1]
    boat_score = float(np.clip(p_low * SOUNDSCAPE_BOAT_SCALE, 0.0, 1.0))

    return {
        'ndsi_underwater':  float(round(ndsi, 4)),
        'band_power_low':   float(round(float(p_low), 4)),
        'band_power_mid':   float(round(float(p_mid), 4)),
        'band_power_high':  float(round(float(p_high), 4)),
        'temporal_entropy': float(round(temporal_entropy, 4)),
        'spectral_entropy': float(round(spectral_entropy, 4)),
        'dominant_band':    dominant_band,
        'boat_score':       float(round(boat_score, 4)),
    }


def _temporal_entropy(y: np.ndarray) -> float:
    """Wiener entropy over the temporal envelope (maad or scipy fallback)."""
    try:
        import maad.features as mf
        import maad.sound as ms
        # maad expects (y, sr) but temporal_entropy only needs y
        return float(mf.temporal_entropy(y))
    except Exception:
        pass
    # Fallback: entropy of the amplitude distribution
    env = np.abs(y) + 1e-12
    env = env / env.sum()
    return float(-np.sum(env * np.log(env + 1e-12)) / np.log(len(env)))


def _spectral_entropy(psd: np.ndarray) -> float:
    """Wiener spectral entropy (maad or scipy fallback)."""
    try:
        import maad.features as mf
        return float(mf.spectral_entropy(psd))
    except Exception:
        pass
    p = psd + 1e-12
    p = p / p.sum()
    return float(-np.sum(p * np.log(p)) / np.log(len(p)))


def _plot_ndsi_timeseries(soundscape: Dict[str, dict], output_dir: Path) -> None:
    """Generates a PNG with the NDSI time series per clip."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    names = list(soundscape.keys())
    ndsi_vals = [soundscape[n]['ndsi_underwater'] for n in names]
    boat_vals = [soundscape[n]['boat_score'] for n in names]

    fig, ax = plt.subplots(figsize=(max(8, len(names) * 0.5), 4))
    x = range(len(names))
    ax.bar(x, ndsi_vals, color='teal', alpha=0.7, label='NDSI underwater')
    ax.bar(x, [-b for b in boat_vals], color='coral', alpha=0.6, label='boat_score (neg)')
    ax.axhline(0, color='black', linewidth=0.8)
    ax.axhline(0.5, color='teal', linewidth=0.5, linestyle='--', alpha=0.5)
    ax.axhline(-0.5, color='coral', linewidth=0.5, linestyle='--', alpha=0.5)
    ax.set_xticks(list(x))
    ax.set_xticklabels([Path(n).stem[:20] for n in names], rotation=45, ha='right', fontsize=6)
    ax.set_ylabel('Score')
    ax.set_title('Soundscape Index — NDSI underwater per clip')
    ax.legend(fontsize=8)
    plt.tight_layout()
    out = output_dir / 'ndsi_timeseries.png'
    fig.savefig(out, dpi=120)
    plt.close(fig)
    logger.info("  → %s", out)


def run_soundscape(
    wav_paths: List[Path],
    output_dir: Path,
) -> Dict[str, dict]:
    """
    Computes soundscape indices for each WAV clip.

    Args:
        wav_paths:  List of WAV paths (clips from Stage 0).
        output_dir: Folder where soundscape.json and the visualization are saved.

    Returns:
        Dict {filename: metrics_dict}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    soundscape: Dict[str, dict] = {}

    logger.info("Stage 5 — Soundscape characterization (%d clips)", len(wav_paths))

    for path in wav_paths:
        fname = path.name
        try:
            y, sr = _load_wav(path)
            metrics = _compute_metrics(y, sr)
            soundscape[fname] = metrics
            logger.debug("  %s → NDSI=%.3f  dominant=%s  boat=%.3f",
                         fname, metrics['ndsi_underwater'],
                         metrics['dominant_band'], metrics['boat_score'])
        except Exception as exc:
            logger.warning("  %s — error: %s", fname, exc)
            soundscape[fname] = {'error': str(exc)}

    # Save JSON
    json_out = output_dir / 'soundscape.json'
    json_out.write_text(json.dumps(soundscape, indent=2))
    logger.info("Stage 5 done — soundscape.json written (%d clips)", len(soundscape))
    logger.info("  → %s", json_out)

    # Visualization
    valid = {k: v for k, v in soundscape.items() if 'error' not in v}
    if valid:
        _plot_ndsi_timeseries(valid, output_dir)

    return soundscape
