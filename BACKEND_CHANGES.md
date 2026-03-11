# Backend Changes — Review Before Merge

> **Author:** Frontend/integration team (Claude-assisted)
> **Date:** 2026-03-10
> **Purpose:** Document all backend changes for the backend team to review.
> These changes focused on enabling audio playback in the frontend, reorganizing
> the folder structure, and generating clean spectrograms. The pipeline scripts
> themselves were NOT modified — only moved. Internal references still need updating.

---

## 1. FILE MOVES (reorganization)

### Before → After

| Before | After | Notes |
|--------|-------|-------|
| `analyze_marine_audio.py` | `pipeline/analyze_marine_audio.py` | Core pipeline script |
| `cascade_classifier.py` | `pipeline/cascade_classifier.py` | Core pipeline script |
| `rank_biological_importance.py` | `pipeline/rank_biological_importance.py` | Core pipeline script |
| `src/audio_tester.py` | `utils/audio_tester.py` | Helper utility |
| `src/categorize_audio.py` | `utils/categorize_audio.py` | Helper utility |
| `src/clip_audio.py` | `utils/clip_audio.py` | Helper utility |
| `src/explore_sample.py` | `utils/explore_sample.py` | Helper utility |
| `src/tester.py` | `utils/tester.py` | Helper utility |
| `r2_download.py` | `utils/r2_download.py` | R2 cloud download |
| `r2_manifest_template.json` | `utils/r2_manifest_template.json` | Manifest template |
| `CASCADE_PIPELINE.md` | `docs/CASCADE_PIPELINE.md` | Documentation |
| `RANKING_METHODOLOGY.md` | `docs/RANKING_METHODOLOGY.md` | Documentation |
| `README master - Colaborator 2.md` | `docs/README master - Colaborator 2.md` | Documentation |
| `data_download.ipynb` | `docs/data_download.ipynb` | Reference notebook |
| `src/marine-acoustic-monitoring/` | `docs/hackathon-reference/` | Hackathon starter code |

### Deleted
| Path | Reason |
|------|--------|
| `.idea/` | IDE config — should not be in repo |
| `src/__pycache__/` | Python cache — should not be in repo |
| `src/__init__.py` | Empty file, no longer needed |
| `src/` (directory) | Emptied, removed |

### Unchanged (stayed in place)
- `output/` — analysis results, spectrograms, annotations (used by frontend)
- `output2/` — cascade results, spectrograms, annotations (used by frontend)

---

## 2. NEW FILES

### `run_pipeline.py`
Orchestrator script that runs the 3 pipeline stages in sequence.
```
python run_pipeline.py [--skip-stage1] [--skip-stage2] [--skip-stage3] [--skip-clean]
```
Calls: `pipeline/analyze_marine_audio.py` → `pipeline/cascade_classifier.py` → `pipeline/rank_biological_importance.py` → `generate_clean_spectrograms.py`

### `generate_clean_spectrograms.py`
Crops the matplotlib composite spectrogram PNGs to extract ONLY the top-panel heatmap content (removes axis tick labels, colorbar, subsidiary charts, titles).

**Why:** The frontend needs clean edge-to-edge heatmap images for synchronized audio cursor/slider overlay. The original PNGs have charts and labels that break the time↔pixel mapping.

**How it works:**
- Detects the matplotlib axes frame per-image using the `gray(212) → black(0) → content` border pattern
- Handles variable left boundaries (y-axis label width differs per image)
- Skips the colorbar strip on the right (detects narrow content regions < 80px)
- Input: `output/spectrograms/*.png` (1680×960) and `output2/spectrograms/*.png` (1920×1680)
- Output: `output/spectrograms_clean/*_clean.png`
- Produces 200 images (100 basic + 100 cascade)

### `download_audio.py`
Downloads individual WAV files on-demand from Cloudflare R2 cloud storage.
Called by the frontend Vite dev server when a user requests audio that isn't available locally.

**Important:** WAV files are stored OUTSIDE the repo at `SALA/data/audio/` (not in `hackathon_sala2026/`) because the full dataset is 20+ GB and should not be committed.

Path resolution: `REPO_ROOT.parent.parent / "data" / "audio"` → `SALA/data/audio/`

R2 credentials are hardcoded as defaults for the hackathon (from `participant-download.env`), overridable via environment variables.

### `requirements.txt`
```
numpy>=1.24
librosa>=0.10
matplotlib>=3.7
scipy>=1.10
soundfile>=0.12
tensorflow>=2.12
tensorflow_hub>=0.13
boto3>=1.28
Pillow>=9.5
```

### `.gitignore`
Ignores: `__pycache__/`, `.idea/`, `.env`, `data/`, `*.wav`, IDE files, OS files.

---

## 3. STALE REFERENCES IN PIPELINE SCRIPTS (NOT YET FIXED)

The pipeline scripts were MOVED but their internal path references were intentionally left unchanged for backend team review. These need updating once the team approves the new structure:

### `pipeline/cascade_classifier.py`
```python
# Line 39-40 — INPUT_DIR points to nonexistent folder
INPUT_DIR = Path("Music_Soundtrap_Pilot")   # ← needs updating
OUTPUT_DIR = Path("output2")                  # ← relative to CWD, works if run from backend/
```

### `pipeline/analyze_marine_audio.py`
```python
# Line 25-26
INPUT_DIR = Path("Music_Soundtrap_Pilot")   # ← needs updating
OUTPUT_DIR = Path("output")                   # ← relative to CWD, works if run from backend/
```

### `pipeline/rank_biological_importance.py`
```python
# Line 38-40
RESULTS_FILE = Path("output2/cascade_results.json")    # ← relative to CWD
OUTPUT_JSON = Path("output2/ranked_importance.json")
OUTPUT_CSV = Path("output2/ranked_importance.csv")
```

