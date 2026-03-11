# PROJECT OVERVIEW — Dragon Ocean Analyzer

> **This is the master document.** Any AI (Claude, etc.) working on this
> project should read this file first. It contains all the necessary context.

---

## What this project is

**Dragon Ocean Analyzer** is a web dashboard for the SALA 2026 hackathon that visualizes results from an underwater audio classification pipeline. 3-minute presentation.

**Problem:** San Cristóbal Bay (Galápagos) has SoundTrap ST300 hydrophones that recorded ~926 WAV files (~97 hours). Marine biologists need to know which ones to review first.

**Our solution:** A 6-stage pipeline (segmentation + 3 AI models + soundscape + clustering) + a biological importance ranking + an interactive frontend that shows everything.

---

## Pipeline (stages 0-6)

```
WAV → Stage 0: AudioClipper    (silence filter + segmentation)
    → Stage 1: YAMNet          (521 AudioSet classes, bio vs noise)
    → Stage 2: Multispecies    (12 classes: 7 species + 5 vocalizations)
    → Stage 3: Humpback Whale  (binary per 1s window)
    → Stage 5: Soundscape      (NDSI — penalizes boat dominance)
    → Stage 6: Clustering      (UMAP + HDBSCAN, bonus for biological cluster)
    → Stage 4: Ranking         (9 weighted dimensions, score 0-100, 5 tiers)
```

**IMPORTANT:** The 3 models (stages 1-3) always run (no gating). It is not a true cascade — it is a parallel pipeline. See BACKEND_AUDIT.md §4.1.

### Models

| Stage | Model | Input SR | Output |
|-------|--------|----------|--------|
| 1 | YAMNet (TFHub google/yamnet/1) | 16 kHz | 521 classes, embeddings |
| 2 | Multispecies Whale (Kaggle google/multispecies-whale/TF2/default/2) | 24 kHz | 12 classes per 5s window |
| 3 | Humpback Whale (TFHub google/humpback_whale/1) | 10 kHz | binary score per 1s window |

### Ranking v2 (9 dimensions)

| Dimension (key) | Weight | Measures |
|-----------------|------|------|
| `whale_sustained` | 18% | Composite max + mean multispecies |
| `bio_richness` | 15% | Count + YAMNet bio scores |
| `acoustic_diversity` | 15% | Species + vocalization types |
| `humpback_coverage` | 12% | Fraction of windows with humpback |
| `cross_model` | 12% | Convergence across models |
| `ndsi_score` | 10% | Marine NDSI (Stage 5, penalizes boats) |
| `cluster_signal` | 8% | Bonus for biological cluster (Stage 6) |
| `humpback_peak` | 5% | Maximum humpback score |
| `yamnet_quality` | 5% | Whether YAMNet top-1 is biological |

**Tiers:** CRITICAL (≥65), HIGH (≥45), MODERATE (≥25), LOW (≥10), MINIMAL (<10)

---

## Dataset analyzed

- **100 recordings** from the Pilot deployment (48 kHz, ~5 min each)
- **Filenames:** `YYMMDD_SEQUENCE.wav` (e.g.: `190806_3754.wav` = Aug 6, 2019)
- **1 single WAV** in the repo (`190806_3754.wav`, 15.9s). The other 99 were processed externally.

### Current results

| Metric | Value |
|--------|-------|
| CRITICAL | 3 files |
| HIGH | 35 |
| MODERATE | 40 |
| LOW | 19 |
| MINIMAL | 3 |
| YAMNet bio signals | 70/100 |
| any_whale_detected | 61/100 |
| humpback_detected | **99/100** (suspicious — see notes) |

### Scientific warnings

1. **Biological content has NOT been verified** by domain experts. Models detect patterns, they do not confirm presence.
2. **Humpback FP reduced:** threshold raised from 0.1 → 0.3. Exact figure depends on the active dataset.
3. `'singing'`/`'speech'`/`'music'` removed from `YAMNET_BIO_KEYWORDS` — no longer inflate bio_richness.
4. **The dB values are relative**, not calibrated to µPa.

---

## Repo structure

