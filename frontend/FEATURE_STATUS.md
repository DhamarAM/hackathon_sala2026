# Feature Status — Dragon Ocean Analyzer

> **Last updated:** 2026-03-10
> **Repo structure:** `backend/` (Python pipeline) · `frontend/` (React UI)

---

## ✅ Implemented

| Area | Feature | Notes |
|------|---------|-------|
| Landing Page | Hero with 72px title, stats, pipeline diagram, feature cards | Loads live data from output/ |
| Theme | Dark/Light toggle with localStorage persistence | CSS variables in `styles.css` |
| Navigation | Navbar + collapsible sidebar | Links: Single Analysis, Batch Report |
| Batch Report | Report table (sort, filter, search), CSV export, detail modal | `MultipleObservations.jsx` |
| Batch Report | Tier doughnut chart, score histogram | Chart.js |
| Single Analysis | File selector grid, split layout (spectrogram + analysis) | `SingleObservation.jsx` |
| Spectrogram | Zoom (wheel, up to 5x), pan (drag), hover info | `SpectrogramViewer.jsx` |
| Audio | Play/pause, volume, scrub, time display, error states | Range requests via Vite middleware |
| Event Timeline | Auto-generated markers from cascade data, click-to-seek, tooltips | Color-coded by classifier stage |
| Analysis Panel | Score+tier, radar chart, 3 classifier cards, YAMNet bars, time series, band energy, annotations | `AnalysisPanel.jsx` |
| Infra | Vite middleware serves JSON/PNG/WAV, HTTP 206 range requests | `vite.config.js` |

## 🔧 TODO — Needs Implementation

> **Teammates: pick items below and create a branch `feature/<name>`**

### HIGH PRIORITY (for demo)
- [ ] **Confidence Heatmap** — Canvas overlay on spectrogram showing detection confidence by time region *(Person B)*
- [ ] **Audio Waveform Overlay** — WaveSurfer.js waveform visualization synced with spectrogram *(Person B)*
- [ ] **Keyboard Shortcuts** — Space=play/pause, arrows=seek, +/-=zoom *(anyone)*

### MEDIUM PRIORITY
- [ ] **Species Frequency Chart** — Bar chart: how many recordings per species *(Person B)*
- [ ] **Folder Path Selector** — Input to set custom data directory path *(Person A)*
- [ ] **Comparison Mode** — Side-by-side view of two recordings *(Person A)*
- [ ] **Bookmark/Flag System** — Mark recordings for review *(Person A)*

### BACKEND HOOKS NEEDED
> These require Python endpoints in `backend/`. Frontend is ready to consume them.

- [ ] `POST /api/analyze` — Upload WAV → run pipeline → return JSON
- [ ] `POST /api/analyze-batch` — Batch analysis on a directory
- [ ] `GET /api/status` — Processing status check
- [ ] `GET /api/files` — List available audio files
- [ ] `WebSocket /api/events` — Real-time progress during batch
- [ ] `POST /api/export/pdf` — PDF report generation

## 📂 Frontend File Map

```
frontend/
├── src/
│   ├── main.jsx              # Entry point
│   ├── App.jsx               # Router + layout shell
│   ├── config.js             # API paths, tier config, species map
│   ├── utils.js              # Data loaders, CSV export
│   ├── styles.css            # All styles (dark+light themes)
│   ├── context/
│   │   └── ThemeContext.jsx   # Dark/light toggle provider
│   ├── pages/
│   │   ├── LandingPage.jsx       # Person A
│   │   ├── SingleObservation.jsx # Person A
│   │   └── MultipleObservations.jsx # Person A
│   └── components/
│       ├── Navbar.jsx            # Person A
│       ├── Sidebar.jsx           # Person A
│       ├── PipelineDiagram.jsx   # Person B
│       ├── SpectrogramViewer.jsx # Person B
│       ├── Charts.jsx            # Person B
│       ├── ReportTable.jsx       # Person B
│       ├── AnalysisPanel.jsx     # Person B
│       ├── DetailModal.jsx       # Person A
│       └── TierBadge.jsx         # shared
├── vite.config.js        # Dev server + data middleware
├── package.json
└── index.html
```

## 🚀 Quick Start

```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:3000
```

Data served from: `../output/`, `../output2/`, `../backend/data/raw_data/`
