"""
backend/stage1_3_cascade.py — Stages 1-6: cascade classification.

  Stage 1: Perch 2.0           — Google (2025), ~14k biodiversity classes + embeddings
  Stage 2: Multispecies Whale  — Google (2023), 12 cetacean classes
  Stage 3: Humpback Whale      — Google (2021), specialized binary detector
  Stage 4: NatureLM-BEATs      — Earth Species Project (2025), bioacoustic embeddings
  Stage 5: BioLingual          — David Robinson (2024), zero-shot bioacoustic classification
  Stage 6: Dasheng             — Shanghai AI Lab (2024), structural complexity

Models are loaded once per process (singleton).

Usage:
    from backend.pipeline.stage2_cascade import run_cascade

    results = run_cascade(clip_paths, output_dir=Path("outputs/analysis"))
"""

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
os.environ.setdefault('PYTORCH_ALLOC_CONF', 'expandable_segments:True')
warnings.filterwarnings('ignore')

import tensorflow as tf
import tensorflow_hub as hub

from backend.config import (
    PERCH_BIO_THRESHOLD, PERCH_FALLBACK_BIO_THRESHOLD,
    PERCH_BIO_KEYWORDS, PERCH_MARINE_KEYWORDS,
    BIOLINGUAL_LABELS, BIOLINGUAL_BIO_LABELS,
    MULTISPECIES_THRESHOLD, MULTISPECIES_DETECTION_THR, HUMPBACK_THRESHOLD,
    WHALE_SPECIES,
    DASHENG_TEMPORAL_SCALE, DASHENG_DIVERSITY_SCALE, DASHENG_BIO_THRESHOLD,
    ANALYSIS_DIR, SPECTROGRAMS_DIR, ANNOTATIONS_DIR, RESULTS_FILE,
)

logger = logging.getLogger(__name__)

# ─── Model singleton ──────────────────────────────────────────────────────────

_models: dict = {}


def _get_torch_device():
    import torch
    if torch.backends.mps.is_available():
        return torch.device('mps')
    if torch.cuda.is_available():
        return torch.device('cuda')
    return torch.device('cpu')


def _get_models() -> dict:
    """Loads all 6 models once per process."""
    if _models.get('_ready'):
        return _models

    # Clear any partially-loaded state from a previous failed attempt
    _models.clear()

    logger.info("Loading models (3 CNN + 3 Transformer) — first run takes a while…")

    # Allow TF to grow GPU memory on demand instead of reserving everything upfront.
    # Without this, TF grabs ~4.4 GB at startup, leaving almost nothing for PyTorch.
    gpus = tf.config.list_physical_devices('GPU')
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError:
            pass  # already initialized — harmless

    import torch
    device = _get_torch_device()
    _models['device'] = device
    logger.info("  PyTorch device: %s", device)

    # ── Stage 1: Perch 2.0 ──
    logger.info("  Loading Perch 2.0…")
    try:
        from hoplite.zoo import model_configs as perch_configs
        perch_model = perch_configs.load_model_by_name('perch_v2')
        _models['perch'] = perch_model
        _models['perch_backend'] = 'hoplite'
        try:
            from hoplite.zoo import class_lists
            _models['perch_classes'] = class_lists.get_class_list('perch_v2')
        except Exception:
            _models['perch_classes'] = None
    except Exception as e:
        logger.warning("  perch-hoplite unavailable (%s), using TF Hub fallback…", e)
        perch_model = hub.load(
            'https://www.kaggle.com/models/google/bird-vocalization-classifier/'
            'TensorFlow2/bird-vocalization-classifier/8'
        )
        _models['perch'] = perch_model
        _models['perch_backend'] = 'tfhub'
        _models['perch_classes'] = None

    # ── Stage 2: Multispecies Whale ──
    logger.info("  Loading Multispecies Whale…")
    _models['multispecies'] = hub.load(
        'https://www.kaggle.com/models/google/multispecies-whale/TensorFlow2/default/2'
    )
    meta = _models['multispecies'].metadata()
    _models['multispecies_sr']      = int(meta['input_sample_rate'].numpy())
    _models['multispecies_context'] = int(meta['context_width_samples'].numpy())
    _models['multispecies_classes'] = [n.decode() for n in meta['class_names'].numpy()]

    # ── Stage 3: Humpback Whale ──
    logger.info("  Loading Humpback Whale…")
    _models['humpback'] = hub.load('https://tfhub.dev/google/humpback_whale/1')

    # ── Transformer models (each loaded independently — failures are non-fatal) ──
    logger.info("  Loading Transformer models on %s…", device)

    # Stage 4: NatureLM-BEATs (requires avex: pip install avex)
    logger.info("  Loading NatureLM-BEATs…")
    try:
        from avex import load_model as avex_load
        naturelm = avex_load(
            'esp_aves2_naturelm_audio_v1_beats',
            device=str(device),
        )
        _models['naturelm'] = naturelm
        _models['naturelm_processor'] = None   # avex handles preprocessing internally
        logger.info("  NatureLM-BEATs loaded (avex backend).")
    except Exception as e:
        logger.warning("  NatureLM-BEATs unavailable (%s) — stage 4 will return zeros.", e)
        _models['naturelm'] = None
        _models['naturelm_processor'] = None

    # Stage 5: BioLingual
    logger.info("  Loading BioLingual…")
    try:
        from transformers import pipeline as hf_pipeline
        bl_device_id = device.index or 0 if device.type == 'cuda' else (-1 if device.type == 'cpu' else -1)
        _models['biolingual'] = hf_pipeline(
            task='zero-shot-audio-classification',
            model='davidrrobinson/BioLingual',
            device=bl_device_id,
        )
        logger.info("  BioLingual loaded.")
    except Exception as e:
        logger.warning("  BioLingual unavailable (%s) — stage 5 will return zeros.", e)
        _models['biolingual'] = None

    # Stage 6: Dasheng
    logger.info("  Loading Dasheng…")
    try:
        import dasheng
        dasheng_model = dasheng.dasheng_base()
        dasheng_model.eval()
        dasheng_model.to(device)
        _models['dasheng'] = dasheng_model
        logger.info("  Dasheng loaded.")
    except Exception as e:
        logger.warning("  Dasheng unavailable (%s) — stage 6 will return zeros.", e)
        _models['dasheng'] = None

    loaded = [k for k in ('naturelm', 'biolingual', 'dasheng') if _models.get(k) is not None]
    logger.info("CNN models: Perch+Multispecies+Humpback. Transformer models loaded: %s",
                loaded or 'none')
    _models['_ready'] = True
    return _models


