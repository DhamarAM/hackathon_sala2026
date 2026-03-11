# Cascade Classifier Pipeline for Marine Audio Analysis

## Overview

This document covers **Stages 1–3** of the full pipeline — the cascade classification block. It runs after Stage 0 (AudioClipper) and feeds its results into Stages 3–5 (Soundscape, Clustering, Ranking).

The cascade processes each WAV clip through three pre-trained deep learning models in sequence to detect and classify marine biological sounds. It is designed for **unlabeled field recordings** where no ground-truth annotations exist, providing an initial probabilistic assessment of the biological value of each clip.

## Full Pipeline Context

```
Source WAVs
    │
    ▼
Stage 0 — AudioClipper          (backend/pipeline/stage1_clip.py)
    Silence detection → active-segment clips
    │
    ▼
Stages 1–3 — Cascade            (backend/pipeline/stage2_cascade.py)  ← THIS DOC
    YAMNet + Multispecies Whale + Humpback
    │
    ▼
Stage 5 — Soundscape            (backend/pipeline/stage3_soundscape.py)
    Acoustic indices (NDSI, band power, entropy)
    │
    ▼
Stage 6 — Clustering            (backend/pipeline/stage4_cluster.py)
    BirdNET/MFCC embeddings → UMAP → HDBSCAN
    │
    ▼
Stage 4 — Biological Ranking    (backend/pipeline/stage5_rank.py)
    9-dimensional weighted score → ranked.json / ranked.csv
```

## Cascade Architecture (Stages 1–3)

```
┌─────────────────────────────────────────────────────────────┐
│                     Input: WAV clip                         │
│         (active segment from Stage 0, any sample rate)      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: YAMNet (Google, TF Hub)                           │
│  ──────────────────────────────────────                      │
│  • General-purpose audio classifier                         │
│  • 521 AudioSet classes                                     │
│  • Input: 16 kHz mono (resampled internally)                │
│  • Output: class scores + 1024-dim embeddings               │
│  • Purpose: Detect biological vs mechanical vs silence       │
│  • Flags: biological_audio, marine_environment              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: Multispecies Whale Detector (Google/Kaggle)        │
│  ────────────────────────────────────────────                │
│  • Specialized whale/dolphin classifier                      │
│  • 12 classes (7 species + 5 vocalization types)             │
│  • Input: 24 kHz mono, 5-second windows (120k samples)      │
│  • Output: per-window probability for each class             │
│  • Purpose: Identify specific whale/dolphin species          │
│  • Flags: whale_species                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3: Humpback Whale Detector (Google, TF Hub)           │
│  ─────────────────────────────────────────                   │
│  • Specialized binary humpback vocalization detector         │
│  • Input: 10 kHz mono, 1-second windows                     │
│  • Output: per-window humpback presence probability          │
│  • Purpose: High-sensitivity humpback detection              │
│  • Flags: humpback                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT                                                      │
│  • 4-panel spectrogram PNG per clip                         │
│  • Per-clip JSON annotation                                  │
│  • Consolidated results.json                                 │
└─────────────────────────────────────────────────────────────┘
```

## Models

### Stage 1: YAMNet

