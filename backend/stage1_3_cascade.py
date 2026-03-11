"""
backend/stage1_3_cascade.py — Stages 1-3: clasificación en cascada.

  Stage 1: YAMNet      — 521 clases AudioSet, señal biológica/marina/ruido
  Stage 2: Multispecies Whale — 12 clases cetáceos (Orca, Jorobada, Azul…)
  Stage 3: Humpback Whale    — detector especializado binario

Los modelos se cargan una sola vez por proceso (singleton).

Uso:
    from backend.stage1_3_cascade import run_cascade

    results = run_cascade(clip_paths, output_dir=Path("outputs/analysis"))
"""

import csv
import json
import logging
import os
import warnings
from pathlib import Path
from typing import Dict, List

import numpy as np
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore')

import tensorflow as tf
import tensorflow_hub as hub

from backend.config import (
    YAMNET_TOP_K, YAMNET_BIO_THRESHOLD,
    YAMNET_BIO_KEYWORDS, YAMNET_MARINE_KEYWORDS, YAMNET_NOISE_KEYWORDS,
    MULTISPECIES_THRESHOLD, MULTISPECIES_DETECTION_THR, HUMPBACK_THRESHOLD,
    WHALE_SPECIES,
    ANALYSIS_DIR, SPECTROGRAMS_DIR, ANNOTATIONS_DIR, RESULTS_FILE,
)

logger = logging.getLogger(__name__)

# ─── Model singleton ──────────────────────────────────────────────────────────

_models: dict = {}

def _get_models() -> dict:
    """Carga los 3 modelos una vez por proceso."""
    if _models:
        return _models

    logger.info("Cargando modelos TF (esto puede tardar la primera vez)…")

    _models['yamnet'] = hub.load('https://tfhub.dev/google/yamnet/1')
    class_map_path = _models['yamnet'].class_map_path().numpy().decode()
    with open(class_map_path) as f:
        _models['yamnet_classes'] = [row['display_name'] for row in csv.DictReader(f)]

    _models['multispecies'] = hub.load(
        'https://www.kaggle.com/models/google/multispecies-whale/TensorFlow2/default/2'
    )
    meta = _models['multispecies'].metadata()
    _models['multispecies_sr']      = int(meta['input_sample_rate'].numpy())
    _models['multispecies_context'] = int(meta['context_width_samples'].numpy())
    _models['multispecies_classes'] = [n.decode() for n in meta['class_names'].numpy()]

    _models['humpback'] = hub.load('https://tfhub.dev/google/humpback_whale/1')

    logger.info("Modelos cargados.")
    return _models


# ─── Stage 1: YAMNet ──────────────────────────────────────────────────────────

def _run_yamnet(y: np.ndarray, sr: int) -> dict:
    m = _get_models()
    if sr != 16_000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16_000)

    scores, embeddings, _ = m['yamnet'](tf.constant(y.astype(np.float32)))
    mean_scores = scores.numpy().mean(axis=0)
    class_names = m['yamnet_classes']

    top_idx    = np.argsort(mean_scores)[::-1][:YAMNET_TOP_K]
    top_classes = [{'class': class_names[i], 'score': round(float(mean_scores[i]), 4)}
                   for i in top_idx]

    bio, marine, noise = [], [], []
    for i, score in enumerate(mean_scores):
        if score < YAMNET_BIO_THRESHOLD:
            continue
        name = class_names[i].lower()
        entry = {'class': class_names[i], 'score': round(float(score), 4)}
        if any(kw in name for kw in YAMNET_BIO_KEYWORDS):
            bio.append(entry)
        if any(kw in name for kw in YAMNET_MARINE_KEYWORDS):
            marine.append(entry)
        if any(kw in name for kw in YAMNET_NOISE_KEYWORDS):
            noise.append(entry)

    mean_emb = embeddings.numpy().mean(axis=0)
    return {
        'top_classes':      sorted(top_classes, key=lambda x: -x['score']),
        'bio_detections':   sorted(bio,    key=lambda x: -x['score']),
        'marine_detections':sorted(marine, key=lambda x: -x['score']),
        'noise_detections': sorted(noise,  key=lambda x: -x['score']),
        'has_bio_signal':   len(bio) > 0,
        'has_marine_signal':len(marine) > 0,
        'embedding_norm':   round(float(np.linalg.norm(mean_emb)), 4),
    }


# ─── Stage 2: Multispecies Whale ──────────────────────────────────────────────

