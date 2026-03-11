# Backend — Dragon Ocean Analyzer

Python pipeline for marine bioacoustic classification. Processes SoundTrap hydrophone recordings through 6 stages and produces a ranked report of biological importance.

---

## Requirements

```bash
pip install -r requirements.txt   # from repo root
```

**Key dependencies:** `tensorflow`, `tensorflow-hub`, `librosa`, `scikit-maad`, `opensoundscape`, `umap-learn`, `hdbscan`

**Stage 6 (clustering)** requires GPU for BirdNET embeddings. Without GPU it falls back to MFCC features automatically. Use `--no-cluster` to skip it entirely.

---

## How to Run

Run from the **repo root** (not from inside `backend/`):

```bash
# Full pipeline — default source and output
python -m backend.run

# Custom source directory
python -m backend.run --source hackathon_data/marine-acoustic

# Custom output directory
python -m backend.run --source hackathon_data/marine-acoustic --output outputs
```

### Skip flags (resume from a checkpoint)

Each stage writes its output to disk. If a run was interrupted, skip completed stages:

```bash
# Stage 0 already ran — reuse clips
python -m backend.run --skip-clip

# Stages 0–3 already ran — reuse cascade results
python -m backend.run --skip-clip --skip-cascade

# Run only Stage 4 (re-rank existing results)
python -m backend.run --skip-clip --skip-cascade --skip-soundscape --no-cluster

# Without GPU — skip Stage 6 entirely
python -m backend.run --no-cluster
```

| Flag | Skips | Reuses from |
|------|-------|-------------|
| `--skip-clip` | Stage 0 | `outputs/clips/*.wav` |
| `--skip-cascade` | Stage 1-3 | `outputs/analysis/results.json` |
| `--skip-soundscape` | Stage 5 | `outputs/soundscape/soundscape.json` |
| `--skip-cluster` | Stage 6 | `outputs/clusters/clusters.json` |
| `--no-cluster` | Stage 6 | _(does not run, uses placeholder scores)_ |

---

## Pipeline Stages

```
Source WAVs
    │
    ▼
Stage 0 — AudioClipper
    Silence detection (RMS threshold), active-segment extraction,
    padding, merging. Produces short WAV clips.
    │
    ▼
Stage 1 — YAMNet
    521-class AudioSet classifier (16 kHz). Flags biological/marine/noise signals.
    │
Stage 2 — Multispecies Whale
    12-class cetacean detector: 7 species + 5 vocalization types (24 kHz, 5s windows).
    │
Stage 3 — Humpback Whale
    Binary per-window detector (10 kHz, 1s windows).
    │
    ▼
Stage 5 — Soundscape Characterization
    NDSI (Normalized Difference Soundscape Index), band power, spectral
    and temporal entropy. Penalizes anthropogenic noise. CPU-only.
    │
    ▼
Stage 6 — Embedding Clustering   [optional, GPU recommended]
    BirdNET embeddings (1024-dim) → UMAP (2D) → HDBSCAN clusters.
    Fallback: MFCC+Chroma (148-dim) on CPU.
    │
    ▼
Stage 4 — Biological Importance Ranking
    9-dimensional weighted score (0–100), 5 tiers.
    Writes ranked.json and ranked.csv.
```

---

## Output Structure

All outputs are written to `outputs/` (gitignored):

