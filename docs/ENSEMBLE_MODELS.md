# Ensemble Classifier Models — Marine Audio Analysis

## Overview

This document covers the **6-model ensemble** used to classify marine acoustic recordings. All models run in parallel on each WAV clip — this is not a sequential cascade, but an independent ensemble where each model contributes equally to the final biological importance score.

The ensemble runs after Stage 0 (AudioClipper) and feeds its results into the Soundscape, Clustering, and Ranking stages.

---

## Model Summary

| # | Model | Author | Year | Family | Input SR | Role |
|---|-------|--------|------|--------|----------|------|
| 1 | **Perch 2.0** | Google Research | 2025 | CNN (EfficientNet) | 32 kHz | General bioacoustic triage, ~14k biodiversity classes |
| 2 | **Multispecies Whale Detector** | Google / NOAA | 2023 | CNN | 24 kHz | 12 cetacean classes (7 species + 5 vocalizations) |
| 3 | **Humpback Whale Detector** | Google / NOAA | 2021 | CNN (ResNet) | 10 kHz | Binary humpback presence, 1s resolution |
| 4 | **NatureLM-BEATs** | Earth Species Project | 2025 | Transformer (BEATs) | 16 kHz | Bioacoustic embeddings, structural complexity |
| 5 | **BioLingual** | David Robinson | 2024 | Transformer (CLAP) | any | Zero-shot semantic classification, detects boat noise |
| 6 | **Dasheng** | Shanghai AI Lab | 2024 | Transformer (self-supervised) | any | Audio complexity via temporal variance + embedding diversity |

**CNN models (1–3):** domain-specific, trained on labeled cetacean/bird data. High precision for known species, lower recall for out-of-domain recordings.

**Transformer models (4–6):** domain-agnostic, self-supervised or zero-shot. More robust to out-of-domain audio but less species-specific.

---

## Full Pipeline Context

```
Source WAVs
    │
    ▼
Stage 0 — AudioClipper          (backend/pipeline/stage1_clip.py)
    Silence detection → active-segment clips
    │
    ▼
Stages 1–6 — Cascade            (backend/pipeline/stage2_cascade.py)  ← THIS DOC
    Perch 2.0 + Multispecies Whale + Humpback + NatureLM + BioLingual + Dasheng
    │
    ▼
Stage 5 — Soundscape            (backend/pipeline/stage3_soundscape.py)
    Acoustic indices (NDSI, band power, entropy)
    │
    ▼
Stage 6 — Clustering            (backend/pipeline/stage4_cluster.py)
    NatureLM embeddings → UMAP → HDBSCAN
    │
    ▼
Stage 4 — Biological Ranking    (backend/pipeline/stage5_rank.py)
    6-model equal-weight score → ranked.json / ranked.csv
```

## Cascade Architecture (Stages 1–6)