# ─── Stage 1: Perch 2.0 ───────────────────────────────────────────────────────

def _run_perch(y: np.ndarray, sr: int) -> dict:
    m = _get_models()
    model        = m['perch']
    backend      = m['perch_backend']
    class_names  = m.get('perch_classes')

    y_32k = librosa.resample(y, orig_sr=sr, target_sr=32_000) if sr != 32_000 else y

    if backend == 'hoplite':
        output = model.embed(y_32k.astype(np.float32))
        embeddings = np.array(output.embeddings)
        logits = getattr(output, 'logits', None)
        if logits is not None:
            logits = np.array(
                logits.get('label', logits) if isinstance(logits, dict) else logits
            )
            probs = 1 / (1 + np.exp(-logits.mean(axis=0)))
        else:
            probs = None
    else:
        # TF Hub bird-vocalization-classifier expects exactly 160000 samples (5s @ 32kHz).
        # Chunk the audio and aggregate results across chunks.
        CHUNK = 160_000
        y_padded = y_32k.astype(np.float32)
        if len(y_padded) < CHUNK:
            y_padded = np.pad(y_padded, (0, CHUNK - len(y_padded)))
        chunks = [y_padded[i:i + CHUNK] for i in range(0, len(y_padded), CHUNK)]
        # Last chunk: pad to exactly CHUNK samples
        last = chunks[-1]
        if len(last) < CHUNK:
            chunks[-1] = np.pad(last, (0, CHUNK - len(last)))

        all_embeddings, all_logits = [], []
        for chunk in chunks:
            audio_tf = tf.constant(chunk[np.newaxis, :])
            result = model.infer_tf(audio_tf)
            emb_keys = [k for k in result.keys() if 'embed' in k.lower()]
            log_keys = [k for k in result.keys()
                        if any(t in k.lower() for t in ('logit', 'label', 'output_1'))]
            if emb_keys:
                all_embeddings.append(result[emb_keys[0]].numpy())
            if log_keys:
                all_logits.append(result[log_keys[0]].numpy())
        embeddings = np.concatenate(all_embeddings, axis=0) if all_embeddings else np.zeros((1, 1536))
        probs = np.concatenate(all_logits, axis=0).mean(axis=0) if all_logits else None

    bio_detections    = []
    marine_detections = []
    top_classes       = []

    if probs is not None and class_names is not None:
        top_indices = np.argsort(probs)[::-1][:10]
        top_classes = [
            {'class': class_names[i], 'score': round(float(probs[i]), 4)}
            for i in top_indices if i < len(class_names)
        ]
        for idx, prob in enumerate(probs):
            if prob < PERCH_BIO_THRESHOLD or idx >= len(class_names):
                continue
            name_lower = class_names[idx].lower()
            entry = {'class': class_names[idx], 'score': round(float(prob), 4)}
            if any(kw in name_lower for kw in PERCH_BIO_KEYWORDS):
                bio_detections.append(entry)
            if any(kw in name_lower for kw in PERCH_MARINE_KEYWORDS):
                marine_detections.append(entry)

        bio_detections.sort(key=lambda x: -x['score'])
        marine_detections.sort(key=lambda x: -x['score'])

        count_norm   = min(len(bio_detections) / 10.0, 1.0)
        score_norm   = min(sum(d['score'] for d in bio_detections), 1.0)
        marine_boost = min(len(marine_detections) / 3.0, 1.0) * 0.3
        bio_signal   = min((count_norm + score_norm) / 2.0 + marine_boost, 1.0)
    else:
        emb_arr    = np.array(embeddings)
        if emb_arr.ndim == 1:
            emb_arr = emb_arr[np.newaxis, :]
        bio_signal = min(float(np.std(emb_arr)) / 2.0, 1.0)

    return {
        'top_classes':       top_classes,
        'bio_detections':    bio_detections[:10],
        'marine_detections': marine_detections[:5],
        'has_bio_signal':    len(bio_detections) > 0 or bio_signal > (
                                 PERCH_BIO_THRESHOLD if class_names is not None
                                 else PERCH_FALLBACK_BIO_THRESHOLD
                             ),
        'has_marine_signal': len(marine_detections) > 0,
        'bio_signal_score':  round(bio_signal, 4),
    }


