"""
Cascade Classifier Pipeline for Marine Audio Analysis.

Processes WAV files through a cascade of pre-trained models:
  Stage 1: YAMNet — general audio classification (biological vs non-biological)
  Stage 2: Multispecies Whale Detector — 12-class whale/dolphin identification
  Stage 3: Humpback Whale Detector — specialized humpback vocalization scoring

Each stage enriches the output with model-specific scores and classifications.
Uses multiprocessing with max 2 workers for parallel processing.

Usage:
    python3 -u cascade_classifier.py
"""

import json
import multiprocessing as mp
import os
import sys
import traceback
import warnings
from pathlib import Path

import numpy as np
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Suppress TF warnings for cleaner output
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings('ignore')

import tensorflow as tf
import tensorflow_hub as hub

# ─── Configuration ───────────────────────────────────────────────────────────

INPUT_DIR = Path("Music_Soundtrap_Pilot")
OUTPUT_DIR = Path("output2")
SPECTROGRAMS_DIR = OUTPUT_DIR / "spectrograms"
ANNOTATIONS_DIR = OUTPUT_DIR / "annotations"
RESULTS_FILE = OUTPUT_DIR / "cascade_results.json"

MAX_WORKERS = 2

# YAMNet biological/marine-related class indices (from AudioSet ontology)
# These are the class names from YAMNet that indicate biological or
# marine-related audio content.
YAMNET_BIO_KEYWORDS = {
    'animal', 'whale', 'bird', 'insect', 'frog', 'cricket', 'cat', 'dog',
    'roar', 'howl', 'bark', 'chirp', 'tweet', 'squawk', 'coo', 'crow',
    'singing', 'music', 'speech',
}
YAMNET_MARINE_KEYWORDS = {
    'whale', 'water', 'ocean', 'rain', 'thunder', 'stream', 'waterfall',
    'splash', 'waves',
}
YAMNET_NOISE_KEYWORDS = {
    'silence', 'white noise', 'static', 'hum', 'buzz',
}

# Multispecies whale model class name mapping
WHALE_SPECIES = {
    'Oo': 'Orcinus orca (Killer whale / Orca)',
    'Mn': 'Megaptera novaeangliae (Humpback whale)',
    'Eg': 'Eubalaena glacialis (North Atlantic right whale)',
    'Be': 'Mesoplodon/Ziphius (Beaked whale)',
    'Bp': 'Balaenoptera physalus (Fin whale)',
    'Bm': 'Balaenoptera musculus (Blue whale)',
    'Ba': 'Balaenoptera acutorostrata (Minke whale)',
    'Upcall': 'Right whale upcall vocalization',
    'Call': 'Generic whale call',
    'Gunshot': 'Right whale gunshot sound',
    'Echolocation': 'Odontocete echolocation clicks',
    'Whistle': 'Dolphin/whale whistle',
}

# Detection thresholds
YAMNET_TOP_K = 5                     # Top-K YAMNet classes to report
YAMNET_BIO_THRESHOLD = 0.05         # Min score to flag a YAMNet bio class
MULTISPECIES_THRESHOLD = 0.01       # Min probability for whale species detection
HUMPBACK_THRESHOLD = 0.1            # Min probability for humpback detection


# ─── Model loading (per-process singleton) ───────────────────────────────────

_models = {}