```
dragon-ocean-analyzer/
├── README.md               ← Intro + quickstart
├── LICENSE
├── requirements.txt        ← Python deps (librosa, tensorflow, etc.)
├── .gitignore
│
├── backend/                ← Python ML pipeline
│   ├── config.py           ← All pipeline constants
│   ├── run.py              ← Entry point: python -m backend.run --source ...
│   ├── download_audio.py   ← Downloads WAVs from R2 (called by frontend)
│   ├── pipeline/
│   │   ├── stage1_clip.py       ← Silence filter + WAV segmentation
│   │   ├── stage2_cascade.py    ← YAMNet + Multispecies + Humpback
│   │   ├── stage3_soundscape.py ← NDSI (scikit-maad)
│   │   ├── stage4_cluster.py    ← UMAP + HDBSCAN embeddings
│   │   └── stage5_rank.py       ← 9-dimensional ranking (score 0-100)
│   └── utils/              ← Helpers: r2_download, spectrograms, tester…
│
├── frontend/               ← React 18 + Vite 6
│   ├── src/
│   │   ├── main.jsx, App.jsx      ← Entry + router
│   │   ├── config.js              ← Tiers, species map, scoring dimensions
│   │   ├── utils.js               ← Data loaders, CSV export
│   │   ├── styles.css             ← Dark+light theme (CSS custom properties)
│   │   ├── context/ThemeContext.jsx
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx
│   │   │   ├── SingleObservation.jsx
│   │   │   └── MultipleObservations.jsx
│   │   └── components/
│   │       ├── Navbar.jsx, Sidebar.jsx
│   │       ├── PipelineDiagram.jsx
│   │       ├── SpectrogramViewer.jsx  ← Zoom, pan, audio, timeline
│   │       ├── Charts.jsx             ← Doughnut, Bar, Line, Radar
│   │       ├── ReportTable.jsx        ← Sort, filter, CSV export
│   │       ├── AnalysisPanel.jsx      ← Score, radar, 3 classifiers, charts
│   │       ├── DetailModal.jsx
│   │       └── TierBadge.jsx
│   ├── vite.config.js             ← Middleware serves outputs/
│   └── package.json               ← React 18, Vite 6, Chart.js
│
├── scripts/                ← Utilities and deployment
│   ├── r2_download.py      ← Downloads data from Cloudflare R2
│   ├── manifest.json       ← Hackathon dataset manifest
│   ├── r2_manifest_template.json
│   ├── runpod_run.sh       ← Launcher for RunPod GPU
│   └── data_download.ipynb ← Interactive download notebook
│
├── docs/                   ← Project documentation
│   ├── PROJECT_OVERVIEW.md ← THIS FILE (read first)
│   ├── FRONTEND_AUDIT.md
│   ├── PAPER_NOTES.md
│   └── guidelines.md
│
└── outputs/        ← Generated by run.py (gitignored)
    ├── clips/              ← Segmented WAVs (Stage 0)
    ├── analysis/           ← results.json + spectrograms/ + annotations/
    ├── ranking/            ← ranked.json + ranked.csv
    ├── soundscape/         ← Stage 5 output
    └── clusters/           ← Stage 6 output
```

---

## Data schemas (quick reference)

### cascade_results.json → per file

```
stage1_yamnet:
  top_classes: [{class, score}]
  bio_detections: [{class, score}]
  has_bio_signal: bool
  has_marine_signal: bool

stage2_multispecies:
  detections: [{class_code, species, max_score, mean_score}]
  top_species: string
  top_max_score: float
  any_whale_detected: bool (threshold ≥ MULTISPECIES_DETECTION_THR = 0.10)
  num_windows: int
  top_time_series: [float]  ← included in JSON since Bug 1.1 fix

stage3_humpback:
  max_score: float
  mean_score: float
  fraction_above_threshold: float
  humpback_detected: bool (threshold ≥ HUMPBACK_THRESHOLD = 0.30)
  num_windows: int
  time_series: [float]  ← included in JSON since Bug 1.1 fix
```

### ranked.json → per file (outputs/ranking/)

```
total_ranked: int
tier_distribution: {CRITICAL, HIGH, MODERATE, LOW, MINIMAL}
rankings: [{
  rank, filename, score (0-100), tier
  components: {whale_sustained, bio_richness, acoustic_diversity,
               humpback_coverage, cross_model, ndsi_score,
               cluster_signal, humpback_peak, yamnet_quality}
  cascade_flags: [string]
  top_species: string  ← full name, not code
  annotations: [string]
}]
```

