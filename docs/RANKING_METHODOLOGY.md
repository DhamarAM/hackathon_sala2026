# Biological Importance Ranking — Methodology (v4)

## Objective

Rank all processed audio clips by **biological importance**, allowing researchers to focus their manual review on the recordings with the richest and most relevant content.

## Score Formula

```
score (0–100) = mean(bio_signal_score per model) × 100
```

Six models each contribute their `bio_signal_score [0, 1]` with **equal weight (1/6)**. Models that independently agree on biological content push the score up linearly.

This approach is robust to out-of-domain failures: if one model produces near-zero scores for a type of recording it was not calibrated on, the other five models can still produce a meaningful result. No single model is authoritative.

---

## The 6 Models

| Model | Key | What bio_signal_score measures |
|-------|-----|-------------------------------|
| Perch 2.0 | `perch` | Fraction of detections in biological/marine classes, normalized |
| Multispecies Whale | `multispecies` | Peak cetacean score (normalized to detection threshold) + species richness |
| Humpback Detector | `humpback` | Peak humpback score + fraction of windows above threshold |
| NatureLM-BEATs | `naturelm` | Embedding entropy + magnitude (structural complexity of bio signals) |
| BioLingual | `biolingual` | Probability mass on biological labels (zero-shot) |
| Dasheng | `dasheng` | Temporal variance + embedding diversity (non-stationarity = biology) |

Each model's `bio_signal_score` is computed independently in `backend/pipeline/stage2_cascade.py` and stored in `outputs/analysis/results.json`. The ranking stage (`stage5_rank.py`) reads these values and averages them.

### Design rationale: normalization choices

**Multispecies:** normalized by `MULTISPECIES_DETECTION_THR = 0.01` (not the original 0.10). Rationale: hydrophone recordings produce scores 10–50× lower than the aerial/surface recordings this model was calibrated on. Normalizing by 0.01 means "a clip at the detection threshold contributes ~0.5 to bio_signal". This is an intentional domain-adaptation choice — see comments in `stage2_cascade.py`.

**Humpback:** `0.5 × (max_score / threshold) + 0.5 × min(coverage × 2, 1)`. Peak component saturates at threshold (0.3); coverage saturates at 50% of windows above threshold.

**Dasheng:** Thresholds recalibrated for marine audio: `temporal_scale = 0.5` (was 3.0), `diversity_scale = 0.1` (was 0.3). Marine recordings are stationary — terrestrial defaults would produce near-zero scores on all clips.

---

## Soundscape and Cluster metadata (not in score)

`boat_score` (from soundscape) and `cluster_id` (from clustering) are stored as metadata in `ranked.json` but do **not** affect the score. Rationale: BioLingual already has "boat engine noise" as a label — if a clip is dominated by boat noise, its bio_signal_scores will be low without an additional penalty (double-counting).

---

## Tier Classification

From `backend/config.py → RANK_TIERS`:

| Tier | Score | Recommended Action |
|------|-------|--------------------|
| **CRITICAL** | ≥ 70 | Immediate priority review |
| **HIGH** | ≥ 50 | Detailed review |
| **MODERATE** | ≥ 30 | Review when possible |
| **LOW** | ≥ 15 | Optional review |
| **MINIMAL** | < 15 | Low priority |

---

## Output

```
outputs/ranking/
├── ranked.json   # Full ranking: scores, tiers, 6 model components, flags, annotations
└── ranked.csv    # Flat version: rank, filename, score, tier, 6 model scores, boat_score, flags
```

```bash
# Run ranking only (reuse all previous stage outputs)
python -m backend.run --skip-clip --skip-cascade --skip-soundscape --skip-cluster
```

> Script: `backend/pipeline/stage5_rank.py`

---

## Limitations

1. **Domain mismatch**: All models were trained on data that is not perfectly representative of Galápagos hydrophone recordings. Perch 2.0 and NatureLM on terrestrial audio; Google whale models on surface/aerial recordings. Thresholds are calibrated empirically.
2. **Bias toward orcas**: The multispecies model has high sensitivity for *Orcinus orca*, which may inflate scores for clips with acoustically similar patterns.
3. **Geographic bias**: Models trained on North Atlantic/Pacific data. Some species codes (Eg = Right whale) appear in detections but that species is not found in Galápagos waters — likely responding to similar acoustic patterns from local species.
4. **Scores are not probabilities**: A high score indicates greater potential value for human review, not scientific certainty of species presence.
5. **Requires expert validation**: Final biological classifications must be confirmed by a marine bioacoustics specialist.