# ─── Stage 2: Multispecies Whale ──────────────────────────────────────────────

def _run_multispecies(y: np.ndarray, sr: int) -> dict:
    m           = _get_models()
    target_sr   = m['multispecies_sr']
    context     = m['multispecies_context']
    class_names = m['multispecies_classes']

    if sr != target_sr:
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)

    audio_3d = y.astype(np.float32).reshape(1, -1, 1)
    result   = m['multispecies'].score(
        waveform=tf.constant(audio_3d),
        context_step_samples=tf.constant(context, dtype=tf.int64),
    )
    scores      = result['score'].numpy()
    max_scores  = scores[0].max(axis=0)
    mean_scores = scores[0].mean(axis=0)

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

    confirmed   = [d for d in detections if d['max_score'] >= MULTISPECIES_DETECTION_THR]
    top_score   = float(max_scores[top_idx])
    # bio_signal_score design note:
    # Normalization anchor = MULTISPECIES_DETECTION_THR (0.01), not the original 0.10.
    # Rationale: this model was calibrated on aerial/surface recordings; hydrophone recordings
    # produce scores 10–50x lower (typical range 0.005–0.05 vs 0.05–0.5 surface).
    # Normalizing by 0.01 means "a clip at the detection threshold contributes ~0.5 to bio_signal".
    # This is an intentional domain-adaptation choice — the raw score is not inflated, but
    # the normalization acknowledges the expected score range for underwater audio.
    # Trade-off: aggressive normalization → higher scores for weak detections.
    # Alternative: normalize by 0.10 (original threshold) for more conservative estimates.
    peak_norm   = min(top_score / max(MULTISPECIES_DETECTION_THR, 1e-6), 1.0)
    richness    = min(len(confirmed) / 3.0, 1.0)   # saturates at 3+ confirmed species
    bio_signal  = round(0.5 * peak_norm + 0.5 * richness, 4)

    return {
        'detections':         detections,
        'num_windows':        int(scores.shape[1]),
        'top_species':        class_names[top_idx],
        'top_species_name':   WHALE_SPECIES.get(class_names[top_idx], ''),
        'top_max_score':      round(top_score, 6),
        'top_time_series':    time_series,
        'any_whale_detected': bool(confirmed),
        'bio_signal_score':   bio_signal,
    }


# ─── Stage 3: Humpback ────────────────────────────────────────────────────────

