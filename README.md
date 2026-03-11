# Dragon Ocean Analyzer

**SALA 2026 Hackathon** — Marine Acoustic Monitoring Platform for the Galapagos Marine Reserve

---

## Project Overview

The Bay of San Cristobal in the Galapagos hosts dolphins, sea lions, and potentially humpback whales, but is also one of the busiest maritime traffic areas in the archipelago. The Galapagos Science Center deployed SoundTrap ST300 hydrophones to continuously record underwater audio.

**Our solution:** A web dashboard that visualizes the output of a 3-stage AI cascade classifier pipeline, helping marine biologists prioritize which recordings to manually review based on biological importance.

### The Pipeline

```
WAV Audio  -->  Stage 1: YAMNet (521 AudioSet classes, bio vs mechanical vs silence)
           -->  Stage 2: Google Multispecies Whale Detector (7 species, 5 vocalization types)
           -->  Stage 3: Google Humpback Whale Detector (binary humpback presence per second)
           -->  Biological Importance Ranking v2 (7-dimension weighted score, 5 tiers)
           -->  Frontend Dashboard (this repo)
```

### Dataset

- **Source:** SoundTrap ST300 hydrophones (48-144 kHz sample rates)
- **Units:** Pilot (721 files, 48kHz), Unit 6478 (189 files, 96kHz), Unit 5783 (16 files, 144kHz)
- **Total:** ~926 WAV files, ~97 hours of audio
- **Currently analyzed:** 100 recordings from Pilot deployment
- **Audio content:** Boat noise, ambient ocean, transient signals; animal vocalizations unverified but detected by models

### Ranking System (v2)

Each recording gets a 0-100 biological importance score from 7 weighted dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Whale confidence | 20% | Composite of max + mean multispecies scores |
| Bio richness (YAMNet) | 20% | Count + score of biological detections |
| Acoustic diversity | 20% | Number of vocalization types detected |
| Humpback coverage | 15% | % of time windows with humpback signal |
| Cross-model agreement | 15% | Convergence across all 3 classifiers |
| Humpback peak | 5% | Maximum humpback probability |
| YAMNet top quality | 5% | Whether top-1 class is biological |

**Tiers:** CRITICAL (>=65), HIGH (>=45), MODERATE (>=25), LOW (>=10), MINIMAL (<10)

---

## Repo Structure

```
hackathon_sala2026/
├── backend/                    # Python pipeline (classmates' code)
│   ├── src/                    # Python modules
│   ├── data/raw_data/          # WAV audio files
│   ├── output/                 # Stage 1 results: analysis_results.json + spectrograms
│   ├── output2/                # Stages 2-3 results: cascade_results.json + ranked_biological.json
│   ├── analyze_marine_audio.py # Band analysis + spectrogram generation
│   ├── cascade_classifier.py   # 3-stage AI pipeline
│   └── rank_biological_importance.py  # Scoring + ranking
│
├── frontend/                   # React dashboard (OUR code)
│   ├── src/
│   │   ├── pages/              # LandingPage, SingleObservation, MultipleObservations
│   │   ├── components/         # SpectrogramViewer, Charts, ReportTable, etc.
│   │   ├── context/            # ThemeContext (dark/light)
│   │   ├── App.jsx             # Router + layout
│   │   ├── config.js           # Tier config, species map, scoring dimensions
│   │   ├── utils.js            # Data loaders, CSV export
│   │   └── styles.css          # Full theme system (dark + light)
│   ├── vite.config.js          # Dev server + data middleware
│   ├── FEATURE_STATUS.md       # What's done and what's TODO
│   └── package.json
│
├── LICENSE
└── README.md                   # <-- You are here
```

---

## Quick Start (Frontend)

```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:3000
```

The Vite dev server reads data from `backend/output/`, `backend/output2/`, and `backend/data/raw_data/` via custom middleware. No backend server needed.

---

## What Is Already Implemented