def get_models():
    """Load models once per worker process (cached in global dict)."""
    if _models:
        return _models

    print(f"    [PID {os.getpid()}] Loading models...", flush=True)

    # YAMNet
    _models['yamnet'] = hub.load('https://tfhub.dev/google/yamnet/1')

    # Load YAMNet class names
    class_map_path = _models['yamnet'].class_map_path().numpy().decode()
    import csv
    yamnet_classes = []
    with open(class_map_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            yamnet_classes.append(row['display_name'])
    _models['yamnet_classes'] = yamnet_classes

    # Multispecies Whale
    _models['multispecies'] = hub.load(
        'https://www.kaggle.com/models/google/multispecies-whale/TensorFlow2/default/2'
    )
    meta = _models['multispecies'].metadata()
    _models['multispecies_sr'] = int(meta['input_sample_rate'].numpy())
    _models['multispecies_context'] = int(meta['context_width_samples'].numpy())
    _models['multispecies_classes'] = [n.decode() for n in meta['class_names'].numpy()]

    # Humpback Whale
    _models['humpback'] = hub.load('https://tfhub.dev/google/humpback_whale/1')

    print(f"    [PID {os.getpid()}] Models loaded.", flush=True)
    return _models


# ─── Stage 1: YAMNet ─────────────────────────────────────────────────────────

def run_yamnet(y, sr):
    """Run YAMNet on audio. Returns dict with top classes and bio/marine flags."""
    models = get_models()
    yamnet = models['yamnet']
    class_names = models['yamnet_classes']

    # Resample to 16kHz mono
    if sr != 16000:
        y_16k = librosa.resample(y, orig_sr=sr, target_sr=16000)
    else:
        y_16k = y

    waveform = tf.constant(y_16k.astype(np.float32))
    scores, embeddings, log_mel = yamnet(waveform)

    # Average scores across all time frames
    mean_scores = scores.numpy().mean(axis=0)

    # Top-K classes
    top_indices = np.argsort(mean_scores)[::-1][:YAMNET_TOP_K]
    top_classes = []
    for idx in top_indices:
        top_classes.append({
            'class': class_names[idx],
            'score': round(float(mean_scores[idx]), 4),
        })

    # Check for biological and marine keywords
    bio_detections = []
    marine_detections = []
    noise_detections = []

    for idx, score in enumerate(mean_scores):
        name_lower = class_names[idx].lower()
        if score < YAMNET_BIO_THRESHOLD:
            continue
        for kw in YAMNET_BIO_KEYWORDS:
            if kw in name_lower:
                bio_detections.append({
                    'class': class_names[idx],
                    'score': round(float(score), 4),
                })
                break
        for kw in YAMNET_MARINE_KEYWORDS:
            if kw in name_lower:
                marine_detections.append({
                    'class': class_names[idx],
                    'score': round(float(score), 4),
                })
                break
        for kw in YAMNET_NOISE_KEYWORDS:
            if kw in name_lower:
                noise_detections.append({
                    'class': class_names[idx],
                    'score': round(float(score), 4),
                })
                break

    # Extract embeddings for potential downstream use
    mean_embedding = embeddings.numpy().mean(axis=0)

    return {
        'top_classes': top_classes,
        'bio_detections': sorted(bio_detections, key=lambda x: -x['score']),
        'marine_detections': sorted(marine_detections, key=lambda x: -x['score']),
        'noise_detections': sorted(noise_detections, key=lambda x: -x['score']),
        'has_bio_signal': len(bio_detections) > 0,
        'has_marine_signal': len(marine_detections) > 0,
        'embedding_norm': round(float(np.linalg.norm(mean_embedding)), 4),
    }


# ─── Stage 2: Multispecies Whale Detector ─────────────────────────────────────

def run_multispecies(y, sr):
    """Run Google Multispecies Whale model. Returns species detections."""
    models = get_models()
    model = models['multispecies']
    target_sr = models['multispecies_sr']  # 24000
    context = models['multispecies_context']  # 120000 (5s)
    class_names = models['multispecies_classes']

    # Resample to 24kHz
    if sr != target_sr:
        y_24k = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
    else:
        y_24k = y

    # Reshape to (1, samples, 1)
    audio_3d = y_24k.astype(np.float32).reshape(1, -1, 1)

    # Run inference
    result = model.score(
        waveform=tf.constant(audio_3d),
        context_step_samples=tf.constant(context, dtype=tf.int64)
    )
    scores = result['score'].numpy()  # (1, time_steps, 12)

    # Max score per species across all time windows
    max_scores = scores[0].max(axis=0)  # (12,)
    mean_scores = scores[0].mean(axis=0)  # (12,)

    detections = []
    for i, cls_name in enumerate(class_names):
        if max_scores[i] >= MULTISPECIES_THRESHOLD:
            detections.append({
                'class_code': cls_name,
                'species': WHALE_SPECIES.get(cls_name, cls_name),
                'max_score': round(float(max_scores[i]), 6),
                'mean_score': round(float(mean_scores[i]), 6),
            })

    detections.sort(key=lambda x: -x['max_score'])

    # Time-series scores for top detection (for plotting)
    top_species_idx = int(np.argmax(max_scores))
    time_series = scores[0, :, top_species_idx].tolist()

    return {
        'detections': detections,
        'num_windows': int(scores.shape[1]),
        'top_species': class_names[top_species_idx],
        'top_species_name': WHALE_SPECIES.get(class_names[top_species_idx], ''),
        'top_max_score': round(float(max_scores[top_species_idx]), 6),
        'top_time_series': time_series,
        'any_whale_detected': any(d['max_score'] >= 0.1 for d in detections),
    }


# ─── Stage 3: Humpback Whale Detector ────────────────────────────────────────

def run_humpback(y, sr):
    """Run Google Humpback Whale specialized detector."""
    models = get_models()
    model = models['humpback']

    # Resample to 10kHz
    target_sr = 10000
    if sr != target_sr:
        y_10k = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
    else:
        y_10k = y

    # Reshape to (1, samples, 1)
    audio_3d = y_10k.astype(np.float32).reshape(1, -1, 1)

    # Run inference
    result = model.score(
        waveform=tf.constant(audio_3d),
        context_step_samples=tf.constant(target_sr, dtype=tf.int64)  # 1s steps
    )
    scores = result['scores'].numpy()  # (1, time_steps, 1)
    scores_1d = scores[0, :, 0]

    max_score = float(scores_1d.max())
    mean_score = float(scores_1d.mean())
    # Percentage of windows above threshold
    above_threshold = float(np.sum(scores_1d >= HUMPBACK_THRESHOLD) / len(scores_1d))

    return {
        'max_score': round(max_score, 6),
        'mean_score': round(mean_score, 6),
        'fraction_above_threshold': round(above_threshold, 4),
        'num_windows': int(len(scores_1d)),
        'humpback_detected': max_score >= HUMPBACK_THRESHOLD,
        'time_series': scores_1d.tolist(),
    }


# ─── Cascade Pipeline ────────────────────────────────────────────────────────

def generate_spectrogram(y, sr, fname, yamnet_result, multispecies_result, humpback_result):
    """Generate a combined spectrogram + model scores visualization."""
    fig, axes = plt.subplots(4, 1, figsize=(16, 14),
                             gridspec_kw={'height_ratios': [3, 1, 1, 1]})

    # 1. Mel spectrogram
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, n_fft=2048,
                                        hop_length=512, fmax=sr / 2)
    S_db = librosa.power_to_db(S, ref=np.max)
    img = librosa.display.specshow(S_db, sr=sr, x_axis='time', y_axis='mel',
                                    ax=axes[0], hop_length=512)
    fig.colorbar(img, ax=axes[0], format='%+2.0f dB')

    # Title with summary
    bio = yamnet_result.get('has_bio_signal', False)
    whale = multispecies_result.get('any_whale_detected', False)
    hump = humpback_result.get('humpback_detected', False)
    flags = []
    if bio: flags.append('BIO')
    if whale: flags.append('WHALE')
    if hump: flags.append('HUMPBACK')
    flag_str = ' | '.join(flags) if flags else 'NO DETECTIONS'
    axes[0].set_title(f'{fname} — [{flag_str}]', fontsize=12, fontweight='bold')

    # 2. YAMNet top classes
    top = yamnet_result.get('top_classes', [])
    if top:
        names = [c['class'][:25] for c in top]
        scores = [c['score'] for c in top]
        colors = ['#2ecc71' if any(kw in c['class'].lower() for kw in YAMNET_BIO_KEYWORDS | YAMNET_MARINE_KEYWORDS) else '#95a5a6' for c in top]
        bars = axes[1].barh(range(len(names)), scores, color=colors)
        axes[1].set_yticks(range(len(names)))
        axes[1].set_yticklabels(names, fontsize=8)
        axes[1].set_xlabel('Score')
        axes[1].set_title('Stage 1: YAMNet Top Classes', fontsize=10)
        axes[1].set_xlim(0, 1)
        axes[1].invert_yaxis()

    # 3. Multispecies whale scores over time
    ts = multispecies_result.get('top_time_series', [])
    if ts:
        t_multi = np.linspace(0, len(y) / sr, len(ts))
        axes[2].plot(t_multi, ts, color='#e74c3c', linewidth=1)
        axes[2].axhline(y=MULTISPECIES_THRESHOLD, color='orange', linestyle='--',
                        alpha=0.7, label=f'threshold={MULTISPECIES_THRESHOLD}')
        top_sp = multispecies_result.get('top_species', '?')
        axes[2].set_title(f'Stage 2: Multispecies Whale — top: {top_sp} ({WHALE_SPECIES.get(top_sp, "")})', fontsize=10)
        axes[2].set_ylabel('Score')
        axes[2].legend(fontsize=7)
        axes[2].grid(True, alpha=0.3)

    # 4. Humpback scores over time
    ht = humpback_result.get('time_series', [])
    if ht:
        t_hump = np.linspace(0, len(y) / sr, len(ht))
        axes[3].plot(t_hump, ht, color='#3498db', linewidth=1)
        axes[3].axhline(y=HUMPBACK_THRESHOLD, color='orange', linestyle='--',
                        alpha=0.7, label=f'threshold={HUMPBACK_THRESHOLD}')
        axes[3].set_title('Stage 3: Humpback Whale Detector', fontsize=10)
        axes[3].set_xlabel('Time (s)')
        axes[3].set_ylabel('Score')
        axes[3].legend(fontsize=7)
        axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    spec_path = SPECTROGRAMS_DIR / f'{Path(fname).stem}_cascade.png'
    fig.savefig(str(spec_path), dpi=120)
    plt.close(fig)
    return spec_path.name