- **Source**: [TensorFlow Hub](https://tfhub.dev/google/yamnet/1)
- **Architecture**: MobileNet v1 backbone trained on AudioSet
- **Training data**: AudioSet (2M+ YouTube clips, 521 sound categories)
- **Input**: Float32 waveform at 16 kHz
- **Output**:
  - Class scores: `(N_frames, 521)` — probability per AudioSet class per 0.96s frame
  - Embeddings: `(N_frames, 1024)` — learned audio representations
- **Role in pipeline**: Broad triage — identifies whether audio contains biological sounds (animal vocalizations), marine environmental sounds (water, waves), or only noise/silence.

### Stage 2: Google Multispecies Whale Detector

- **Source**: [Kaggle Models](https://www.kaggle.com/models/google/multispecies-whale/TensorFlow2/default/2)
- **Architecture**: CNN-based classifier from Google's bioacoustics team
- **Training data**: Annotated whale/dolphin recordings from NOAA and research partners
- **Input**: Float32 waveform at 24 kHz, shape `(batch, samples, 1)`, 5-second context windows (120,000 samples)
- **Output**: `(batch, time_steps, 12)` — per-window probability for 12 classes
- **Classes**:

| Code | Species / Type | Description |
|------|---------------|-------------|
| `Oo` | *Orcinus orca* | Killer whale / Orca |
| `Mn` | *Megaptera novaeangliae* | Humpback whale |
| `Eg` | *Eubalaena glacialis* | North Atlantic right whale |
| `Be` | *Mesoplodon/Ziphius* | Beaked whale |
| `Bp` | *Balaenoptera physalus* | Fin whale |
| `Bm` | *Balaenoptera musculus* | Blue whale |
| `Ba` | *Balaenoptera acutorostrata* | Minke whale |
| `Upcall` | — | Right whale upcall vocalization |
| `Call` | — | Generic whale call |
| `Gunshot` | — | Right whale gunshot sound |
| `Echolocation` | — | Odontocete echolocation clicks |
| `Whistle` | — | Dolphin/whale whistle |

### Stage 3: Google Humpback Whale Detector

- **Source**: [TensorFlow Hub](https://tfhub.dev/google/humpback_whale/1)
- **Architecture**: ResNet-based binary classifier
- **Training data**: NOAA/Google annotated humpback whale recordings
- **Input**: Float32 waveform at 10 kHz, shape `(batch, samples, 1)`, 1-second step windows
- **Output**: `(batch, time_steps, 1)` — per-window humpback presence probability
- **Role in pipeline**: High-sensitivity humpback detector that complements Stage 2. Uses a different input sample rate (10 kHz vs 24 kHz) and finer temporal resolution (1s vs 5s windows), making it more sensitive to short humpback vocalizations.

## Detection Thresholds

All thresholds are defined in `backend/config.py`:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `YAMNET_BIO_THRESHOLD` | 0.05 | Min YAMNet score to flag a biological class |
| `MULTISPECIES_THRESHOLD` | 0.01 | Min score to list a species in `detections[]` |
| `MULTISPECIES_DETECTION_THR` | 0.10 | Min score to activate the `whale_species` flag |
| `HUMPBACK_THRESHOLD` | 0.30 | Min per-window score to activate the `humpback` flag |

Thresholds are set to favor **recall over precision** — for unlabeled field data it's better to flag potential detections for human review than to miss them.

## Output Structure

```
outputs/
└── analysis/
    ├── results.json              # Consolidated results for all clips
    ├── spectrograms/
    │   └── <clip>_cascade.png   # 4-panel visualization per clip
    └── annotations/
        └── <clip>_cascade.json  # Full per-clip result (includes time_series arrays)
```

### Per-clip annotation JSON

```json
{
  "filename": "6478.230724141251_seg004.wav",
  "duration_s": 30.0,
  "sample_rate": 96000,
  "status": "analyzed",
  "cascade_flags": ["biological_audio", "whale_species", "humpback"],
  "cascade_summary": "biological_audio; whale_species; humpback",
  "stage1_yamnet": {
    "top_classes": [...],
    "bio_detections": [...],
    "marine_detections": [...],
    "has_bio_signal": true,
    "has_marine_signal": false,
    "embedding_norm": 12.3456
  },
  "stage2_multispecies": {
    "detections": [
      {
        "class_code": "Mn",
        "species": "Megaptera novaeangliae (Humpback whale)",
        "max_score": 0.8523,
        "mean_score": 0.1204
      }
    ],
    "top_species": "Mn",
    "top_max_score": 0.8523,
    "any_whale_detected": true
  },
  "stage3_humpback": {
    "max_score": 0.9102,
    "mean_score": 0.0834,
    "fraction_above_threshold": 0.12,
    "humpback_detected": true
  },
  "annotations": [
    "Whale: Megaptera novaeangliae (Humpback whale) (score=0.8523)",
    "Humpback detected (max=0.9102, 12% of windows)",
    "YAMNet bio: Animal, Insect, Wild animals"
  ]
}
```

### Spectrogram visualization

Each PNG contains 4 panels:
1. **Mel spectrogram** — full frequency range with detection flags in title
2. **YAMNet top classes** — horizontal bar chart of top-5 detected sound categories
3. **Multispecies whale scores** — time series of top species detection probability
4. **Humpback scores** — time series of humpback detection probability

## Usage

```bash
# Full pipeline (includes clipping, cascade, soundscape, clustering, ranking)
python -m backend.run --source <wav_folder>

# Cascade only (clips must exist already)
python -m backend.run --source <wav_folder> --skip-clip --skip-soundscape --no-cluster
```

See `backend/README.md` for the full list of flags and checkpoint-resume options.

## Interpretation Guide

### Cascade flags

- **`biological_audio`**: YAMNet detected animal/biological sound classes above threshold. Broad indicator — could include birds, insects, or snapping shrimp patterns.
- **`marine_environment`**: YAMNet detected water/ocean/wave-related sounds. Confirms the recording is capturing the underwater environment.
- **`whale_species`**: The multispecies model detected at least one whale/dolphin class with score ≥ 0.10. Check `stage2_multispecies.detections` for species breakdown.
- **`humpback`**: The specialized humpback detector found vocalization patterns with score ≥ 0.30. Check `stage3_humpback.fraction_above_threshold` for temporal extent.

### Confidence levels

- **Strong detection** (score > 0.5): High confidence, likely a true positive
- **Moderate detection** (0.1 – 0.5): Probable detection, worth manual review
- **Weak detection** (0.01 – 0.1): Possible but uncertain, may be noise or distant vocalization
- **No detection** (< 0.01): No evidence from this model

### Important caveats

1. **No model is perfect**: These models were trained on specific datasets that may not perfectly represent Galápagos marine soundscapes. False positives and false negatives are expected.
2. **Geographic bias**: The multispecies model was trained primarily on North Atlantic and North Pacific recordings. Some species (like North Atlantic right whale) are not found in Galápagos waters — detections of these species likely indicate similar acoustic patterns from local species.
3. **Sample rate limitations**: The source recordings are 96 kHz (SoundTrap ST300), but models require resampling to 10–24 kHz. This discards ultrasonic information that may contain echolocation clicks.
4. **Complementary models**: Each model captures different aspects — YAMNet is broad but shallow, multispecies is cetacean-specific, and humpback is highly specialized. Use all three together for the most complete picture.
5. **YAMNet domain mismatch**: Trained on terrestrial audio (YouTube). When it classifies underwater audio as "Insect" or "Cricket", it is likely responding to rhythmic patterns from snapping shrimp or fish choruses.

## Dependencies

- `tensorflow >= 2.17`
- `tensorflow-hub >= 0.16`
- `setuptools < 81` (required by `tensorflow-hub` import)
- `librosa >= 0.10`
- `numpy`
- `matplotlib`