def _run_multispecies(y: np.ndarray, sr: int) -> dict:
    m          = _get_models()
    target_sr  = m['multispecies_sr']     # 24 000
    context    = m['multispecies_context'] # 120 000 (5 s)
    class_names = m['multispecies_classes']

    if sr != target_sr:
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)

    audio_3d = y.astype(np.float32).reshape(1, -1, 1)
    result   = m['multispecies'].score(
        waveform=tf.constant(audio_3d),
        context_step_samples=tf.constant(context, dtype=tf.int64),
    )
    scores     = result['score'].numpy()  # (1, T, 12)
    max_scores = scores[0].max(axis=0)
    mean_scores= scores[0].mean(axis=0)

    detections = [
        {
            'class_code': cls,
            'species':    WHALE_SPECIES.get(cls, cls),
            'max_score':  round(float(max_scores[i]), 6),
            'mean_score': round(float(mean_scores[i]), 6),
        }
        for i, cls in enumerate(class_names)
        if max_scores[i] >= MULTISPECIES_THRESHOLD
    ]
    detections.sort(key=lambda x: -x['max_score'])

    top_idx     = int(np.argmax(max_scores))
    time_series = scores[0, :, top_idx].tolist()

    return {
        'detections':       detections,
        'num_windows':      int(scores.shape[1]),
        'top_species':      class_names[top_idx],
        'top_species_name': WHALE_SPECIES.get(class_names[top_idx], ''),
        'top_max_score':    round(float(max_scores[top_idx]), 6),
        'top_time_series':  time_series,
        'any_whale_detected': any(d['max_score'] >= MULTISPECIES_DETECTION_THR for d in detections),
    }


# ─── Stage 3: Humpback ────────────────────────────────────────────────────────

def _run_humpback(y: np.ndarray, sr: int) -> dict:
    m = _get_models()
    target_sr = 10_000
    if sr != target_sr:
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)

    audio_3d = y.astype(np.float32).reshape(1, -1, 1)
    result   = m['humpback'].score(
        waveform=tf.constant(audio_3d),
        context_step_samples=tf.constant(target_sr, dtype=tf.int64),
    )
    s1d = result['scores'].numpy()[0, :, 0]

    return {
        'max_score':               round(float(s1d.max()), 6),
        'mean_score':              round(float(s1d.mean()), 6),
        'fraction_above_threshold':round(float((s1d >= HUMPBACK_THRESHOLD).mean()), 4),
        'num_windows':             int(len(s1d)),
        'humpback_detected':       bool(s1d.max() >= HUMPBACK_THRESHOLD),
        'time_series':             s1d.tolist(),
    }


# ─── Spectrogram ──────────────────────────────────────────────────────────────

def _save_spectrogram(
    y: np.ndarray, sr: int, fname: str,
    s1: dict, s2: dict, s3: dict,
    out_dir: Path,
) -> str:
    fig, axes = plt.subplots(4, 1, figsize=(16, 14),
                             gridspec_kw={'height_ratios': [3, 1, 1, 1]})

    S_db = librosa.power_to_db(
        librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, n_fft=2048, hop_length=512),
        ref=np.max,
    )
    img = librosa.display.specshow(S_db, sr=sr, x_axis='time', y_axis='mel',
                                   ax=axes[0], hop_length=512)
    fig.colorbar(img, ax=axes[0], format='%+2.0f dB')

    flags = ((['BIO']     if s1.get('has_bio_signal')          else []) +
             (['WHALE']   if s2.get('any_whale_detected')       else []) +
             (['HUMPBACK']if s3.get('humpback_detected')        else []))
    axes[0].set_title(f"{fname}  [{' | '.join(flags) or 'NO DETECTIONS'}]",
                      fontsize=12, fontweight='bold')

    # YAMNet bar chart
    top = s1.get('top_classes', [])
    if top:
        names  = [c['class'][:25] for c in top]
        scores = [c['score']      for c in top]
        colors = ['#2ecc71' if any(kw in c['class'].lower()
                  for kw in YAMNET_BIO_KEYWORDS | YAMNET_MARINE_KEYWORDS)
                  else '#95a5a6' for c in top]
        axes[1].barh(range(len(names)), scores, color=colors)
        axes[1].set_yticks(range(len(names)))
        axes[1].set_yticklabels(names, fontsize=8)
        axes[1].set_xlim(0, 1)
        axes[1].set_title('Stage 1: YAMNet', fontsize=10)
        axes[1].invert_yaxis()

    # Multispecies time-series
    ts = s2.get('top_time_series', [])
    if ts:
        axes[2].plot(np.linspace(0, len(y) / sr, len(ts)), ts, color='#e74c3c', linewidth=1)
        axes[2].axhline(MULTISPECIES_THRESHOLD, color='orange', linestyle='--', alpha=0.7)
        top_sp = s2.get('top_species', '?')
        axes[2].set_title(
            f"Stage 2: Multispecies — {top_sp} ({WHALE_SPECIES.get(top_sp, '')})", fontsize=10)
        axes[2].grid(True, alpha=0.3)

    # Humpback time-series
    ht = s3.get('time_series', [])
    if ht:
        axes[3].plot(np.linspace(0, len(y) / sr, len(ht)), ht, color='#3498db', linewidth=1)
        axes[3].axhline(HUMPBACK_THRESHOLD, color='orange', linestyle='--', alpha=0.7)
        axes[3].set_title('Stage 3: Humpback Whale Detector', fontsize=10)
        axes[3].set_xlabel('Time (s)')
        axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    stem = Path(fname).stem
    out_path = out_dir / f"{stem}_cascade.png"
    fig.savefig(str(out_path), dpi=120)
    plt.close(fig)
    return out_path.name


