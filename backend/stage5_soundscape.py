"""
backend/stage5_soundscape.py — Stage 5: Soundscape characterization.

Calcula índices acústicos adaptados para el océano sobre cada clip WAV.
No requiere GPU. Usa scikit-maad para entropías y computa bandas de potencia
personalizadas para contexto marino (no defaults terrestres).

Métricas por clip:
  ndsi_underwater   — ratio BIO / (ANTHRO + BIO); > 0.5 = dominado por biología
  band_power_low    — energía relativa en 50–2000 Hz  (barcos, peces)
  band_power_mid    — energía relativa en 2–10 kHz    (camarones, delfines bajos)
  band_power_high   — energía relativa en 10–48 kHz   (ecolocación, delfines)
  temporal_entropy  — diversidad temporal de la señal  (maad.features.temporal_entropy)
  spectral_entropy  — diversidad espectral              (maad.features.spectral_entropy)
  dominant_band     — LOW | MID | HIGH (cuál tiene más energía)
  boat_score        — proxy de ruido de barco (band_power_low normalizado)

Uso:
    from backend.stage5_soundscape import run_soundscape
    soundscape = run_soundscape(clip_paths, output_dir=Path("outputs/soundscape"))
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


# ─── Límites de banda (Hz) ────────────────────────────────────────────────────
_ANTHRO_LOW_HZ  = (50,   1_000)   # ruido antropogénico dominante
_BIO_LOW_HZ     = (50,   2_000)   # peces, barcos mezclados
_BIO_BAND_HZ    = (2_000, 20_000) # biología marina principal
_MID_HZ         = (2_000, 10_000) # camarones, delfines bajos
_HIGH_HZ        = (10_000, 48_000) # ecolocación, delfines altos


def _load_wav(path: Path):
    """Carga WAV con librosa; devuelve (y, sr)."""
    import librosa
    y, sr = librosa.load(str(path), sr=None, mono=True)
    return y, sr


def _band_power(psd: np.ndarray, freqs: np.ndarray, low: float, high: float) -> float:
    """Potencia integrada en una banda de frecuencia."""
    mask = (freqs >= low) & (freqs <= high)
    if not mask.any():
        return 0.0
    return float(np.sum(psd[mask]))


def _compute_metrics(y: np.ndarray, sr: int) -> dict:
    """Calcula métricas acústicas para un array de audio."""
    from scipy.signal import welch

    nperseg = min(len(y), 4096)
    freqs, psd = welch(y, fs=sr, nperseg=nperseg)

    total_power = np.sum(psd) + 1e-12

    # Bandas de potencia relativa
    p_anthro = _band_power(psd, freqs, *_ANTHRO_LOW_HZ) / total_power
    p_bio    = _band_power(psd, freqs, *_BIO_BAND_HZ)   / total_power
    p_low    = _band_power(psd, freqs, *_BIO_LOW_HZ)    / total_power
    p_mid    = _band_power(psd, freqs, *_MID_HZ)        / total_power
    p_high   = _band_power(psd, freqs, *_HIGH_HZ)       / total_power

    # NDSI submarino: ratio biología vs (ruido + biología)
    denom = p_anthro + p_bio
    ndsi = float((p_bio - p_anthro) / denom) if denom > 1e-12 else 0.0
    ndsi = float(np.clip(ndsi, -1.0, 1.0))

    # Entropías con scikit-maad (si disponible), sino scipy fallback
    temporal_entropy = _temporal_entropy(y)
    spectral_entropy = _spectral_entropy(psd)

    # Banda dominante
    bands = {'LOW': p_low, 'MID': p_mid, 'HIGH': p_high}
    dominant_band = max(bands, key=bands.get)

    # boat_score: potencia baja normalizada a [0,1]
    boat_score = float(np.clip(p_low * 5, 0.0, 1.0))  # escala empírica

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
    """Entropía de Wiener sobre la envolvente temporal (maad o scipy fallback)."""
    try:
        import maad.features as mf
        import maad.sound as ms
        # maad espera (y, sr) pero temporal_entropy sólo necesita y
        return float(mf.temporal_entropy(y))
    except Exception:
        pass
    # Fallback: entropía de la distribución de amplitudes
    env = np.abs(y) + 1e-12
    env = env / env.sum()
    return float(-np.sum(env * np.log(env + 1e-12)) / np.log(len(env)))


def _spectral_entropy(psd: np.ndarray) -> float:
    """Entropía espectral de Wiener (maad o scipy fallback)."""
    try:
        import maad.features as mf
        return float(mf.spectral_entropy(psd))
    except Exception:
        pass
    p = psd + 1e-12
    p = p / p.sum()
    return float(-np.sum(p * np.log(p)) / np.log(len(p)))


def _plot_ndsi_timeseries(soundscape: Dict[str, dict], output_dir: Path) -> None:
    """Genera un PNG con la serie temporal del NDSI por clip."""
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
    Calcula índices de soundscape para cada clip WAV.

    Args:
        wav_paths:  Lista de rutas WAV (clips del Stage 0).
        output_dir: Carpeta donde se guarda soundscape.json y la visualización.

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

    # Guardar JSON
    json_out = output_dir / 'soundscape.json'
    json_out.write_text(json.dumps(soundscape, indent=2))
    logger.info("Stage 5 done — soundscape.json escrito (%d clips)", len(soundscape))
    logger.info("  → %s", json_out)

    # Visualización
    valid = {k: v for k, v in soundscape.items() if 'error' not in v}
    if valid:
        _plot_ndsi_timeseries(valid, output_dir)

    return soundscape
