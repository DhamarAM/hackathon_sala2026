# Frontend Audit & Implementation Guide

> **For frontend teammates using Claude Opus 4.6.**
> This document cross-references the hackathon problem brief, the actual backend data, and the current frontend code. It lists what's correct, what's wrong, and what to implement next.

---

## 1. Bugs & Data Mismatches (FIX FIRST)

### ✅ 1.1 `time_series` arrays — CORREGIDO

`top_time_series` (multispecies) y `time_series` (humpback) ahora se incluyen en `results.json`. El backend dejó de borrarlos del JSON consolidado. Los charts en `AnalysisPanel.jsx` y `SpectrogramViewer.jsx` renderizan correctamente cuando hay datos.

### 1.2 SPECIES_MAP is incomplete

**File:** `config.js` (lines 21-29)

The actual classes found in `cascade_results.json` are:
```
Species:      Bm, Bp, Eg, Mn, Oo
Vocalizations: Call, Echolocation, Gunshot, Upcall, Whistle
```

Our `SPECIES_MAP` includes `Ba` (Minke) and `Be` (Beaked) which are **never detected** in the data, and is **missing** the 5 vocalization type codes. The Google Multispecies model outputs 12 classes: 7 species + 5 vocalization types.

**Fix:** Update `SPECIES_MAP` in `config.js`:
```js
export const SPECIES_MAP = {
  Oo: 'Orcinus orca (Killer whale)',
  Mn: 'Megaptera novaeangliae (Humpback whale)',
  Eg: 'Eubalaena glacialis (Right whale)',
  Bp: 'Balaenoptera physalus (Fin whale)',
  Bm: 'Balaenoptera musculus (Blue whale)',
  Ba: 'Balaenoptera acutorostrata (Minke whale)',  // in model but not detected
  Be: 'Beaked whale',                               // in model but not detected
  Call: 'Whale call (vocalization)',
  Echolocation: 'Echolocation click',
  Gunshot: 'Gunshot call',
  Upcall: 'Upcall (right whale)',
  Whistle: 'Dolphin/whale whistle',
}
```

### 1.3 Feature cards claim "Identify 7 whale species"

**File:** `LandingPage.jsx` (line 96)

The model has 12 classes (7 species + 5 vocalizations). And the README says "12 whale/dolphin classes". Also, only 5 species ever appear in our 100-file dataset (Ba and Be were never detected).

**Fix:** Change to "Detect 12 whale and dolphin sound classes across 7 species using Google's multispecies classifier."

### 1.4 Frequency hover assumes 24kHz max

**File:** `SpectrogramViewer.jsx` (line 119)

The hover calculates frequency as `(1 - yRatio) * 24000 Hz`. The Pilot recordings are 48 kHz (Nyquist = 24 kHz), so this is **correct for Pilot data**. But if unit-6478 (96 kHz, Nyquist = 48 kHz) or unit-5783 (144 kHz, Nyquist = 72 kHz) recordings are ever added, this will be wrong.

**Fix (low priority):** Accept `sampleRate` as a prop and compute `(1 - yRatio) * sampleRate / 2`.

### 1.5 Audio only works for ONE file

**File:** `SpectrogramViewer.jsx` (line 300)

There's only one WAV file in the dataset: `190806_3754.wav` (15.9 seconds). The other 99 recordings don't have WAV files in our repo. The error message says this but it could be more helpful for the demo.

**Fix:** For the demo, consider preloading the one working file and making it clear in the UI that this is a sample. Also consider downloading more files from the dataset (the `marine-acoustic-core` subset has 123 WAVs, ~7.3 GB).

---

## 2. Conceptual Inaccuracies to Fix

### 2.1 "Biological content is unverified" — we don't state this

The hackathon README heavily emphasizes: *"The domain experts have not yet confirmed the presence of marine animal sounds in these specific recordings."* Our frontend presents classifier results as if they're confirmed detections ("Whale Detected", "Humpback Signals", "Critical Priority").

**Fix:** Add a disclaimer banner or footnote:
> "Detection scores are from pretrained AI models. Biological content has not been verified by domain experts. High scores indicate acoustic patterns consistent with species vocalizations."

This is important for the pitch — it shows scientific rigor and honesty, which judges would value.

### ✅ 2.2 Cascade pipeline stage names — CORREGIDO