### Pages
- **Landing Page** — Hero with animated gradient title, live stats (recordings count, critical priority, whale detections, humpback signals), 5-stage pipeline diagram, 6-card feature overview, CTA navigation
- **Single Analysis** — File selector grid with score badges and tier borders, spectrogram viewer with audio playback, full analysis panel with charts
- **Batch Report** — Pipeline summary stats, tier distribution doughnut chart, score histogram, sortable/filterable report table, CSV export, row-click detail modal

### Spectrogram Viewer
- Zoom up to 5x via mouse wheel with zoom controls overlay
- Pan via click-and-drag when zoomed
- Hover shows time + frequency coordinates
- Toggle between cascade (4-panel) and basic (2-panel) spectrograms
- Red playhead synced with audio at all zoom levels

### Audio Player
- Play/pause with timeline scrubbing
- Volume slider
- Time display (current / total)
- Error handling when audio unavailable
- HTTP 206 range requests for proper seeking

### Event Timeline
- Auto-generated markers from cascade classifier outputs
- Color-coded: teal (multispecies), blue (humpback), green (YAMNet bio)
- Click-to-seek, hover tooltips with species + confidence

### Analysis Panel
- Biological importance score + tier badge
- 7-dimension scoring radar chart
- 3 classifier cards (YAMNet, Multispecies, Humpback) with detection status
- YAMNet horizontal bar chart (top audio classes)
- Multispecies + Humpback time series line charts
- 4-band frequency energy bar chart
- Annotation list

### Charts (Chart.js)
- Tier distribution (Doughnut)
- Score histogram (Bar)
- Scoring radar (Radar)
- YAMNet classes (horizontal Bar)
- Time series (Line)
- Band energy (Bar)

### Infrastructure
- Dark/Light theme toggle with localStorage persistence
- React 18 + React Router 6 + Vite 6
- CSS custom properties dual-theme system
- Responsive layout
- `.gitignore` configured

---

## What Still Needs Implementation

### High Priority (for the 3-minute demo)

1. **Confidence Heatmap Overlay** — Canvas overlay on spectrogram showing detection confidence as a color gradient by time region. Use the `time_series` arrays from `cascade_results.json` (multispecies and humpback scores per window) to paint semi-transparent colored regions over the spectrogram image.