### Multispecies model classes (12 total)

**Species (7):** Oo (Orca), Mn (Humpback), Eg (Right whale), Bp (Fin), Bm (Blue), Ba (Minke), Be (Beaked)
**Vocalizations (5):** Call, Echolocation, Gunshot, Upcall, Whistle

Only detected in our data: Bm, Bp, Eg, Mn, Oo + Call, Echolocation, Gunshot, Upcall, Whistle. Ba and Be never appear.

---

## API Routes (Vite middleware)

| Route | Serves from | Content |
|------|------------|---------|
| `/api/pipeline/analysis/*` | `outputs/analysis/` | results.json, spectrograms/, annotations/ |
| `/api/pipeline/ranking/*` | `outputs/ranking/` | ranked.json, ranked.csv |
| `/api/pipeline/soundscape/*` | `outputs/soundscape/` | soundscape.json |
| `/api/pipeline/clusters/*` | `outputs/clusters/` | clusters.json |
| `/api/audio/*` | `backend/data/raw_data/` | WAV files (HTTP 206 range) |

---

## Known bugs (summary — see audits for detail)

### Frontend
- ✅ **time_series did not exist in JSON** → fixed, now included
- ✅ **API routes disconnected** → fixed, now `/api/pipeline/*`
- ✅ **cross_model_agreement** → fixed to `cross_model`
- ✅ **visual threshold 0.5** → fixed to 0.3 in TimeSeriesChart
- **SPECIES_MAP incomplete** → missing Call, Echolocation, Gunshot, Upcall, Whistle (see `docs/FRONTEND_AUDIT.md` §1.2)
- **Missing disclaimer** of unverified biological content

### Backend
- ✅ **time_series was deleted** from consolidated JSON — fixed
- ✅ **'singing'/'speech'/'music' as bio** — removed from YAMNET_BIO_KEYWORDS
- ✅ **HUMPBACK_THRESHOLD = 0.1** (99% FP) → raised to 0.3
- ✅ **0.1 hardcoded** in stage2_cascade.py → extracted as MULTISPECIES_DETECTION_THR in config.py
- ✅ **No requirements.txt** — now exists
- **Cascade without gates** → all 3 models always run (pending decision — see analysis: YAMNet does not detect cetaceans in this dataset, a YAMNet-based gate would block the pipeline)

---

## Code conventions

### Frontend
- CSS: everything in `styles.css` with custom properties. Maintain `[data-theme="dark"]` AND `[data-theme="light"]`
- Data: use functions from `utils.js` (loadRankedData, loadCascadeResults, etc.)
- Charts: components in `Charts.jsx` using react-chartjs-2
- Config: species map, tiers, dimensions in `config.js`
- Components: one file per component in `components/`

### Backend
- Pipeline execution: `python -m backend.run --source <data_dir>` (orchestrates stages 0-6)
- Output dir: `outputs/` (clips/, analysis/, ranking/, soundscape/, clusters/)

---

## Hackathon context

- **Event:** SALA 2026 AI Hackathon
- **Demo:** 3 minutes, 5 slides max
- **Judging:** Originality (30%), Technical Execution (30%), Impact & Relevance (25%), Presentation (15%)
- **Key pitch points:**
  - Tool for marine biologists that prioritizes which recordings to review
  - 9 scoring dimensions, not just a simple threshold
  - 100 files analyzed, 3 CRITICAL identified
  - Galápagos: 23 cetacean species, 14 residents/visitors
  - Unverified content = scientific honesty (valuable for judges)
- **Future vision:** similarity search (Agile Modeling), PCEN, more units, active learning

---

## Base prompt for Claude

```
I work on "Dragon Ocean Analyzer" — React dashboard + Python pipeline for
marine bioacoustics, SALA 2026 hackathon (Galápagos Marine Reserve).

READ FIRST: docs/PROJECT_OVERVIEW.md (full project context)
THEN READ: docs/FRONTEND_AUDIT.md based on your task

Repo:
  backend/          — Python pipeline stages 0-6
  frontend/src/     — React 18 + Vite 6 + Chart.js
  scripts/          — download and deployment utilities
  docs/             — documentation
  outputs/  — generated artifacts (gitignored)

My task is: [DESCRIBE]
```