**Recommended fix:** Make all paths relative to the script's own location:
```python
BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
INPUT_DIR = BACKEND_DIR.parent.parent.parent / "data" / "audio"  # SALA/data/audio/
OUTPUT_DIR = BACKEND_DIR / "output2"
```

Or accept them as CLI arguments via argparse (the `run_pipeline.py` coordinator could pass them).

**Note:** `INPUT_DIR = "Music_Soundtrap_Pilot"` was ALREADY a bug before our changes — this path never existed in the repo. See BACKEND_AUDIT.md §1.2.

---

## 4. OTHER KNOWN BUGS (from BACKEND_AUDIT.md, NOT fixed)

These bugs were documented but intentionally left for the backend team:

1. **`time_series` deleted before saving** — `cascade_classifier.py` L544-549 pops `top_time_series` and `time_series` from consolidated JSON. Frontend works around this by loading individual annotation JSONs which DO have the data.

2. **`'speech'`/`'music'`/`'singing'` in YAMNET_BIO_KEYWORDS** — inflates bio detection counts. 21/100 files have "Speech" as a biological detection.

3. **Cascade doesn't actually cascade** — all 3 models run unconditionally regardless of stage 1 result.

4. **`HUMPBACK_THRESHOLD = 0.1`** — triggers 99/100 detections, likely too sensitive.

5. **`bit_depth: 24` hardcoded** — not read from WAV file.

---

## 5. NEW BACKEND FOLDER STRUCTURE

```
backend/
├── .gitignore
├── requirements.txt
├── run_pipeline.py              ← NEW: orchestrator
├── download_audio.py            ← NEW: on-demand R2 audio download
├── generate_clean_spectrograms.py ← NEW: crop heatmaps for frontend
├── pipeline/
│   ├── analyze_marine_audio.py  ← MOVED from root
│   ├── cascade_classifier.py    ← MOVED from root
│   └── rank_biological_importance.py ← MOVED from root
├── utils/
│   ├── audio_tester.py          ← MOVED from src/
│   ├── categorize_audio.py      ← MOVED from src/
│   ├── clip_audio.py            ← MOVED from src/
│   ├── explore_sample.py        ← MOVED from src/
│   ├── tester.py                ← MOVED from src/
│   ├── r2_download.py           ← MOVED from root
│   └── r2_manifest_template.json← MOVED from root
├── docs/
│   ├── CASCADE_PIPELINE.md      ← MOVED from root
│   ├── RANKING_METHODOLOGY.md   ← MOVED from root
│   ├── README master - Colaborator 2.md ← MOVED from root
│   ├── data_download.ipynb      ← MOVED from root
│   └── hackathon-reference/     ← MOVED from src/marine-acoustic-monitoring/
├── output/                      ← UNCHANGED (analysis results + spectrograms)
│   ├── analysis_results.json
│   ├── annotations/
│   ├── spectrograms/
│   └── spectrograms_clean/      ← NEW: cropped heatmap-only PNGs
└── output2/                     ← UNCHANGED (cascade results + spectrograms)
    ├── cascade_results.json
    ├── ranked_importance.json
    ├── ranked_importance.csv
    ├── annotations/
    └── spectrograms/
```

### External data (OUTSIDE repo):
```
SALA/data/audio/                 ← WAV files (20+ GB, NOT in Git)
├── 190806_3754.wav
├── 190806_3811.wav
├── 190806_3826.wav
└── 190806_3905.wav
```

---

## 6. HOW THE FRONTEND USES THESE

The Vite dev server (`frontend/vite.config.js`) serves backend files via middleware:

| Frontend URL | Maps to |
|-------------|---------|
| `/api/output/*` | `backend/output/*` |
| `/api/output2/*` | `backend/output2/*` |
| `/api/audio/*` | `SALA/data/audio/*` (external) |
| `/api/clean-spectrogram/*` | `backend/output/spectrograms_clean/*` |
| `/api/audio/status/<file>` | JSON: checks if WAV exists locally |
| `/api/audio/download/<file>` | Triggers `download_audio.py`, returns status |

**Audio on-demand flow:**
1. User opens a recording in Single Analysis view
2. Frontend checks `/api/audio/status/190806_XXXX.wav`
3. If `exists: false`, shows "Audio not available locally" + "Download from cloud" button
4. User clicks → frontend calls `/api/audio/download/190806_XXXX.wav`
5. Vite middleware spawns `python download_audio.py 190806_XXXX.wav`
6. Script downloads from R2 to `SALA/data/audio/`
7. Frontend reloads `<audio>` element → playback works

---

## 7. TO REVERT

If the backend team wants to undo these changes:

```bash
# Move pipeline scripts back to root
mv pipeline/*.py .
rmdir pipeline

# Move utils back to src/
mkdir -p src
mv utils/audio_tester.py utils/categorize_audio.py utils/clip_audio.py \
   utils/explore_sample.py utils/tester.py src/
mv utils/r2_download.py utils/r2_manifest_template.json .
rmdir utils

# Move docs back to root
mv docs/CASCADE_PIPELINE.md docs/RANKING_METHODOLOGY.md \
   docs/"README master - Colaborator 2.md" docs/data_download.ipynb .
mv docs/hackathon-reference src/marine-acoustic-monitoring
rmdir docs

# New files to keep (or delete):
# - run_pipeline.py, generate_clean_spectrograms.py, download_audio.py
# - requirements.txt, .gitignore
# - output/spectrograms_clean/
```

The new files (`run_pipeline.py`, `generate_clean_spectrograms.py`, `download_audio.py`, `requirements.txt`, `.gitignore`) can be kept regardless of folder structure.