`PipelineDiagram.jsx` actualizado. Stages actuales:
1. SoundTrap Collection
2. Audio Segmentation (Stage 0 — silence filter)
3. AI Cascade Classifier (Stages 1-3 — YAMNet → Multispecies → Humpback)
4. Soundscape & Clustering (Stages 5-6 — NDSI + UMAP/HDBSCAN)
5. Ranking & Report (Stage 4 — 9-dimension scoring)

### 2.3 Band frequency ranges in context

**File:** `config.js` (lines 41-46)

Our bands are: `infrasonic_whales (10-100 Hz)`, `low_freq_fish (50-500 Hz)`, `mid_freq_dolphins (500-5000 Hz)`, `high_freq_clicks (5-24 kHz)`.

The hackathon README defines different bands: `LOW (50-2000 Hz, boats and fish)`, `MID (2-10 kHz, shrimp and dolphins)`, `HIGH (>10 kHz, echolocation)`.

These are **not contradictory** — our bands come from the backend `analyze_marine_audio.py` which uses more specific marine-acoustic ranges. But we should mention in the UI or pitch that our band definitions are more granular than standard acoustic ecology bands, specifically designed for marine mammal detection.

---

## 3. Missing Features — Prioritized for 3-Minute Demo

### MUST HAVE (will make the demo impressive)

#### 3.1 Species Detection Summary Chart
A bar chart showing detection counts across all 100 files: how many files contain each class code (Oo, Mn, Echolocation, etc.). Quick to implement — aggregate from `cascade_results.json`.

**Where:** Add to `LandingPage.jsx` or `MultipleObservations.jsx`
**Data:** Loop through all files in cascade_results, count detections by class_code.

#### 3.2 Fix the Multispecies Detections Display
Currently the AnalysisPanel shows `top_species` and `top_max_score`, but doesn't list ALL detections for a file. The data has a `detections` array with multiple species per file.

**Where:** `AnalysisPanel.jsx`, Stage 2 classifier card (line 71-87)
**Fix:** Show all detections, not just the top. E.g.:
```
Mn (Humpback): max 3.8%, mean 1.4%
Oo (Orca): max 3.3%, mean 1.4%
Echolocation: max 10.8%, mean 0.6%
```

#### 3.3 Disclaimer / Context Banner
Show the scientific context: unverified data, tool-focused approach, Galapagos Marine Reserve.

**Where:** Navbar or landing page subtitle
**Why:** Judges score "Impact & Relevance" at 25%. Showing we understand the limitations is key.

### SHOULD HAVE (adds depth to the demo)

#### 3.4 Temporal Patterns (hour-of-day / date analysis)
Pilot filenames encode timestamps: `YYMMDD_sequence`. Parse them to show detection patterns by date. Do detections cluster on certain days?

**Where:** New chart in `MultipleObservations.jsx` or a new "Patterns" tab
**Data:** Parse filenames from rankings, cross-reference with cascade data.

#### 3.5 Comparison View
Side-by-side comparison of a CRITICAL file vs. a MINIMAL file. Very powerful for demo: "Look at the difference between a high-priority and low-priority recording."

**Where:** New component or mode in `SingleObservation.jsx`

#### 3.6 Acoustic Indices from the README
The hackathon README suggests computing: Shannon entropy, NDSI (bio vs human noise ratio), acoustic diversity index. If the backend computed these, display them. If not, at least mention them as "planned" in the pitch.

**Where:** New section in `AnalysisPanel.jsx`
**Note:** The README warns that default `scikit-maad` frequency ranges are for forests, not ocean. Our custom bands are already more appropriate.

### NICE TO HAVE (if time permits)

#### 3.7 Keyboard Shortcuts
Space = play/pause, arrows = seek, +/- = zoom.

#### 3.8 WaveSurfer.js Waveform
Audio waveform visualization synced with spectrogram.

#### 3.9 More Audio Files
Download `marine-acoustic-colab` subset (425 MB, 11 WAVs) to demo audio playback on more than 1 file.

---

## 4. Pitch Strategy Notes (Judging Criteria)

The judges evaluate:
- **Originality & Innovation (30%):** Our cascade pipeline approach + biological ranking is novel. Emphasize the 7-dimension scoring system.
- **Technical Execution (30%):** Show the full frontend with real data flowing through. Fix the bugs above so nothing looks broken during the demo.
- **Impact & Relevance (25%):** Frame it as "a tool for marine biologists" — the platform prioritizes which of 926 recordings to manually review. That's a real workflow need.
- **Presentation & Clarity (15%):** 3 minutes, 5 slides max. The frontend IS the prototype/MVP shown in slide 4.