# ─── Single-file backend ─────────────────────────────────────────────────────

def _classify_one(wav_path: Path, spec_dir: Path, ann_dir: Path) -> dict:
    fname = wav_path.name
    try:
        y, sr    = librosa.load(str(wav_path), sr=None, mono=True)
        duration = len(y) / sr
        rms      = float(np.sqrt(np.mean(y ** 2)))

        if rms < 1e-7:
            return {
                'filename': fname, 'duration_s': round(duration, 2),
                'sample_rate': sr, 'status': 'silent',
                'cascade_flags': [], 'cascade_summary': 'silent',
                'annotations': ['File is silent'],
            }

        s1 = _run_yamnet(y, sr)
        s2 = _run_multispecies(y, sr)
        s3 = _run_humpback(y, sr)

        spec_name = _save_spectrogram(y, sr, fname, s1, s2, s3, spec_dir)

        # Flags y anotaciones
        flags = []
        if s1['has_bio_signal']:    flags.append('biological_audio')
        if s2['any_whale_detected']:flags.append('whale_species')
        if s3['humpback_detected']: flags.append('humpback')
        if s1['has_marine_signal']: flags.append('marine_environment')

        annotations = []
        for d in s2['detections']:
            label = 'Whale' if d['max_score'] >= MULTISPECIES_DETECTION_THR else 'Possible whale'
            annotations.append(f"{label}: {d['species']} (score={d['max_score']:.4f})")
        if s3['humpback_detected']:
            annotations.append(
                f"Humpback detected (max={s3['max_score']:.4f}, "
                f"{s3['fraction_above_threshold']:.0%} of windows)")
        if s1['has_bio_signal']:
            names = [d['class'] for d in s1['bio_detections'][:3]]
            annotations.append(f"YAMNet bio: {', '.join(names)}")
        if not annotations:
            annotations.append('No marine biological signals detected')

        result = {
            'filename':         fname,
            'source_path':      str(wav_path),
            'duration_s':       round(duration, 2),
            'sample_rate':      sr,
            'rms':              round(rms, 8),
            'status':           'analyzed',
            'cascade_flags':    flags,
            'cascade_summary':  '; '.join(flags) if flags else 'no_detections',
            'stage1_yamnet':    s1,
            'stage2_multispecies': s2,
            'stage3_humpback':  s3,
            'annotations':      annotations,
            'spectrogram':      spec_name,
        }

        ann_path = ann_dir / f"{wav_path.stem}_cascade.json"
        ann_path.write_text(json.dumps(result, indent=2))

        return result

    except Exception as exc:
        logger.error("Error procesando %s: %s", fname, exc)
        return {
            'filename': fname, 'status': 'error',
            'error': str(exc), 'annotations': [f'Error: {exc}'],
        }


# ─── Public API ───────────────────────────────────────────────────────────────

def run_cascade(
    wav_paths: List[Path],
    output_dir: Path = ANALYSIS_DIR,
) -> Dict[str, dict]:
    """
    Corre el cascade sobre una lista de WAVs.
    Devuelve dict {filename: result}.
    """
    spec_dir = output_dir / "spectrograms"
    ann_dir  = output_dir / "annotations"
    spec_dir.mkdir(parents=True, exist_ok=True)
    ann_dir.mkdir(parents=True, exist_ok=True)

    if not wav_paths:
        logger.warning("run_cascade: no WAV paths provided")
        return {}

    logger.info("Stage 1-3 — cascade sobre %d clip(s)", len(wav_paths))
    results: Dict[str, dict] = {}

    for i, path in enumerate(wav_paths, 1):
        logger.info("  [%d/%d] %s", i, len(wav_paths), path.name)
        result = _classify_one(path, spec_dir, ann_dir)
        results[path.name] = result

        flags = result.get('cascade_flags', [])
        logger.info("    → %s", ', '.join(flags) if flags else 'no detections')

    consolidated = results

    results_path = output_dir / "results.json"
    results_path.write_text(json.dumps({
        'backend': 'Cascade v2.0 (Stage 0 integrated)',
        'total_files': len(results),
        'bio_signals':        sum(1 for r in results.values() if 'biological_audio' in r.get('cascade_flags', [])),
        'whale_detected':     sum(1 for r in results.values() if 'whale_species'    in r.get('cascade_flags', [])),
        'humpback_detected':  sum(1 for r in results.values() if 'humpback'         in r.get('cascade_flags', [])),
        'errors':             sum(1 for r in results.values() if r.get('status') == 'error'),
        'files': consolidated,
    }, indent=2))

    logger.info("Stage 1-3 done — results → %s", results_path)
    return results
