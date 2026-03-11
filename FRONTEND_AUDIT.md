# Frontend Audit & Implementation Guide

> **For frontend teammates using Claude Opus 4.6.**
> This document cross-references the hackathon problem brief, the actual backend data, and the current frontend code. It lists what's correct, what's wrong, and what to implement next.
>
> **Last updated: 2026-03-10** — Marked implemented items.

---

## 1. Bugs & Data Mismatches

### 1.1 `time_series` arrays — RESOLVED

**Status:** WORKAROUND FOUND

The consolidated `cascade_results.json` has `time_series` deleted (backend bug — see BACKEND_AUDIT.md §1.1). However, the individual annotation JSONs (`output2/annotations/*_cascade.json`) **DO** have `top_time_series` and `time_series`. Since the frontend loads per-file data via `loadFileAnnotation()` → individual JSONs, the time series charts and event markers now **work correctly**.

No frontend fix needed. Backend team should still stop deleting these fields from the consolidated JSON.

### 1.2 SPECIES_MAP — IMPLEMENTED

`config.js` now includes all 12 classes (7 species + 5 vocalizations) with scientific context:
```js
Echolocation: 'Echolocation click (odontocetes)',
Gunshot: 'Gunshot call (right whale surface)',
Upcall: 'Upcall (right whale contact call)',
Whistle: 'Whistle (tonal FM)',
```

### 1.3 Feature cards "Identify 7 whale species" — IMPLEMENTED

Changed to "Detect 12 whale and dolphin sound classes across 7 species."

### 1.4 Frequency hover assumes 24kHz max — IMPLEMENTED

`SpectrogramViewer.jsx` now accepts `sampleRate` prop (default 48000). Frequency hover computes `(1 - yRatio) * sampleRate / 2`. Passed from `SingleObservation.jsx` and `DetailModal.jsx` using `cascade?.sample_rate || basic?.sample_rate || 48000`.

### 1.5 Audio only works for ONE file — IMPLEMENTED

- 4 WAV files now available (3 CRITICAL + 1 original), stored outside repo at `SALA/data/audio/`
- On-demand download from R2 cloud storage: when user selects a file without audio, the UI shows "Audio not available locally" with a "Download from cloud" button
- Download triggers `backend/download_audio.py` via Vite middleware → fetches from Cloudflare R2
- Auto-reloads audio element after download completes

---

## 2. Conceptual Inaccuracies — ALL IMPLEMENTED

### 2.1 Disclaimer banner — IMPLEMENTED

Added professional disclaimer in subtle accent style (not yellow warning):
> "Automated analysis using pretrained AI models. High scores indicate acoustic patterns consistent with species vocalizations, not confirmed presence."

Applied to: LandingPage hero, AnalysisPanel footer, MultipleObservations footnote. CSS class `disclaimer-banner` uses `var(--accent-bg)` + italic.

### 2.2 Pipeline stage names — IMPLEMENTED

`PipelineDiagram.jsx` updated with precise 5-stage names matching the actual pipeline.

### 2.3 Band frequency context — IMPLEMENTED

`config.js` `BAND_CONFIG` now has `note` fields:
```js
infrasonic_whales: { note: 'Mysticete moans (bio range extends to 4 kHz)' },
high_freq_clicks:  { note: 'Limited by 48 kHz Pilot SR (Nyquist = 24 kHz)' },
```

---

## 3. Missing Features — Status

### MUST HAVE

| Feature | Status | Notes |
|---------|--------|-------|
| 3.1 Species Detection Summary Chart | IMPLEMENTED | `Charts.jsx` SpeciesDetectionChart, shown in MultipleObservations |
| 3.2 All Multispecies Detections | IMPLEMENTED | AnalysisPanel shows full detection list with class codes, species names, scores |
| 3.3 Disclaimer / Context Banner | IMPLEMENTED | See §2.1 above |

### SHOULD HAVE

| Feature | Status | Notes |
|---------|--------|-------|
| 3.4 Temporal Patterns | NOT DONE | Could parse timestamps from filenames for hour-of-day chart |
| 3.5 Comparison View | NOT DONE | Side-by-side CRITICAL vs MINIMAL |
| 3.6 Acoustic Indices | NOT DONE | Backend doesn't compute these |

### NICE TO HAVE

| Feature | Status | Notes |
|---------|--------|-------|
| 3.7 Keyboard Shortcuts | IMPLEMENTED | Space=play/pause, arrows=seek ±5s, +/-=zoom |
| 3.8 WaveSurfer.js | NOT DONE | Using native audio + clean spectrogram overlay instead |
| 3.9 More Audio Files | IMPLEMENTED | On-demand R2 download system |

---

## 4. Additional Changes (this session)

