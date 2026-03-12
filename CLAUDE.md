# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

**Dragon Ocean Analyzer** — a SALA 2026 hackathon dashboard for analyzing marine acoustic recordings from the Galápagos Marine Reserve. It runs a 6-stage AI pipeline to classify ~926 hydrophone recordings and ranks them by biological importance so marine biologists know which to review first.

**Always read `docs/PROJECT_OVERVIEW.md` first** — it is the master document containing schemas, API routes, and the full context.

---

## Commands

### Frontend
```bash
cd frontend
npm install
npm run dev       # Dev server (http://localhost:5173 or :3000)
npm run build     # Production build
npm run preview   # Preview build
```

### Backend Pipeline
```bash
# Install (Python 3.10+, from repo root)
pip install -r requirements.txt

# Run full pipeline
python -m backend.run --source hackathon_data/marine-acoustic

# Resume with checkpoints (skip completed stages)
python -m backend.run --skip-clip --skip-cascade        # reuse clips + cascade outputs
python -m backend.run --no-cluster                       # skip GPU-heavy Stage 6
python -m backend.run --skip-clip --skip-cascade --skip-cluster --no-cluster  # ranking only
```

No test suite or linting configuration exists in this project.

---

## Architecture

### Two Independent Components

**Backend** (`backend/`) — Python ML pipeline, no server, outputs JSON/CSV files to `outputs/`.

**Frontend** (`frontend/`) — React 18 + Vite 6 dashboard. Vite's custom middleware plugin (`vite.config.js`) serves pipeline outputs and audio directly — no separate API server is needed.

### Pipeline Stages (run via `backend/run.py`)

| Stage | File | What it does |
|-------|------|-------------|
| 0 | `stage1_clip.py` | Silence detection + WAV segmentation |
| 1–6 | `stage2_cascade.py` | Perch 2.0 · Multispecies Whale · Humpback · NatureLM · BioLingual · Dasheng |
| 5 | `stage3_soundscape.py` | NDSI, entropy, band power, boat_score indices |
| 6 | `stage4_cluster.py` | NatureLM embeddings → UMAP → HDBSCAN (GPU or CPU) |
| 4 | `stage5_rank.py` | 6-model equal-weight score → 5 tiers → `ranked.json` + `ranked.csv` |

All constants (thresholds, weights, keywords) are centralized in `backend/config.py`.

### Output Directory Layout
```
outputs/
├── clips/           # Stage 0 segmented WAVs
├── analysis/        # results.json, spectrograms/, annotations/
├── ranking/         # ranked.json, ranked.csv (final output)
├── soundscape/      # Stage 5 outputs
└── clusters/        # Stage 6 outputs
```

### Vite Middleware API Routes
The Vite dev server (and build) acts as the API layer:

| Route | Source |
|-------|--------|
| `/api/pipeline/analysis/results.json` | `outputs/analysis/results.json` |
| `/api/pipeline/ranking/ranked.json` | `outputs/ranking/ranked.json` |
| `/api/pipeline/analysis/spectrograms/{file}` | `outputs/analysis/spectrograms/` |
| `/api/pipeline/analysis/annotations/{id}_cascade.json` | `outputs/analysis/annotations/` |
| `/api/pipeline/soundscape/*` | `outputs/soundscape/` |
| `/api/pipeline/clusters/*` | `outputs/clusters/` |
| `/api/audio/{filename}` | `backend/data/audio/` (HTTP 206 range) |
| `/api/clean-spectrogram/{filename}` | On-the-fly generation |

Audio files are searched in subdirectories: `Music_Soundtrap_Pilot/`, `6478/`, `5783/`.

### Frontend Structure
- `src/config.js` — API routes, tier colors/labels, species map, scoring dimensions
- `src/utils.js` — Data loaders (loadRankedData, loadCascadeResults, etc.), CSV export
- `src/pages/` — LandingPage, SingleObservation, MultipleObservations
- `src/components/` — SpectrogramViewer (zoom/pan/playback), Charts, ReportTable, AnalysisPanel

### Ranking System
6-model equal-weight score (0–100) produces 5 tiers:
- **CRITICAL** ≥70, **HIGH** ≥50, **MODERATE** ≥30, **LOW** ≥15, **MINIMAL** <15

`score = mean(bio_signal_score per model) × 100` — models: `perch`, `multispecies`, `humpback`, `naturelm`, `biolingual`, `dasheng` (each weight = 1/6). `boat_score` from soundscape is stored as metadata only (does not affect score).

---

See `docs/FRONTEND_NEXT_STEPS.md` for the full list of pending features and bugs.