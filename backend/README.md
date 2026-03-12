# Backend — Dragon Ocean Analyzer

Python pipeline for marine bioacoustic classification. Processes SoundTrap hydrophone recordings through 6 stages and produces a ranked report of biological importance.

---

## Requirements

```bash
pip install -r requirements.txt   # from repo root
```

**Key dependencies:** `tensorflow`, `tensorflow-hub`, `librosa`, `scikit-maad`, `opensoundscape`, `umap-learn`, `hdbscan`

**Stage 6 (clustering)** uses NatureLM embeddings (reuses the model loaded in the cascade). Use `--no-cluster` to skip it entirely.

---

## How to Run

Run from the **repo root** (not from inside `backend/`):

```bash
python -m backend.run --source hackathon_data/marine-acoustic/5783
```

Other examples:

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

| Stage | Script | What it does |
|-------|--------|--------------|
| Stage 0 | `backend/pipeline/stage1_clip.py` | AudioClipper — silence detection (RMS), active-segment extraction, padding and merging. Produces short WAV clips. |
| Cascade | `backend/pipeline/stage2_cascade.py` | 6 models in parallel — Perch 2.0 (32 kHz) + Multispecies Whale (12 classes, 24 kHz) + Humpback (binary, 10 kHz) + NatureLM-BEATs (16 kHz) + BioLingual (zero-shot) + Dasheng (complexity). |
| Soundscape | `backend/pipeline/stage3_soundscape.py` | NDSI, band power, boat_score. CPU-only, no GPU needed. |
| Clustering | `backend/pipeline/stage4_cluster.py` | NatureLM embeddings (768-dim) → UMAP (2D) → HDBSCAN. |
| Ranking | `backend/pipeline/stage5_rank.py` | 6-model equal-weight score (0–100), 5 tiers. Writes `ranked.json` and `ranked.csv`. |

> **Note on numbering:** Stage 4 (Ranking) runs last because it depends on Stages 5 and 6 as inputs. The script filenames (`stage1_` through `stage5_`) reflect execution order, not the conceptual stage numbers.

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
│   │   └── <clip>_cascade.png      4-panel spectrogram (mel + Perch 2.0 + multispecies + humpback)
│   └── annotations/
│       └── <clip>_cascade.json     Full per-clip result (includes time_series arrays)
│
├── soundscape/                     ← Stage 5
│   ├── soundscape.json             NDSI, entropy, band power per clip
│   └── ndsi_timeseries.png         Bar chart of NDSI values across clips
│
├── clusters/                       ← Stage 6
│   ├── clusters.json               Cluster assignments + UMAP coordinates per clip
│   ├── embeddings.npy              Raw NatureLM embedding matrix (N × 768)
│   └── umap_clusters.png           2D scatter plot colored by cluster
│
└── ranking/                        ← Stage 4
    ├── ranked.json                 Full ranking with scores, tiers, and 6 model components
    └── ranked.csv                  Flat CSV version for quick inspection
```

### What to expect in `ranked.json`

```json
{
  "total_ranked": 57,
  "tier_distribution": {"HIGH": 7, "MODERATE": 3, "LOW": 28, "MINIMAL": 19},
  "rankings": [
    {
      "rank": 1,
      "filename": "190808_4244_seg003.wav",
      "score": 63.37,
      "tier": "HIGH",
      "components": {
        "perch": 0.0332,
        "multispecies": 0.6667,
        "humpback": 0.6111,
        "naturelm": 0.5724,
        "biolingual": 0.9842,
        "dasheng": 0.9349
      },
      "cascade_flags": ["biological_audio", "whale_species", "humpback", "naturelm_bio", "biolingual_bio", "dasheng_complex"],
      "top_species": "Orcinus orca (Orca)",
      "boat_score": 0.12,
      "ndsi": 0.45,
      "cluster_id": 2
    }
  ]
}
```

### Ranking tiers

| Tier | Score | Interpretation |
|------|-------|----------------|
| CRITICAL | ≥ 70 | Strong multi-model agreement — review first |
| HIGH | ≥ 50 | Clear biological signals — detailed review |
| MODERATE | ≥ 30 | Moderate signals — review when possible |
| LOW | ≥ 15 | Weak signal — review if time permits |
| MINIMAL | < 15 | Little biological evidence |

### Ranking methodology (6-model equal-weight)

`score = mean(bio_signal_score per model) × 100`

| Model | Key | Weight |
|-------|-----|--------|
| Perch 2.0 | `perch` | 1/6 |
| Multispecies Whale | `multispecies` | 1/6 |
| Humpback Detector | `humpback` | 1/6 |
| NatureLM-BEATs | `naturelm` | 1/6 |
| BioLingual | `biolingual` | 1/6 |
| Dasheng | `dasheng` | 1/6 |

`boat_score` and `cluster_id` are stored as metadata — they do not affect the score.

---

## Key Configuration

All thresholds and paths are in `backend/config.py`:

```python
HUMPBACK_THRESHOLD         = 0.3    # per-window detection (raised from 0.1 to reduce FP)
MULTISPECIES_DETECTION_THR = 0.01   # activates whale_species flag (lowered from 0.10 for hydrophone calibration)
MULTISPECIES_THRESHOLD     = 0.005  # minimum score to list in detections[]
SILENCE_THRESHOLD          = 50.0   # RMS units for Stage 0 activity detection
```

---

## Notes

- **First run downloads models** (Perch 2.0, Multispecies, Humpback from TF Hub/Kaggle; NatureLM, BioLingual, Dasheng from HuggingFace). Cached after first use.
- **Perch 2.0 domain note**: Trained on terrestrial/aerial bioacoustics. In hydrophone recordings with TF Hub fallback (no class names), bio_signal falls back to `std(embeddings)/2`. Typical range: 0.02–0.08.
- **Biological content is unverified** — all detections are model predictions, not expert-confirmed observations.
- **Cache invalidation:** if you change `HUMPBACK_THRESHOLD` or other detection thresholds, delete `outputs/analysis/` before re-running to avoid stale cached results.