### Demo Flow Suggestion (3 minutes)
1. **(30s)** Problem: 926 underwater recordings, no labels, biologists need help prioritizing what to listen to.
2. **(30s)** Our solution: 3-stage cascade AI pipeline + biological importance ranking.
3. **(60s)** Live demo: Landing page → Batch report (sort by tier, show CRITICAL files) → Click into a CRITICAL file → Show spectrogram, classifier results, radar chart → Play audio.
4. **(30s)** Results: 3 CRITICAL, 35 HIGH priority recordings identified out of 100. 61 files with whale species detections. 99 files with humpback-consistent signals.
5. **(30s)** Future: Scale to full 926 files, add acoustic indices, real-time processing, domain expert validation workflow.

---

## 5. Data Quick Reference

### Available data (in `outputs/`)

| Ruta API | Archivo local | Key fields |
|----------|--------------|------------|
| `/api/pipeline/analysis/results.json` | `outputs/analysis/results.json` | total_files, bio_signals, whale_detected, humpback_detected, files{} |
| `/api/pipeline/ranking/ranked.json` | `outputs/ranking/ranked.json` | total_ranked, tier_distribution, rankings[] |
| `/api/pipeline/ranking/ranked.csv` | `outputs/ranking/ranked.csv` | CSV con 9 componentes + tier |
| `/api/pipeline/analysis/spectrograms/*.png` | `outputs/analysis/spectrograms/` | Espectrogramas 4-panel (cascade) |
| `/api/pipeline/analysis/annotations/*_cascade.json` | `outputs/analysis/annotations/` | Resultado completo por clip |
| `/api/audio/*.wav` | `backend/data/raw_data/` | WAV files (HTTP 206 range) |

### Thresholds actuales
- `HUMPBACK_THRESHOLD = 0.3` (subido desde 0.1 para reducir FP)
- `MULTISPECIES_DETECTION_THR = 0.10` (activa flag `whale_species`)
- `MULTISPECIES_THRESHOLD = 0.01` (lista detecciones en el array)

### Clases detectadas en el dataset
`Bm, Bp, Call, Echolocation, Eg, Gunshot, Mn, Oo, Upcall, Whistle`
(Ba y Be nunca aparecen en estos datos)

---

## 6. Frontend File Map

```
frontend/src/
├── main.jsx              # Entry point
├── App.jsx               # Router + layout shell
├── config.js             # API paths, tier config, species map, scoring dimensions
├── utils.js              # Data loaders (loadRankedData, loadCascadeResults, etc.), CSV export
├── styles.css            # All styles (dark+light themes, CSS custom properties)
├── context/
│   └── ThemeContext.jsx   # Dark/light toggle with localStorage
├── pages/
│   ├── LandingPage.jsx
│   ├── SingleObservation.jsx
│   └── MultipleObservations.jsx
└── components/
    ├── Navbar.jsx
    ├── Sidebar.jsx
    ├── PipelineDiagram.jsx
    ├── SpectrogramViewer.jsx   # Zoom, pan, audio player, event timeline
    ├── Charts.jsx              # Doughnut, Bar, Line, Radar (react-chartjs-2)
    ├── ReportTable.jsx         # Sort, filter, search, CSV export
    ├── AnalysisPanel.jsx       # Score, radar, 3 classifier cards, charts
    ├── DetailModal.jsx
    └── TierBadge.jsx
```

## 7. Prompt para Claude (Frontend)

```
Trabajo en el frontend de "Dragon Ocean Analyzer" — React 18 + Vite 6,
hackathon SALA 2026 (Galápagos Marine Reserve).

LEE PRIMERO: docs/PROJECT_OVERVIEW.md (contexto completo, schemas, API routes)
LUEGO LEE: docs/FRONTEND_AUDIT.md (bugs pendientes, TODO features, file map)

BUGS PENDIENTES (abiertos):
- SPECIES_MAP falta 5 clases de vocalización (Call, Echolocation, Gunshot, Upcall, Whistle)
- Falta disclaimer "contenido biológico no verificado"

BUGS YA CORREGIDOS (no tocar):
- time_series ya existe en results.json
- API routes ya apuntan a /api/pipeline/*
- cross_model_agreement → cross_model en SCORING_DIMENSIONS
- PipelineDiagram refleja el pipeline real

STYLE: CSS custom properties en src/styles.css, dark+light themes.
CHARTS: react-chartjs-2, nuevos charts van en src/components/Charts.jsx.
DATA: usar funciones de src/utils.js (loadRankedData, loadCascadeResults, loadFileAnnotation).

Mi tarea es: [DESCRIBE]
```
