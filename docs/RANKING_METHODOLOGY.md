# Biological Importance Ranking — Methodology (v3)

## Objective

Rank all processed audio clips by **biological importance**, allowing researchers to focus their manual review on the recordings with the richest and most relevant content.

## Problem

The pipeline generates multiple heterogeneous metrics per clip:
- **Stage 1–3 (Cascade)**: YAMNet class scores, multispecies per-window probabilities, humpback per-window probabilities
- **Stage 3 (Soundscape)**: NDSI, band power distribution, spectral/temporal entropy
- **Stage 4 (Clustering)**: cluster identity, cluster size, dominant spectral band

How can we combine all these into a **single, sortable score** that reflects the true biological value of each recording?

## Score Formula

```
Score (0–100) = Σ (component_i × weight_i) × 100
```

9 components, each normalized to [0, 1]. Weights defined in `backend/config.py` under `RANK_WEIGHTS`.

---

## The 9 Dimensions

### Dimension 1 — Sustained Cetacean Presence (18%)

```
whale_sustained = 0.5 × top_max_score + 0.5 × min(Σ mean_scores × 5, 1.0)
```

Combines the **peak** signal (best 5-second window) with the **sustained** presence (average across all windows). A clip with a moderate but persistent signal scores higher than one with a single transient spike.

The ×5 factor compensates for mean scores being 10–100× smaller than max scores (vocalizations are intermittent, not continuous).

---

### Dimension 2 — YAMNet Biological Richness (15%)

```
bio_richness = 0.5 × min(n_bio_detections / 8, 1.0) + 0.5 × min(Σ bio_scores, 1.0)
```

Combines:
- **Count** of biological class detections (normalized to 8): more types = richer signal
- **Intensity** of those detections (sum of scores): stronger = clearer

When YAMNet's top-1 class is "Animal" or "Wild animals" in underwater audio, it correlates strongly with visible biological structure in the spectrogram. When top-1 is "Speech" or "Silence", biological detections tend to be isolated events in otherwise noisy audio.

---

### Dimension 3 — Acoustic Diversity (15%)

```
diversity = min((n_species + n_vocalization_types) / 7, 1.0)
```

Where:
- `n_species`: species with multispecies score ≥ 0.01 (Oo, Mn, Eg, Be, Bp, Bm, Ba)
- `n_vocalization_types`: types with score ≥ 0.01 (Call, Echolocation, Whistle, Gunshot, Upcall)

More distinct sound types = richer acoustic scene = more scientific value. Normalization to 7.0 reflects the maximum observed in practice.

---

### Dimension 4 — Humpback Temporal Coverage (12%)

```
humpback_coverage = fraction of 1s windows with humpback score ≥ 0.30
```

Sustained humpback presence (many windows above threshold) is more informative than a single high-confidence moment.

---

### Dimension 5 — Cross-Model Agreement (12%)

```
agreement = 0.30×(YAMNet bio flag) + 0.10×(YAMNet marine flag)
           + 0.35×(whale_species flag) + 0.25×(humpback flag)
```

When three independent models (different architectures, training data, sampling frequencies) agree, the probability of a false positive decreases multiplicatively. Sub-weights reflect each model's cetacean specificity.

---

### Dimension 6 — NDSI Soundscape Score (10%)

```
ndsi_score = clip((ndsi_underwater + 1) / 2, 0, 1)
```

Maps the NDSI from [-1, 1] to [0, 1]. High NDSI = biology-dominated soundscape; low NDSI = anthropogenic noise (boats) dominated. Acts as a noise penalty: clips with heavy boat noise score lower even if the cascade detected something.

Source: Stage 3 (`soundscape.json`). If Stage 3 was skipped, this dimension is 0.0.

---

### Dimension 7 — Biological Cluster Signal (8%)

Bonus for clips that belong to a real acoustic cluster (not outlier) where the dominant spectral band is not LOW (which typically indicates boat noise):