def _run_humpback(y: np.ndarray, sr: int) -> dict:
    m         = _get_models()
    target_sr = 10_000
    if sr != target_sr:
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)

    audio_3d = y.astype(np.float32).reshape(1, -1, 1)
    result   = m['humpback'].score(
        waveform=tf.constant(audio_3d),
        context_step_samples=tf.constant(target_sr, dtype=tf.int64),
    )
    s1d = result['scores'].numpy()[0, :, 0]

    max_s    = float(s1d.max())
    coverage = float((s1d >= HUMPBACK_THRESHOLD).mean())
    # bio_signal_score design note:
    # peak component: max_score normalized by HUMPBACK_THRESHOLD (0.3) — score at threshold = 0.5.
    # coverage component: fraction of windows above threshold, scaled ×2 so 50% coverage → 1.0.
    # Rationale: a clip where half the windows detect humpback is already very strong evidence;
    # saturation at 50% avoids over-rewarding clips that are entirely whale song with no variation.
    bio_signal = round(0.5 * min(max_s / max(HUMPBACK_THRESHOLD, 1e-6), 1.0)
                       + 0.5 * min(coverage * 2.0, 1.0), 4)

    return {
        'max_score':                round(max_s, 6),
        'mean_score':               round(float(s1d.mean()), 6),
        'fraction_above_threshold': round(coverage, 4),
        'num_windows':              int(len(s1d)),
        'humpback_detected':        bool(max_s >= HUMPBACK_THRESHOLD),
        'time_series':              s1d.tolist(),
        'bio_signal_score':         bio_signal,
    }


# ─── Stage 4: NatureLM-BEATs ──────────────────────────────────────────────────

_NATURELM_ZERO = {
    'n_frames': 0, 'embedding_dim': 0, 'norm_mean': 0.0, 'norm_std': 0.0,
    'magnitude_score': 0.0, 'embedding_entropy': 0.0, 'entropy_score': 0.0,
    'bio_signal_score': 0.0,
}

def _run_naturelm(y: np.ndarray, sr: int) -> dict:
    import torch
    m      = _get_models()
    model  = m['naturelm']
    if model is None:
        return _NATURELM_ZERO
    device = m['device']

    # avex expects 16kHz mono float32 tensor, returns (batch, time_steps, 768)
    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16_000) if sr != 16_000 else y
    if len(y_16k) > 60 * 16_000:
        y_16k = y_16k[:60 * 16_000]

    audio_tensor = torch.from_numpy(y_16k).float().unsqueeze(0).to(device)
    with torch.no_grad():
        output = model(audio_tensor)

    # avex returns tensor (batch, time_steps, 768); squeeze batch dim
    if isinstance(output, torch.Tensor):
        embeddings = output.squeeze(0).cpu().numpy()
    else:
        # fallback for unexpected output type
        out = output[0] if isinstance(output, (tuple, list)) else output
        embeddings = (out.squeeze(0).cpu().numpy()
                      if isinstance(out, torch.Tensor) else np.array(out))

    if embeddings.ndim == 1:
        embeddings = embeddings[np.newaxis, :]

    norms          = np.linalg.norm(embeddings, axis=1)
    norm_mean      = float(norms.mean())
    norm_std       = float(norms.std())
    magnitude_score = min(norm_std / (norm_mean + 1e-8), 1.0)

    mean_emb      = np.abs(embeddings.mean(axis=0))
    mean_emb_norm = mean_emb / (mean_emb.sum() + 1e-8)
    entropy       = -np.sum(mean_emb_norm * np.log(mean_emb_norm + 1e-12))
    max_entropy   = np.log(len(mean_emb_norm))
    entropy_score = min(float(entropy / max_entropy), 1.0)

    bio_signal = 0.4 * magnitude_score + 0.6 * entropy_score

    return {
        'n_frames':          int(embeddings.shape[0]),
        'embedding_dim':     int(embeddings.shape[1]),
        'norm_mean':         round(norm_mean, 4),
        'norm_std':          round(norm_std, 4),
        'magnitude_score':   round(magnitude_score, 4),
        'embedding_entropy': round(float(entropy), 4),
        'entropy_score':     round(entropy_score, 4),
        'bio_signal_score':  round(bio_signal, 4),
    }


# ─── Stage 5: BioLingual ──────────────────────────────────────────────────────

