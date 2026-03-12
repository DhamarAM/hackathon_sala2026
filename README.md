# Dragon Ocean Analyzer

**SALA 2026 Hackathon** — Marine Bioacoustics, Galápagos Marine Reserve

---

## The Problem

Marine biologists monitoring the Galápagos Marine Reserve collect hundreds of hydrophone recordings per deployment. Manually reviewing each one to find whale calls, dolphin clicks, or unusual biological activity is time-prohibitive — a single researcher can take days to triage a dataset that spans a few days of recording.

## The Solution

Dragon Ocean Analyzer is an AI-powered dashboard that automatically ranks hydrophone recordings by biological importance, so researchers know exactly which clips to review first.

A 6-model machine learning pipeline processes each recording, assigns a biological importance score (0–100), and classifies it into one of 5 tiers (Critical → Minimal). The interactive dashboard lets marine biologists explore spectrograms, listen to audio, and inspect per-model detection evidence — running locally with a single command.

---

## How It Works

```
Hydrophone WAVs
      │
      ▼
 1. Segmentation — silence removal, active segments (max 30s clips)
      │
      ▼
 2. Cascade classifiers — 6 models run in parallel
      │
      ├── Perch 2.0          Google bioacoustic classifier (~14k classes)
      ├── Multispecies Whale  12 cetacean species + vocalization types
      ├── Humpback Detector   Binary humpback presence (1s resolution)
      ├── NatureLM-BEATs      Bioacoustic transformer (structural complexity)
      ├── BioLingual          Zero-shot classifier (detects boat noise too)
      └── Dasheng             Self-supervised audio complexity
      │
      ▼
 3. Soundscape indices — NDSI, band power, boat noise score
      │
      ▼
 4. Clustering — NatureLM embeddings → UMAP → HDBSCAN
      │
      ▼
 5. Biological importance ranking
           score = mean(6 bio_signal_scores) × 100
           Tiers: CRITICAL ≥70 · HIGH ≥50 · MODERATE ≥30 · LOW ≥15 · MINIMAL
```

Each model contributes its `bio_signal_score [0, 1]` with equal weight. Models that agree on biological content push the score up linearly.

---

## Dashboard Features

- **Ranked list** of all recordings sorted by biological importance score
- **Spectrogram viewer** with zoom, pan, and synchronized audio playback
- **Radar chart** showing the 6-model score breakdown per clip
- **Species detection** panel with per-species probability timelines
- **Batch export** to CSV for further analysis
- **Soundscape indices** (NDSI, boat score) as reviewer context

---

## Quick Start

### View the dashboard (pre-computed results)
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

Vite serves pre-computed pipeline outputs from `outputs/` — no backend needed to view the demo.

> The `outputs/` directory included in the repo contains a **sample of results** from a subset of recordings, enough to fully navigate the dashboard without running the pipeline.

### Test the pipeline with the included sample clip

A single WAV clip is included for local testing:

```
hackathon_data/marine-acoustic/sample/190806_3761.wav
```

```bash
pip install -r requirements.txt
python -m backend.run --source hackathon_data/marine-acoustic/sample

# Resume from checkpoint (skip completed stages)
python -m backend.run --skip-clip --skip-cascade        # reuse clips + cascade
python -m backend.run --no-cluster                       # skip GPU clustering
```

See `backend/README.md` for the full list of flags and checkpoint-resume options.

---

## Dataset

Hundreds of hydrophone recordings from the Galápagos Marine Reserve, captured with SoundTrap ST300 at 48–96 kHz. Recordings span multiple deployments across 2019–2020.

Species known in the region: Orca, Humpback whale, Fin whale, Blue whale, Minke whale, Beaked whale, dolphins.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| ML Pipeline | Python 3.10 · TensorFlow 2.17 · PyTorch · librosa |
| AI Models | Perch 2.0 · Google Multispecies Whale · Google Humpback · NatureLM-BEATs · BioLingual · Dasheng |
| Clustering | UMAP · HDBSCAN |
| Frontend | React 18 · Vite 6 · Chart.js · React Router |
| Data | No database (yet) — pipeline outputs static JSON/CSV served by Vite middleware. The pipeline is ready to deploy and store results in the cloud. |

---

## Repo Structure

```
├── backend/
│   ├── pipeline/          stage1_clip · stage2_cascade · stage3_soundscape
│   │                      stage4_cluster · stage5_rank
│   ├── config.py          all thresholds and constants
│   └── run.py             pipeline entry point
│
├── frontend/
│   └── src/
│       ├── pages/         LandingPage · SingleObservation · MultipleObservations
│       └── components/    SpectrogramViewer · Charts · AnalysisPanel · ReportTable
│
├── hackathon_data/
│   └── marine-acoustic/
│       └── sample/        ← 190806_3761.wav included for pipeline testing
│
├── outputs/               ← sample results included for frontend demo (full run gitignored)
│   ├── clips/             segmented WAVs
│   ├── analysis/          results.json · spectrograms · annotations
│   ├── soundscape/        NDSI timeseries · soundscape.json
│   ├── clusters/          UMAP plot · clusters.json
│   └── ranking/           ranked.json · ranked.csv  ← final output
│
└── docs/
    ├── MODELS.md                ← full documentation for all 8 models (6 ensemble + UMAP + HDBSCAN)
    ├── ENSEMBLE_MODELS.md       ← architecture, thresholds, and per-clip output schema for the 6 classifiers
    ├── RANKING_METHODOLOGY.md   ← scoring formula, tier logic, normalization choices, and limitations
    └── GUIDELINES.md            ← SALA 2026 hackathon rules and submission requirements
```

---

## Scientific Context

The scoring philosophy mirrors ensemble model practice: no single model is authoritative for out-of-domain hydrophone recordings. Perch 2.0 and NatureLM were trained on terrestrial/general bioacoustics; the Google whale models on surface/aerial recordings; BioLingual and Dasheng are domain-agnostic. Averaging their `bio_signal_scores` creates a robust signal where genuine biological content triggers multiple independent detectors simultaneously.

All detection thresholds are calibrated for **hydrophone recordings**, which produce scores 10–50× lower than the surface recordings these models were originally calibrated on. See `backend/config.py` for the full parameter documentation.