def classify_file(wav_path):
    """Run the full cascade pipeline on a single WAV file."""
    fname = wav_path.name
    try:
        # Load audio at native sample rate
        y, sr = librosa.load(str(wav_path), sr=None)
        duration = len(y) / sr
        rms = float(np.sqrt(np.mean(y ** 2)))

        if rms < 1e-7:
            return fname, {
                'filename': fname,
                'duration_s': round(duration, 2),
                'sample_rate': sr,
                'status': 'silent',
                'cascade_summary': 'Silent file — no analysis possible',
                'annotations': ['File is silent (RMS ≈ 0)'],
            }

        # Stage 1: YAMNet
        yamnet_result = run_yamnet(y, sr)

        # Stage 2: Multispecies Whale
        multispecies_result = run_multispecies(y, sr)

        # Stage 3: Humpback Whale
        humpback_result = run_humpback(y, sr)

        # Generate combined spectrogram
        spec_name = generate_spectrogram(
            y, sr, fname, yamnet_result, multispecies_result, humpback_result
        )

        # Build annotations from all stages
        annotations = []

        # YAMNet annotations
        if yamnet_result['has_bio_signal']:
            bio_names = [d['class'] for d in yamnet_result['bio_detections'][:3]]
            annotations.append(f"YAMNet biological signals: {', '.join(bio_names)}")
        if yamnet_result['has_marine_signal']:
            marine_names = [d['class'] for d in yamnet_result['marine_detections'][:3]]
            annotations.append(f"YAMNet marine-related: {', '.join(marine_names)}")

        # Multispecies annotations
        for det in multispecies_result['detections']:
            if det['max_score'] >= 0.1:
                annotations.append(
                    f"Whale detected: {det['species']} "
                    f"(score={det['max_score']:.4f})"
                )
            elif det['max_score'] >= MULTISPECIES_THRESHOLD:
                annotations.append(
                    f"Possible whale: {det['species']} "
                    f"(weak signal, score={det['max_score']:.4f})"
                )

        # Humpback annotations
        if humpback_result['humpback_detected']:
            annotations.append(
                f"Humpback whale detected "
                f"(max={humpback_result['max_score']:.4f}, "
                f"{humpback_result['fraction_above_threshold']:.0%} of windows)"
            )

        if not annotations:
            annotations.append("No marine biological signals detected by any model")

        # Overall cascade summary
        flags = []
        if yamnet_result['has_bio_signal']:
            flags.append('biological_audio')
        if multispecies_result['any_whale_detected']:
            flags.append('whale_species')
        if humpback_result['humpback_detected']:
            flags.append('humpback')
        if yamnet_result['has_marine_signal']:
            flags.append('marine_environment')

        result = {
            'filename': fname,
            'duration_s': round(duration, 2),
            'sample_rate': sr,
            'rms': round(rms, 8),
            'status': 'analyzed',
            'cascade_flags': flags,
            'cascade_summary': '; '.join(flags) if flags else 'no_detections',
            'stage1_yamnet': yamnet_result,
            'stage2_multispecies': multispecies_result,
            'stage3_humpback': humpback_result,
            'annotations': annotations,
            'spectrogram': spec_name,
        }

        # Save individual annotation
        ann_path = ANNOTATIONS_DIR / f'{wav_path.stem}_cascade.json'
        with open(str(ann_path), 'w') as f:
            json.dump(result, f, indent=2)

        return fname, result

    except Exception as e:
        tb = traceback.format_exc()
        return fname, {
            'filename': fname,
            'status': 'error',
            'error': str(e),
            'traceback': tb,
            'annotations': [f'Processing error: {e}'],
        }


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    SPECTROGRAMS_DIR.mkdir(parents=True, exist_ok=True)
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)

    wav_files = sorted(INPUT_DIR.glob('*.wav'))
    wav_files = [f for f in wav_files if f.stat().st_size > 1000]

    print(f'Found {len(wav_files)} WAV files in {INPUT_DIR}/')
    print(f'Output: {OUTPUT_DIR}/')
    print(f'Workers: {MAX_WORKERS}')
    print(f'Pipeline: YAMNet → Multispecies Whale (12 classes) → Humpback Whale')
    print('=' * 70)

    if not wav_files:
        print('No files to process.')
        return

    all_results = {}

    # Use spawn context to avoid TF fork issues
    ctx = mp.get_context('spawn')
    with ctx.Pool(processes=MAX_WORKERS) as pool:
        for i, (fname, result) in enumerate(pool.imap_unordered(classify_file, wav_files)):
            all_results[fname] = result
            status = result.get('status', '?')
            flags = result.get('cascade_flags', [])
            flag_str = ','.join(flags) if flags else '---'
            n_ann = len(result.get('annotations', []))
            print(f'  [{i+1}/{len(wav_files)}] [{flag_str}] {fname}: {status}, {n_ann} annotation(s)')
            sys.stdout.flush()

    # Summary
    whale_files = [r for r in all_results.values() if r.get('stage2_multispecies', {}).get('any_whale_detected')]
    humpback_files = [r for r in all_results.values() if r.get('stage3_humpback', {}).get('humpback_detected')]
    bio_files = [r for r in all_results.values() if r.get('stage1_yamnet', {}).get('has_bio_signal')]
    error_files = [r for r in all_results.values() if r.get('status') == 'error']

    print(f'\n{"=" * 70}')
    print('CASCADE CLASSIFIER SUMMARY')
    print(f'{"=" * 70}')
    print(f'  Total processed: {len(all_results)}')
    print(f'  YAMNet biological signals: {len(bio_files)}')
    print(f'  Whale species detected: {len(whale_files)}')
    print(f'  Humpback detected: {len(humpback_files)}')
    print(f'  Errors: {len(error_files)}')

    if whale_files:
        print(f'\n  FILES WITH WHALE DETECTIONS:')
        for r in sorted(whale_files, key=lambda x: x['filename']):
            print(f'    + {r["filename"]}')
            for det in r.get('stage2_multispecies', {}).get('detections', []):
                if det['max_score'] >= MULTISPECIES_THRESHOLD:
                    print(f'        {det["class_code"]}: {det["species"]} (score={det["max_score"]:.4f})')

    if humpback_files:
        print(f'\n  FILES WITH HUMPBACK DETECTIONS:')
        for r in sorted(humpback_files, key=lambda x: x['filename']):
            score = r.get('stage3_humpback', {}).get('max_score', 0)
            print(f'    + {r["filename"]} (max_score={score:.4f})')

    # Remove time_series from consolidated output (too large)
    for fname, result in all_results.items():
        if 'stage2_multispecies' in result:
            result['stage2_multispecies'].pop('top_time_series', None)
        if 'stage3_humpback' in result:
            result['stage3_humpback'].pop('time_series', None)

    summary = {
        'pipeline': 'Cascade Classifier v1.0',
        'stages': [
            'Stage 1: YAMNet (general audio, 521 classes)',
            'Stage 2: Google Multispecies Whale (12 whale/dolphin classes)',
            'Stage 3: Google Humpback Whale (specialized binary detector)',
        ],
        'input_dir': str(INPUT_DIR),
        'total_files': len(all_results),
        'yamnet_bio_signals': len(bio_files),
        'whale_species_detected': len(whale_files),
        'humpback_detected': len(humpback_files),
        'errors': len(error_files),
        'files': {k: v for k, v in sorted(all_results.items())},
    }
    with open(str(RESULTS_FILE), 'w') as f:
        json.dump(summary, f, indent=2)

    print(f'\n  Results: {RESULTS_FILE}')
    print(f'  Spectrograms: {SPECTROGRAMS_DIR}/')
    print(f'  Annotations: {ANNOTATIONS_DIR}/')


if __name__ == '__main__':
    main()