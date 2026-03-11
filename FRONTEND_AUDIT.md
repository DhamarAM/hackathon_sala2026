# Frontend Audit & Implementation Guide

> **For frontend teammates using Claude Opus 4.6.**
> This document cross-references the hackathon problem brief, the actual backend data, and the current frontend code. It lists what's correct, what's wrong, and what to implement next.

---

## 1. Bugs & Data Mismatches (FIX FIRST)

### 1.1 `time_series` arrays DO NOT EXIST in the data

**Files affected:** `SpectrogramViewer.jsx` (lines 142-166), `AnalysisPanel.jsx` (lines 113-129), `Charts.jsx` (TimeSeriesChart)

The code references `cascade.stage2_multispecies.top_time_series` and `cascade.stage3_humpback.time_series`. These fields **do not exist** in `cascade_results.json`. The actual data structure per file is:

```json
"stage2_multispecies": {
  "detections": [...],        // array of {class_code, species, max_score, mean_score}
  "num_windows": 3,
  "top_species": "Mn",
  "top_species_name": "...",
  "top_max_score": 0.038,
  "any_whale_detected": false
}

"stage3_humpback": {
  "max_score": 0.067,
  "mean_score": 0.014,
  "fraction_above_threshold": 0.0,
  "num_windows": 13,
  "humpback_detected": false
}
```

**Impact:**
- The Time Series charts in AnalysisPanel **never render** (the conditional checks fail silently).
- The event timeline in SpectrogramViewer is **always empty** for multispecies and humpback markers.
- Only YAMNet bio markers can appear (at a fixed 50% position, which is also incorrect).

**Fix options:**
- **Option A (realistic):** Remove the time series charts and event markers since the data doesn't have per-window scores. Replace with a summary visualization of the aggregate scores per file.
- **Option B (generate data):** Modify the backend (`cascade_classifier.py`) to output per-window time series. This would require the backend team.
- **Option C (simulate for demo):** Generate synthetic time series from `num_windows` + `max_score` + `mean_score` to show that the visualization works. Label it clearly as "simulated resolution" in the UI.

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

### 2.2 Cascade pipeline stage names need Precision

**File:** `PipelineDiagram.jsx`

Current stages shown: `SoundTrap Collection → Signal Processing → AI Cascade Classifier → Ensemble Voting → Ranking & Report`

More accurate based on the actual code:
1. **SoundTrap ST300 Recording** (hydrophone capture)
2. **Audio Analysis** (band decomposition, transient detection, spectrogram generation)
3. **YAMNet** (521-class general audio, bio signal gating)
4. **Google Multispecies / Humpback** (12 whale classes + binary humpback)
5. **Biological Importance Ranking** (7-dimension scored ranking, 5 tiers)

The current diagram compresses stages 3-4 into one box and adds "Ensemble Voting" which is not exactly what happens — it's a cascade (sequential gates), not an ensemble (parallel voters).

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

### Available data (in `backend/`)

| File | Records | Key fields |
|------|---------|------------|
| `output/analysis_results.json` | 100 files | band_analysis (4 bands), annotations, spectrogram filename, duration, sample_rate |
| `output2/cascade_results.json` | 100 files | stage1_yamnet (top_classes, bio/marine/noise_detections), stage2_multispecies (detections array, any_whale_detected), stage3_humpback (max/mean_score, fraction_above_threshold) |
| `output2/ranked_importance.json` | 100 rankings | score, tier, 7 components, cascade_flags, top_species |
| `output/spectrograms/*.png` | 100 images | Basic spectrograms (2-panel) |
| `output2/spectrograms/*.png` | 100 images | Cascade spectrograms (4-panel) |
| `output/annotations/*.json` | 100 files | Same as analysis_results per-file data |
| `output2/annotations/*.json` | 100 files | Same as cascade_results per-file data |
| `data/raw_data/190806_3754.wav` | 1 file | 15.9s, 48kHz, only audio available |

### Tier distribution (from ranked_importance.json)
- CRITICAL (>=65): **3 files**
- HIGH (>=45): **35 files**
- MODERATE (>=25): **40 files**
- LOW (>=10): **19 files**
- MINIMAL (<10): **3 files**

### Detection statistics
- YAMNet bio signals: **70 / 100 files**
- Whale species detected (any_whale_detected=true): **61 / 100 files**
- Humpback detected: **99 / 100 files** (note: model may be over-sensitive)
- Unique class codes in data: `Bm, Bp, Call, Echolocation, Eg, Gunshot, Mn, Oo, Upcall, Whistle`

---

## 6. Frontend File Map

```
frontend/src/
├── main.jsx              # Entry point
├── App.jsx               # Router + layout shell
├── config.js             # API paths, tier config, species map, scoring dimensions, band config
├── utils.js              # Data loaders (loadRankedData, loadCascadeResults, etc.), CSV export
├── styles.css            # All styles (dark+light themes, CSS custom properties)
├── context/
│   └── ThemeContext.jsx   # Dark/light toggle with localStorage
├── pages/
│   ├── LandingPage.jsx
│   ├── SingleObservation.jsx
│   └── MultipleObservations.jsx
└── components/
    ├── Icons.jsx               # Inline SVG icons (no emoji, no external deps)
    ├── Navbar.jsx
    ├── Sidebar.jsx
    ├── PipelineDiagram.jsx
    ├── SpectrogramViewer.jsx   # Zoom, pan, audio player, event timeline, keyboard shortcuts
    ├── Charts.jsx              # Doughnut, Bar, Line, Radar, SpeciesDetection (react-chartjs-2)
    ├── ReportTable.jsx         # Sort, filter, search, CSV export
    ├── AnalysisPanel.jsx       # Score, radar, 3 classifier cards, all detections, charts
    ├── DetailModal.jsx
    └── TierBadge.jsx
```

## 7. Claude Opus 4.6 Prompt for Frontend Teammates

```
Trabajo en el frontend de "Dragon Ocean Analyzer" — React 18 + Vite 6,
hackathon SALA 2026 (Galápagos Marine Reserve).

LEE PRIMERO: PROJECT_OVERVIEW.md (contexto completo, schemas, API routes)
LUEGO LEE: FRONTEND_AUDIT.md (bugs, TODO features, file map)

BUGS CLAVE:
1. time_series NO existe en cascade_results.json — código que lo usa está roto
2. SPECIES_MAP falta 5 clases de vocalización (Call, Echolocation, etc.)
3. Falta disclaimer "contenido biológico no verificado"
4. Solo 1 WAV existe (190806_3754.wav)

STYLE: CSS custom properties en src/styles.css, dark+light themes.
CHARTS: react-chartjs-2, nuevos charts van en src/components/Charts.jsx.
DATA: usar funciones de src/utils.js.

Mi tarea es: [DESCRIBE]
```