_BIOLINGUAL_ZERO = {
    'label_scores': {}, 'top_label': 'unavailable', 'top_score': 0.0,
    'bio_score_sum': 0.0, 'top_is_bio': False, 'bio_signal_score': 0.0,
}

def _run_biolingual(y: np.ndarray, sr: int) -> dict:
    m          = _get_models()
    classifier = m['biolingual']
    if classifier is None:
        return _BIOLINGUAL_ZERO

    y_48k = librosa.resample(y, orig_sr=sr, target_sr=48_000) if sr != 48_000 else y
    if len(y_48k) > 30 * 48_000:
        y_48k = y_48k[:30 * 48_000]

    results     = classifier(y_48k, candidate_labels=BIOLINGUAL_LABELS)
    label_scores = {r['label']: round(r['score'], 4) for r in results}

    bio_sum   = sum(label_scores.get(l, 0) for l in BIOLINGUAL_BIO_LABELS)
    top_label = results[0]['label']
    top_score = results[0]['score']
    bio_signal = min(bio_sum, 1.0)

    return {
        'label_scores':    label_scores,
        'top_label':       top_label,
        'top_score':       round(top_score, 4),
        'bio_score_sum':   round(bio_sum, 4),
        'top_is_bio':      top_label in BIOLINGUAL_BIO_LABELS,
        'bio_signal_score': round(bio_signal, 4),
    }


# ─── Stage 6: Dasheng ─────────────────────────────────────────────────────────

_DASHENG_ZERO = {
    'n_frames': 0, 'temporal_variance': 0.0, 'half_cosine_similarity': 1.0,
    'temporal_diversity_score': 0.0, 'bio_signal_score': 0.0,
}

def _run_dasheng(y: np.ndarray, sr: int) -> dict:
    import torch
    m             = _get_models()
    dasheng_model = m['dasheng']
    if dasheng_model is None:
        return _DASHENG_ZERO
    device        = m['device']

    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16_000) if sr != 16_000 else y
    if len(y_16k) > 60 * 16_000:
        y_16k = y_16k[:60 * 16_000]

    audio_tensor = torch.from_numpy(y_16k).float().unsqueeze(0).to(device)
    with torch.no_grad():
        output = dasheng_model(audio_tensor)

    embeddings = output.squeeze(0).cpu().numpy()

    if embeddings.shape[0] > 1:
        diffs             = np.diff(embeddings, axis=0)
        temporal_variance = float(np.mean(np.linalg.norm(diffs, axis=1)))
    else:
        temporal_variance = 0.0

    mid = embeddings.shape[0] // 2
    if mid > 0:
        first   = embeddings[:mid].mean(axis=0)
        second  = embeddings[mid:].mean(axis=0)
        cos_sim = float(np.dot(first, second) /
                        (np.linalg.norm(first) * np.linalg.norm(second) + 1e-8))
    else:
        cos_sim = 1.0

    diversity_score = 1.0 - cos_sim
    bio_signal = (0.5 * min(temporal_variance / DASHENG_TEMPORAL_SCALE, 1.0) +
                  0.5 * min(diversity_score / DASHENG_DIVERSITY_SCALE, 1.0))

    return {
        'n_frames':                int(embeddings.shape[0]),
        'temporal_variance':       round(temporal_variance, 4),
        'half_cosine_similarity':  round(cos_sim, 4),
        'temporal_diversity_score':round(diversity_score, 4),
        'bio_signal_score':        round(bio_signal, 4),
    }


# ─── Spectrogram (6 panels) ───────────────────────────────────────────────────