```
outputs/
├── clips/                          ← Stage 0
│   └── <source>_seg001.wav         Active segments extracted from source WAVs
│
├── analysis/                       ← Stage 1-3
│   ├── results.json                Consolidated cascade results for all clips
│   ├── spectrograms/
│   │   └── <clip>_cascade.png      4-panel spectrogram (mel + YAMNet + multispecies + humpback)
│   └── annotations/
│       └── <clip>_cascade.json     Full per-clip result (includes time_series arrays)
│
├── soundscape/                     ← Stage 5
│   ├── soundscape.json             NDSI, entropy, band power per clip
│   └── ndsi_timeseries.png         Bar chart of NDSI values across clips
│
├── clusters/                       ← Stage 6
│   ├── clusters.json               Cluster assignments + UMAP coordinates per clip
│   ├── embeddings.npy              Raw embedding matrix (N × 1024 or N × 148)
│   └── umap_clusters.png           2D scatter plot colored by cluster
│
└── ranking/                        ← Stage 4
    ├── ranked.json                 Full ranking with scores, tiers, and 9 components
    └── ranked.csv                  Flat CSV version for quick inspection
```

### What to expect in `ranked.json`

```json
{
  "total_ranked": 57,
  "tier_distribution": {"HIGH": 1, "MODERATE": 2, "LOW": 28, "MINIMAL": 26},
  "rankings": [
    {
      "rank": 1,
      "filename": "6478.230724141251_seg004.wav",
      "score": 45.76,
      "tier": "HIGH",
      "components": {
        "whale_sustained": 0.5868,
        "bio_richness": 0.0,
        "acoustic_diversity": 0.5714,
        "humpback_coverage": 1.0,
        "cross_model": 0.6,
        "ndsi_score": 0.0206,
        "cluster_signal": 0.3,
        "humpback_peak": 0.9643,
        "yamnet_quality": 0.0
      },
      "cascade_flags": ["whale_species", "humpback"],
      "top_species": "Generic whale call",
      "annotations": ["Whale: Generic whale call (score=0.6286)", "Humpback detected (...)"]
    }
  ]
}
```

### Ranking tiers

| Tier | Score | Interpretation |
|------|-------|----------------|
| CRITICAL | ≥ 65 | High-confidence multi-model detection — review first |
| HIGH | ≥ 45 | Strong single-model signal — likely biological |
| MODERATE | ≥ 25 | Moderate signal — worth reviewing |
| LOW | ≥ 10 | Weak signal — review if time permits |
| MINIMAL | < 10 | No significant biological signal detected |

### Ranking dimensions (9 total, sum = 100%)

| Dimension | Weight | Source |
|-----------|--------|--------|
| `whale_sustained` | 18% | Multispecies peak + mean scores |
| `bio_richness` | 15% | YAMNet bio detection count and scores |
| `acoustic_diversity` | 15% | Number of distinct species/vocalization types |
| `humpback_coverage` | 12% | Fraction of 1s windows above humpback threshold |
| `cross_model` | 12% | Flags agreement across YAMNet + multispecies + humpback |
| `ndsi_score` | 10% | NDSI index — penalizes anthropogenic noise dominance |
| `cluster_signal` | 8% | Bonus for biological cluster membership (Stage 6) |
| `humpback_peak` | 5% | Maximum humpback score across windows |
| `yamnet_quality` | 5% | Top-1 YAMNet class quality (penalizes silence/noise) |

---

## Key Configuration

All thresholds and paths are in `backend/config.py`:

```python
HUMPBACK_THRESHOLD         = 0.3    # per-window detection (raised from 0.1 to reduce FP)
MULTISPECIES_DETECTION_THR = 0.10   # activates whale_species flag
MULTISPECIES_THRESHOLD     = 0.01   # minimum score to list in detections[]
SILENCE_THRESHOLD          = 50.0   # RMS units for Stage 0 activity detection
```

---

## Notes

- **First run downloads ~500 MB of TF Hub models** (YAMNet, Multispecies, Humpback). Cached after first use.
- **YAMNet does not reliably detect cetaceans** in underwater recordings — it was trained on terrestrial AudioSet. Its role is general environment characterization, not cetacean detection.
- **Biological content is unverified** — all detections are model predictions, not expert-confirmed observations.
- **Cache invalidation:** if you change `HUMPBACK_THRESHOLD` or other detection thresholds, delete `outputs/analysis/` before re-running to avoid stale cached results.