| Condition | Score |
|-----------|-------|
| Real cluster (id ≥ 0), dominant band = MID or HIGH | `min(1.0, 0.5 + 0.1 × cluster_size)` |
| Real cluster (id ≥ 0), dominant band = LOW | 0.30 |
| Outlier (cluster_id = -1) | 0.00 |

Source: Stage 4 (`clusters.json`). If Stage 4 was skipped (`--no-cluster`), this dimension is 0.0.

---

### Dimension 8 — Humpback Peak Confidence (5%)

```
humpback_peak = min(max_humpback_score, 1.0)
```

The single highest humpback score across all 1-second windows. Receives low weight (5%) because it is nearly uniform across clips — most clips have humpback detection — so it has weak discriminating power.

---

### Dimension 9 — YAMNet Top-Class Quality (5%)

```
yamnet_quality = min(top1_score × 3.0, 1.0)  if top-1 ∈ biological classes
               = 0.0                           otherwise
```

When YAMNet's most probable class for the entire clip is a biological class ("Animal", "Wild animals", "Insect", "Bird", "Frog", "Cricket", "Whale vocalization", "Roar"), it indicates that most of the audio is biologically active. If top-1 is "Speech", "Silence", or "Noise", biological detections are likely isolated events.

---

## Current Weights Summary

From `backend/config.py → RANK_WEIGHTS`:

| Dimension | Key | Weight |
|-----------|-----|--------|
| Sustained cetacean presence | `whale_sustained` | 18% |
| YAMNet biological richness | `bio_richness` | 15% |
| Acoustic diversity | `acoustic_diversity` | 15% |
| Humpback temporal coverage | `humpback_coverage` | 12% |
| Cross-model agreement | `cross_model` | 12% |
| NDSI soundscape score | `ndsi_score` | 10% |
| Biological cluster signal | `cluster_signal` | 8% |
| Humpback peak confidence | `humpback_peak` | 5% |
| YAMNet top-class quality | `yamnet_quality` | 5% |
| **Total** | | **100%** |

---

## Tier Classification

Final score (0–100) classified into 5 priority levels (`backend/config.py → RANK_TIERS`):

| Tier | Score | Interpretation | Recommended Action |
|------|-------|---------------|-------------------|
| **CRITICAL** | ≥ 65 | Multiple strong dimensions, high multi-model agreement | Immediate priority review |
| **HIGH** | ≥ 45 | Clear biological signals from at least one model | Detailed review |
| **MODERATE** | ≥ 25 | Signals detected with moderate confidence | Review when possible |
| **LOW** | ≥ 10 | Weak or single-model signals | Optional review |
| **MINIMAL** | < 10 | Little or no biological evidence | Low priority |

---

## Output

```
outputs/ranking/
├── ranked.json   # Full ranking: scores, tiers, 9 components, flags, annotations
└── ranked.csv    # Flat version for spreadsheet import
```

```bash
# Run ranking only (reuse all previous stage outputs)
python -m backend.run --skip-clip --skip-cascade --skip-soundscape --skip-cluster
```

> Script: `backend/pipeline/stage5_rank.py`

---

## Limitations

1. **Bias toward orcas**: The multispecies model has high sensitivity for *Orcinus orca*, which may inflate scores for clips with acoustically similar patterns.
2. **Geographic bias**: Models were trained on North Atlantic/Pacific data. Galápagos species (South Pacific humpback, bottlenose dolphin, Bryde's whale) may not be perfectly represented.
3. **NDSI and cluster scores are optional**: If `--no-cluster` is used, dimensions 7 (cluster_signal) and 6 (ndsi_score, if Stage 3 is also skipped) default to 0.0, effectively compressing the score range. Weights do not auto-renormalize.
4. **Scores are not probabilities**: A high score indicates greater potential value for human review, not scientific certainty of species presence.
5. **Requires expert validation**: Final biological classifications must be confirmed by a marine bioacoustics specialist.
