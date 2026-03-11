# Frontend — Next Steps

> Current state as of March 2026. Read this instead of FRONTEND_AUDIT.md (outdated).

---

## Bugs to Fix Now

### 1. `SCORING_DIMENSIONS` desync with backend — `config.js:40-48`

The frontend defines 7 dimensions with wrong weights and one wrong key. The backend computes 9.

**Current (wrong):**
```js
{ key: 'whale_sustained',    weight: 0.20 },
{ key: 'bio_richness',       weight: 0.20 },
{ key: 'acoustic_diversity', weight: 0.20 },
{ key: 'humpback_coverage',  weight: 0.15 },
{ key: 'cross_model',        weight: 0.15 },
{ key: 'humpback_peak',      weight: 0.05 },
{ key: 'yamnet_top_quality', weight: 0.05 },  // ← wrong key name
```

**Fix — replace with:**
```js
{ key: 'whale_sustained',    label: 'Whale Sustained',    weight: 0.18 },
{ key: 'bio_richness',       label: 'Bio Richness',       weight: 0.15 },
{ key: 'acoustic_diversity', label: 'Acoustic Diversity', weight: 0.15 },
{ key: 'humpback_coverage',  label: 'Humpback Coverage',  weight: 0.12 },
{ key: 'cross_model',        label: 'Cross-Model',        weight: 0.12 },
{ key: 'ndsi_score',         label: 'NDSI Score',         weight: 0.10 },
{ key: 'cluster_signal',     label: 'Cluster Signal',     weight: 0.08 },
{ key: 'humpback_peak',      label: 'Humpback Peak',      weight: 0.05 },
{ key: 'yamnet_quality',     label: 'YAMNet Quality',     weight: 0.05 },
```

Impact: the radar chart in `AnalysisPanel.jsx` silently shows 0 for `yamnet_top_quality` (key doesn't exist in ranked.json) and omits `ndsi_score` and `cluster_signal` entirely.

---

### 2. "7-dimension" copy still in LandingPage — `LandingPage.jsx:115`

```jsx
// Current (wrong):
Prioritize recordings using a 7-dimension weighted scoring system

// Fix:
Prioritize recordings using a 9-dimension weighted scoring system
```

---

### 3. Humpback threshold footnote says 0.1 — `LandingPage.jsx:78`

```jsx
// Current (wrong):
Threshold = 0.1.

// Fix:
Threshold = 0.3.
```

The threshold was raised from 0.1 to 0.3 in `backend/config.py` to reduce false positives.

---

### 4. "Three-stage cascade" copy is incomplete — `LandingPage.jsx:87`

```jsx
// Current:
Three-stage sequential cascade classifier with biological importance ranking

// Fix:
5-stage pipeline: segmentation → 3-model cascade → soundscape → clustering → biological ranking
```

---

## Features for the Demo

### Must Have

#### Species Detection Bar Chart
A bar chart across all files showing how many clips each class code was detected in (Oo, Mn, Echolocation, etc.). Aggregate from `cascadeData.files` — loop over each file's `stage2_multispecies.detections`.

Add to `MultipleObservations.jsx`. Data function goes in `utils.js`. Chart component goes in `Charts.jsx`.

#### Show All Multispecies Detections per Clip
`AnalysisPanel.jsx` currently only shows `top_species` and `top_max_score`. The data has a full `detections[]` array with every class detected.

Show the list with max/mean per class, e.g.:
```
Mn (Humpback):    max 38%  mean 1.4%
Oo (Orca):        max 33%  mean 1.4%
Echolocation:     max 11%  mean 0.6%
```

---

### Should Have

#### Temporal Pattern Chart
Pilot filenames encode date: `YYMMDD_sequence.wav`. Parse the date from `filename` to show detections by day. Do CRITICAL files cluster on certain dates?

#### NDSI / Soundscape Panel
The pipeline already computes NDSI, band power, and entropy per clip (Stage 5). None of this is displayed in the frontend yet. Add a panel in `SingleObservation.jsx` or `AnalysisPanel.jsx` showing:
- NDSI underwater (biology vs noise ratio)
- Dominant band (LOW / MID / HIGH)
- Boat score

Data source: load `soundscape.json` via a new `loadSoundscapeData()` in `utils.js`.

#### Cluster Info Panel
Stage 6 produces `cluster_id`, `umap_x`, `umap_y`, and `cluster_dominant_band` per clip. Add a small cluster info badge to `SingleObservation.jsx`. Cluster 0/1/2 with color, outlier = grey.

---

### Nice to Have

- Comparison view: CRITICAL clip vs MINIMAL clip side by side
- Keyboard shortcuts: Space = play/pause, ←/→ = seek
- Fix spectrogram frequency hover to use actual sample rate instead of hardcoded 24 kHz

---

## What's Already Done

| Item | Status |
|------|--------|
| `time_series` arrays in results.json | ✅ Fixed |
| SPECIES_MAP includes all 12 classes (5 vocalizations) | ✅ Fixed |
| Disclaimer banner on landing page | ✅ Done |
| "Identify 7 whale species" → "Detect 12 classes" | ✅ Fixed |
| PipelineDiagram reflects real pipeline | ✅ Fixed |
| `cross_model_agreement` → `cross_model` | ✅ Fixed |
| API routes point to `/api/pipeline/*` | ✅ Correct |
| `bio_signals` and `whale_detected` field names | ✅ Fixed (was `yamnet_bio_signals`, `whale_species_detected`) |

---

## File Map

```
frontend/src/
├── config.js               ← SCORING_DIMENSIONS needs update (bug #1 above)
├── utils.js                ← add loadSoundscapeData(), loadClustersData()
├── pages/
│   ├── LandingPage.jsx     ← copy fixes (#2, #3, #4 above)
│   ├── SingleObservation.jsx
│   └── MultipleObservations.jsx  ← add species detection chart
└── components/
    ├── AnalysisPanel.jsx   ← show full detections list, add NDSI panel
    ├── Charts.jsx          ← add SpeciesDetectionChart
    └── SpectrogramViewer.jsx
```

## Data Available

| Route | File | Key fields |
|-------|------|------------|
| `/api/pipeline/analysis/results.json` | `outputs/analysis/results.json` | `total_files`, `bio_signals`, `whale_detected`, `humpback_detected`, `files{}` |
| `/api/pipeline/ranking/ranked.json` | `outputs/ranking/ranked.json` | `total_ranked`, `tier_distribution`, `rankings[]` with 9 components |
| `/api/pipeline/analysis/annotations/{id}_cascade.json` | `outputs/analysis/annotations/` | full per-clip result |
| `/api/pipeline/analysis/spectrograms/{file}` | `outputs/analysis/spectrograms/` | 4-panel PNG |
| (not yet exposed) | `outputs/soundscape/soundscape.json` | `ndsi_underwater`, `dominant_band`, `boat_score` per clip |
| (not yet exposed) | `outputs/clusters/clusters.json` | `cluster_id`, `umap_x`, `umap_y`, `cluster_dominant_band` per clip |