```
┌─────────────────────────────────────────────────────────────┐
│                     Input: WAV clip                         │
│         (active segment from Stage 0, any sample rate)      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: Perch 2.0 (Google, TF Hub)                        │
│  ─────────────────────────────────────                       │
│  • General-purpose bioacoustic classifier (~14k classes)    │
│  • Input: 32 kHz mono                                       │
│  • Output: class scores + embeddings                        │
│  • Purpose: Broad biological vs mechanical triage           │
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
│  STAGE 4: NatureLM-BEATs (bioacoustic transformer)          │
│  ──────────────────────────────────────────────             │
│  • BEATs self-supervised transformer fine-tuned on bio audio │
│  • Input: 16 kHz mono, max 60s                              │
│  • Output: 768-dim embeddings → entropy + magnitude scores  │
│  • Purpose: Structural complexity of biological signals      │
│  • Flags: naturelm_bio                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 5: BioLingual (zero-shot bioacoustic classifier)      │
│  ──────────────────────────────────────────────             │
│  • CLAP-based zero-shot classification                       │
│  • 10 labels incl. boat engine noise, ocean ambient          │
│  • Input: any sample rate                                    │
│  • Output: softmax over 10 labels                            │
│  • Purpose: Semantic classification + boat noise detection   │
│  • Flags: biolingual_bio                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 6: Dasheng (self-supervised structural complexity)    │
│  ──────────────────────────────────────────────             │
│  • Self-supervised audio encoder                             │
│  • Measures temporal variance + embedding diversity          │
│  • Input: any sample rate                                    │
│  • Purpose: Detect structurally complex (non-stationary) bio │
│  • Flags: dasheng_complex                                    │
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

### Stage 1: Perch 2.0

- **Source**: TensorFlow Hub (Google Research)
- **Architecture**: EfficientNet backbone trained on ~14k biodiversity classes
- **Input**: Float32 waveform at 32 kHz
- **Output**: Class scores + embeddings
- **Role in pipeline**: Broad triage — identifies whether audio contains biological sounds (animal vocalizations), marine environmental sounds, or only noise/silence. When class names are unavailable (TF Hub fallback), uses `std(embeddings)/2` as a bio signal proxy.

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
| `PERCH_BIO_THRESHOLD` | 0.05 | Min Perch score to flag a biological class |
| `PERCH_FALLBACK_BIO_THRESHOLD` | 0.02 | Fallback threshold when class names unavailable (std of embeddings) |
| `MULTISPECIES_THRESHOLD` | 0.005 | Min score to list a species in `detections[]` |
| `MULTISPECIES_DETECTION_THR` | 0.01 | Min score to activate the `whale_species` flag (lowered from 0.10 for hydrophone calibration) |
| `HUMPBACK_THRESHOLD` | 0.30 | Min per-window score to activate the `humpback` flag |
| `DASHENG_BIO_THRESHOLD` | 0.30 | Min bio_signal_score to activate the `dasheng_complex` flag |

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
  "stage1_perch": {
    "top_classes": [],
    "bio_detections": [],
    "marine_detections": [],
    "has_bio_signal": true,
    "has_marine_signal": false,
    "bio_signal_score": 0.0332
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

- **`biological_audio`**: Perch 2.0 detected animal/biological sound classes above threshold. Broad indicator — could include birds, insects, or snapping shrimp patterns.
- **`marine_environment`**: Perch 2.0 detected water/ocean/wave-related sounds. Confirms the recording is capturing the underwater environment.
- **`whale_species`**: The multispecies model detected at least one whale/dolphin class with score ≥ 0.01. Check `stage2_multispecies.detections` for species breakdown.
- **`humpback`**: The specialized humpback detector found vocalization patterns with score ≥ 0.30. Check `stage3_humpback.fraction_above_threshold` for temporal extent.
- **`naturelm_bio`**: NatureLM-BEATs detected structurally complex biological audio (high embedding entropy or magnitude).
- **`biolingual_bio`**: BioLingual zero-shot classifier assigned majority probability to a biological label.
- **`dasheng_complex`**: Dasheng detected non-stationary structural complexity consistent with biological audio.

### Confidence levels

- **Strong detection** (score > 0.5): High confidence, likely a true positive
- **Moderate detection** (0.1 – 0.5): Probable detection, worth manual review
- **Weak detection** (0.01 – 0.1): Possible but uncertain, may be noise or distant vocalization
- **No detection** (< 0.01): No evidence from this model

### Important caveats

1. **No model is perfect**: These models were trained on specific datasets that may not perfectly represent Galápagos marine soundscapes. False positives and false negatives are expected.
2. **Geographic bias**: The multispecies model was trained primarily on North Atlantic and North Pacific recordings. Some species (like North Atlantic right whale) are not found in Galápagos waters — detections of these species likely indicate similar acoustic patterns from local species.
3. **Sample rate limitations**: The source recordings are 96 kHz (SoundTrap ST300), but models require resampling to 10–24 kHz. This discards ultrasonic information that may contain echolocation clicks.
4. **Complementary models**: Each model captures different aspects — Perch 2.0 is broad, multispecies is cetacean-specific, humpback is highly specialized, NatureLM captures structural complexity, BioLingual provides semantic context, and Dasheng measures non-stationarity. All six contribute equally to the final score.
5. **Perch 2.0 domain note**: When class names are unavailable from TF Hub, bio_signal falls back to `std(embeddings)/2`. Typical range for hydrophone recordings: 0.02–0.08.

## Dependencies

- `tensorflow >= 2.17`
- `tensorflow-hub >= 0.16`
- `setuptools < 81` (required by `tensorflow-hub` import)
- `librosa >= 0.10`
- `numpy`
- `matplotlib`