def _save_spectrogram(
    y: np.ndarray, sr: int, fname: str,
    s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, s6: dict,
    out_dir: Path,
) -> str:
    fig, axes = plt.subplots(6, 1, figsize=(18, 22),
                             gridspec_kw={'height_ratios': [3, 1, 1, 1, 1, 1]})

    # Panel 1: Mel spectrogram
    S_db = librosa.power_to_db(
        librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, n_fft=2048, hop_length=512),
        ref=np.max,
    )
    img = librosa.display.specshow(S_db, sr=sr, x_axis='time', y_axis='mel',
                                   ax=axes[0], hop_length=512)
    fig.colorbar(img, ax=axes[0], format='%+2.0f dB')
    flags = ((['BIO']     if s1.get('has_bio_signal')    else []) +
             (['WHALE']   if s2.get('any_whale_detected') else []) +
             (['HUMPBACK']if s3.get('humpback_detected')  else []))
    axes[0].set_title(f"{fname}  [{' | '.join(flags) or 'NO DETECTIONS'}]",
                      fontsize=12, fontweight='bold')

    # Panel 2: Perch 2.0 top classes
    top_p = s1.get('top_classes', [])[:8]
    if top_p:
        marine_set = {c['class'] for c in s1.get('marine_detections', [])}
        labels = [c['class'][:35] for c in top_p]
        vals   = [c['score'] for c in top_p]
        colors = ['#e74c3c' if c['class'] in marine_set else '#2ecc71' for c in top_p]
        axes[1].barh(range(len(labels)), vals, color=colors)
        axes[1].set_yticks(range(len(labels)))
        axes[1].set_yticklabels(labels, fontsize=7)
        axes[1].set_xlim(0, 1)
        axes[1].invert_yaxis()
    axes[1].set_title(
        f'Perch 2.0 [CNN] — bio: {s1.get("bio_signal_score", 0):.2f}'
        '  (marine=red, other bio=green)', fontsize=9)

    # Panel 3: Multispecies time-series
    ts = s2.get('top_time_series', [])
    if ts:
        axes[2].plot(np.linspace(0, len(y) / sr, len(ts)), ts, color='#e74c3c', linewidth=1)
        axes[2].axhline(MULTISPECIES_THRESHOLD, color='orange', linestyle='--', alpha=0.7)
        axes[2].grid(True, alpha=0.3)
    top_sp = s2.get('top_species', '?')
    axes[2].set_title(
        f"Multispecies Whale [CNN] — {top_sp} ({WHALE_SPECIES.get(top_sp, '')})", fontsize=9)

    # Panel 4: Humpback time-series
    ht = s3.get('time_series', [])
    if ht:
        axes[3].plot(np.linspace(0, len(y) / sr, len(ht)), ht, color='#3498db', linewidth=1)
        axes[3].axhline(HUMPBACK_THRESHOLD, color='orange', linestyle='--', alpha=0.7)
        axes[3].set_xlabel('Time (s)')
        axes[3].grid(True, alpha=0.3)
    axes[3].set_title('Humpback Whale Detector [CNN]', fontsize=9)

    # Panel 5: NatureLM-BEATs metrics
    mag  = s4.get('magnitude_score', 0)
    ent  = s4.get('entropy_score', 0)
    bio4 = s4.get('bio_signal_score', 0)
    axes[4].bar(
        ['Magnitude\nVariance', 'Embedding\nEntropy', 'Bio Signal'],
        [mag, ent, bio4],
        color=['#1abc9c', '#16a085', '#0e6655'],
    )
    axes[4].set_ylim(0, 1)
    axes[4].set_title(
        f'NatureLM-BEATs [Transformer] — '
        f'mag: {mag:.2f}  entropy: {ent:.2f}  bio: {bio4:.2f}', fontsize=9)

    # Panel 6: BioLingual + Dasheng
    bl = s5.get('label_scores', {})
    tv = s6.get('temporal_variance', 0)
    td = s6.get('temporal_diversity_score', 0)
    if bl:
        sorted_bl = sorted(bl.items(), key=lambda x: -x[1])
        bll = [l[:25] for l, _ in sorted_bl]
        blv = [s for _, s in sorted_bl]
        blc = ['#2ecc71' if l in BIOLINGUAL_BIO_LABELS else '#95a5a6' for l, _ in sorted_bl]
        axes[5].barh(range(len(bll)), blv, color=blc, alpha=0.85)
        axes[5].set_yticks(range(len(bll)))
        axes[5].set_yticklabels(bll, fontsize=7)
        axes[5].set_xlim(0, 1)
        axes[5].invert_yaxis()
    axes[5].set_title(
        f'BioLingual [Transformer] — top: {s5.get("top_label", "?")} '
        f'bio: {s5.get("bio_signal_score", 0):.2f}  |  '
        f'Dasheng [Transformer] — var: {tv:.2f}  div: {td:.2f}  '
        f'bio: {s6.get("bio_signal_score", 0):.2f}', fontsize=9)

    plt.tight_layout()
    stem      = Path(fname).stem
    out_path  = out_dir / f"{stem}_cascade.png"
    fig.savefig(str(out_path), dpi=120)
    plt.close(fig)
    return out_path.name