2. **Audio Waveform Overlay** — Integrate [WaveSurfer.js](https://wavesurfer-js.org/) to show the audio waveform synced with the spectrogram. This gives a visual representation of amplitude alongside the frequency view.

3. **Keyboard Shortcuts** — Space = play/pause, Left/Right arrows = seek 5s, +/- = zoom in/out, Escape = close modal. Add a small help tooltip listing shortcuts.

4. **Loading States & Transitions** — Add skeleton loaders while data fetches, smooth page transitions, and loading spinners for heavy operations (CSV export, file switching).

### Medium Priority

5. **Species Frequency Chart** — Bar chart showing how many of the 100 recordings contain each detected species (Oo=Orca, Mn=Humpback, Eg=Right whale, Be=Beaked whale, Bp=Fin whale, Bm=Blue whale, Ba=Minke whale). Data available in `cascade_results.json` per-file multispecies scores.

6. **Temporal Pattern View** — Heatmap or timeline showing detection rates by hour of day. The filenames encode timestamps (e.g., `190806_3754` = Aug 6, 2019). Cross-reference with detection scores to show when biological activity peaks.

7. **Comparison Mode** — Side-by-side view of two recordings: two spectrograms, two analysis panels. Useful for comparing a CRITICAL-tier recording against a LOW-tier one during the demo.

8. **Bookmark/Flag System** — Let users mark recordings as "interesting" or "reviewed". Store in localStorage. Show flagged count in the batch report header.

9. **Folder Path Selector** — Input field on the landing page to specify a custom data directory. Currently paths are hardcoded in `vite.config.js`.

### Low Priority / Post-Hackathon

10. **Real-time Analysis Progress** — When a backend API exists, show a progress bar during batch processing with per-file status updates via WebSocket.

11. **PDF Report Export** — Generate a printable PDF for a single observation (spectrogram + all charts + score breakdown). Requires a backend endpoint or client-side PDF library like jsPDF.

12. **Acoustic Index Visualization** — Display soundscape indices (Shannon entropy, NDSI, ACI) if the backend computes them. These are standard ecological metrics for characterizing underwater sound environments.

13. **Multi-unit Support** — Currently shows Pilot deployment data. Extend to support Unit 6478 (96kHz) and Unit 5783 (144kHz) recordings. Requires running the backend pipeline on those units.

14. **XML Metadata Display** — Parse and show hydrophone metadata from `.log.xml` files: timestamps, water temperature, battery voltage, gain settings.

### Backend Hooks Needed

These API endpoints don't exist yet. The frontend is ready to consume them once the Python team implements them:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/analyze` | POST | Upload WAV, run pipeline, return JSON |
| `/api/analyze-batch` | POST | Run pipeline on a directory |
| `/api/status` | GET | Check processing status |
| `/api/files` | GET | List available audio files |
| `/api/events` | WebSocket | Real-time progress updates |
| `/api/export/pdf` | POST | Generate PDF report |

---

## For Frontend Teammates (Using Claude Opus 4.6)

### How to Start Working

1. Clone the repo and switch to the frontend branch
2. `cd frontend && npm install && npm run dev`
3. Read `frontend/FEATURE_STATUS.md` for the detailed per-file map
4. Pick a TODO item from the list above

### Prompt Template for Claude

When starting a session with Claude Opus 4.6, paste this context:

```
I'm working on the Dragon Ocean Analyzer frontend — a React 18 + Vite 6 marine
acoustic monitoring dashboard. The repo is organized as:
- backend/ — Python pipeline (cascade classifier, ranking), output data (JSON, PNG, WAV)
- frontend/ — React app with Chart.js, CSS custom properties theme system

Key data files the frontend reads:
- /api/output/analysis_results.json — band analysis, spectrograms, annotations for 100 recordings
- /api/output2/cascade_results.json — 3-stage classifier outputs (YAMNet, multispecies, humpback)
- /api/output2/ranked_biological_importance.json — scored + tiered rankings
- /api/output/*.png — spectrogram images
- /api/audio/*.wav — raw audio files

Read frontend/FEATURE_STATUS.md and frontend/README.md for the full implementation status.

My task is: [DESCRIBE YOUR TASK HERE]
```

### Coding Conventions

- **Styles:** All CSS in `src/styles.css` using CSS custom properties. Both `[data-theme="dark"]` and `[data-theme="light"]` must be maintained.
- **Data loading:** Use functions from `src/utils.js` (`loadRankedData`, `loadCascadeResults`, `loadAnalysisResults`, `loadFileAnnotation`).
- **Charts:** Use `react-chartjs-2` wrappers in `src/components/Charts.jsx`. Add new chart types there.
- **Config:** Species codes, tier thresholds, scoring dimensions are in `src/config.js`.
- **Components:** Each component is a single file in `src/components/`. Keep them self-contained.

### Branch Strategy

- `main` — stable, working version
- `feature/pages` — Landing, Single, Multiple page changes
- `feature/viz` — Charts, SpectrogramViewer, visualizations
- `feature/data` — Data loading, config, new data integrations

---

## Hackathon Context

- **Event:** SALA 2026 AI Hackathon
- **Location:** Galapagos / Latin America
- **Demo:** 3-minute presentation
- **Track:** Marine Acoustic Monitoring (code-focused direction)
- **Data source:** Galapagos Science Center hydrophones, Bay of San Cristobal
- **Biological content:** Unverified — the models detect signals but domain experts haven't confirmed animal presence in these specific recordings. This is expected and stated in the hackathon brief.