### 4.1 All emojis replaced with inline SVG icons
Created `Icons.jsx` with 15 SVG components (zero external deps): IconWave, IconSpectrum, IconSearch, IconWhale, IconRanking, IconHeadphones, IconBrain, IconExport, IconVolumeHigh, IconVolumeMute, IconHome, IconWaveform, IconList, IconUpload, IconBarChart.

Updated: PipelineDiagram, LandingPage, SpectrogramViewer, Sidebar, Navbar, SingleObservation.

### 4.2 "Critical Priority" renamed to "High Bio-Interest"
Landing page stat card renamed with subtitle "Score >= 65" for clarity.

### 4.3 Sidebar labels renamed
"Single Observation" → "Single Analysis", "Multiple Observations" → "Batch Report"

### 4.4 Navbar theme toggle
Sun/Moon emoji → SVG SunIcon/MoonIcon. Hamburger → SVG MenuIcon.

### 4.5 Clean spectrograms for audio overlay
`generate_clean_spectrograms.py` (backend) produces 200 heatmap-only PNGs in `output/spectrograms_clean/`. Served via `/api/clean-spectrogram/` endpoint. Available in config as `API.cleanSpectrogram(filename)`.

### 4.6 Audio download system
Frontend flows:
1. `API.audioStatus(filename)` → `{ exists: bool, downloading: bool }`
2. `API.audioDownload(filename)` → triggers R2 download, returns `{ status: 'ready'|'downloading'|'error' }`
3. SpectrogramViewer shows status bar with spinner or "Download from cloud" button

### 4.7 CSS additions
- `.audio-status-bar` — download indicator in SpectrogramViewer
- `.btn-sm` — small button variant
- `.play-btn:disabled` — disabled state for play button
- `.disclaimer-banner` — professional subtle disclaimer
- `.detection-list`, `.detection-item`, related classes — AnalysisPanel detections layout
- `.species-chart-legend`, `.species-chart-legend-item` — chart legend

---

## 5. Data Quick Reference

### Available data (in `backend/`)

| File | Records | Key fields |
|------|---------|------------|
| `output/analysis_results.json` | 100 files | band_analysis, annotations, spectrogram filename, duration, sample_rate |
| `output2/cascade_results.json` | 100 files | stage1_yamnet, stage2_multispecies, stage3_humpback (WITHOUT time_series) |
| `output2/ranked_importance.json` | 100 rankings | score, tier, 7 components, cascade_flags, top_species |
| `output/spectrograms/*.png` | 100 | Basic spectrograms (2-panel, 1680x960) |
| `output2/spectrograms/*.png` | 100 | Cascade spectrograms (4-panel, 1920x1680) |
| `output/spectrograms_clean/*.png` | 200 | Heatmap-only crops (variable size, edge-to-edge time) |
| `output/annotations/*.json` | 100 | Per-file data (HAS time_series) |
| `output2/annotations/*.json` | 100 | Per-file cascade data (HAS time_series) |
| `SALA/data/audio/*.wav` | 4 | EXTERNAL — outside repo, on-demand R2 download |

### Tier distribution
- CRITICAL (>=65): **3 files**
- HIGH (>=45): **35 files**
- MODERATE (>=25): **40 files**
- LOW (>=10): **19 files**
- MINIMAL (<10): **3 files**

---

## 6. Frontend File Map

```
frontend/
├── vite.config.js           # Middleware: serves output, audio, clean spectrograms; on-demand download
├── src/
│   ├── main.jsx             # Entry point
│   ├── App.jsx              # Router + layout shell
│   ├── config.js            # API paths, tier config, species map, band config, scoring dims
│   ├── utils.js             # Data loaders, CSV export, formatters
│   ├── styles.css           # All styles (dark+light themes, CSS custom properties)
│   ├── context/
│   │   └── ThemeContext.jsx  # Dark/light toggle with localStorage
│   ├── pages/
│   │   ├── LandingPage.jsx          # Hero, stats, pipeline, features, disclaimer
│   │   ├── SingleObservation.jsx    # File picker, upload, spectrogram+analysis view
│   │   └── MultipleObservations.jsx # Report table, charts, species summary
│   └── components/
│       ├── Icons.jsx              # 15 inline SVG icons (no emoji, no external deps)
│       ├── Navbar.jsx             # SVG theme toggle, SVG menu button
│       ├── Sidebar.jsx            # SVG nav icons, renamed labels
│       ├── PipelineDiagram.jsx    # SVG stage icons, 5 stages
│       ├── SpectrogramViewer.jsx  # Zoom, pan, audio, download indicator, keyboard shortcuts
│       ├── Charts.jsx             # Doughnut, Bar, Line, Radar, SpeciesDetection
│       ├── ReportTable.jsx        # Sort, filter, search, CSV export
│       ├── AnalysisPanel.jsx      # Score, radar, 3 classifiers, all detections, disclaimer
│       ├── DetailModal.jsx        # Modal wrapper for file detail
│       └── TierBadge.jsx          # Tier color badge
```