# ─── Single-file backend ──────────────────────────────────────────────────────

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

        import torch
        def _gc():
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        s1 = _run_perch(y, sr);      _gc()
        s2 = _run_multispecies(y, sr); _gc()
        s3 = _run_humpback(y, sr);   _gc()
        s4 = _run_naturelm(y, sr);   _gc()
        s5 = _run_biolingual(y, sr); _gc()
        s6 = _run_dasheng(y, sr);    _gc()

        spec_name = _save_spectrogram(y, sr, fname, s1, s2, s3, s4, s5, s6, spec_dir)

        # Flags
        flags = []
        if s1['has_bio_signal']:          flags.append('biological_audio')
        if s1['has_marine_signal']:       flags.append('marine_environment')
        if s2['any_whale_detected']:      flags.append('whale_species')
        if s3['humpback_detected']:       flags.append('humpback')
        if s4['bio_signal_score'] > 0.4:                    flags.append('naturelm_bio')
        if s5.get('top_is_bio', False):                     flags.append('biolingual_bio')
        if s6['bio_signal_score'] > DASHENG_BIO_THRESHOLD:  flags.append('dasheng_complex')

        # Annotations
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
            annotations.append(f"Perch bio: {', '.join(names)}")
        if s4['bio_signal_score'] > 0.4:
            annotations.append(
                f"NatureLM: entropy={s4['embedding_entropy']:.2f}, "
                f"mag_var={s4['norm_std']:.2f}")
        if s5.get('top_is_bio'):
            annotations.append(f"BioLingual: {s5['top_label']} ({s5['top_score']:.3f})")
        if not annotations:
            annotations.append('No marine biological signals detected')

        result = {
            'filename':            fname,
            'source_path':         str(wav_path),
            'duration_s':          round(duration, 2),
            'sample_rate':         sr,
            'rms':                 round(rms, 8),
            'status':              'analyzed',
            'cascade_flags':       flags,
            'cascade_summary':     '; '.join(flags) if flags else 'no_detections',
            'stage1_perch':        s1,
            'stage2_multispecies': s2,
            'stage3_humpback':     s3,
            'stage4_naturelm':     s4,
            'stage5_biolingual':   s5,
            'stage6_dasheng':      s6,
            'annotations':         annotations,
            'spectrogram':         spec_name,
        }

        ann_path = ann_dir / f"{wav_path.stem}_cascade.json"
        ann_path.write_text(json.dumps(result, indent=2))

        return result

    except Exception as exc:
        logger.error("Error processing %s: %s", fname, exc)
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
    Runs the 6-model cascade on a list of WAVs.
    Returns dict {filename: result}.
    """
    spec_dir = output_dir / "spectrograms"
    ann_dir  = output_dir / "annotations"
    spec_dir.mkdir(parents=True, exist_ok=True)
    ann_dir.mkdir(parents=True, exist_ok=True)

    if not wav_paths:
        logger.warning("run_cascade: no WAV paths provided")
        return {}

    logger.info("Stages 1-6 — cascade over %d clip(s)", len(wav_paths))
    results: Dict[str, dict] = {}

    for i, path in enumerate(wav_paths, 1):
        logger.info("  [%d/%d] %s", i, len(wav_paths), path.name)
        result = _classify_one(path, spec_dir, ann_dir)
        results[path.name] = result

        flags = result.get('cascade_flags', [])
        logger.info("    → %s", ', '.join(flags) if flags else 'no detections')

    results_path = output_dir / "results.json"
    results_path.write_text(json.dumps({
        'backend':        'Cascade v3.0 (6-model: 3 CNN + 3 Transformer)',
        'total_files':     len(results),
        'bio_signals':     sum(1 for r in results.values() if 'biological_audio' in r.get('cascade_flags', [])),
        'whale_detected':  sum(1 for r in results.values() if 'whale_species'    in r.get('cascade_flags', [])),
        'humpback_detected':sum(1 for r in results.values() if 'humpback'        in r.get('cascade_flags', [])),
        'naturelm_bio':    sum(1 for r in results.values() if 'naturelm_bio'     in r.get('cascade_flags', [])),
        'biolingual_bio':  sum(1 for r in results.values() if 'biolingual_bio'   in r.get('cascade_flags', [])),
        'dasheng_complex': sum(1 for r in results.values() if 'dasheng_complex'  in r.get('cascade_flags', [])),
        'errors':          sum(1 for r in results.values() if r.get('status') == 'error'),
        'files':           results,
    }, indent=2))

    logger.info("Stages 1-6 done — results → %s", results_path)
    return results
