# PROJECT OVERVIEW — Dragon Ocean Analyzer

> **Este es el documento maestro.** Cualquier AI (Claude, etc.) que trabaje en este
> proyecto debe leer este archivo primero. Contiene todo el contexto necesario.

---

## Qué es este proyecto

**Dragon Ocean Analyzer** es un dashboard web para el hackathon SALA 2026 que visualiza resultados de un pipeline de clasificación de audio subacuático. Presentación de 3 minutos.

**Problema:** La Bahía de San Cristóbal (Galápagos) tiene hidrófonos SoundTrap ST300 que grabaron ~926 archivos WAV (~97 horas). Los biólogos marinos necesitan saber cuáles revisar primero.

**Nuestra solución:** Un pipeline de 3 modelos AI + un ranking de importancia biológica + un frontend interactivo que muestra todo.

---

## Pipeline (3 stages + ranking)

```
WAV → Stage 1: YAMNet (521 clases AudioSet, bio vs ruido)
    → Stage 2: Google Multispecies Whale (12 clases: 7 especies + 5 vocalizaciones)
    → Stage 3: Google Humpback Whale (binario por ventana de 1s)
    → Ranking v2 (7 dimensiones ponderadas, score 0-100, 5 tiers)
```

**IMPORTANTE:** Actualmente los 3 modelos se ejecutan SIEMPRE (no hay gating). No es un cascade real — es un pipeline paralelo. Ver BACKEND_AUDIT.md §4.1.

### Modelos

| Stage | Modelo | Input SR | Output |
|-------|--------|----------|--------|
| 1 | YAMNet (TFHub google/yamnet/1) | 16 kHz | 521 clases, embeddings |
| 2 | Multispecies Whale (Kaggle google/multispecies-whale/TF2/default/2) | 24 kHz | 12 clases por ventana 5s |
| 3 | Humpback Whale (TFHub google/humpback_whale/1) | 10 kHz | score binario por ventana 1s |

### Ranking v2 (7 dimensiones)

| Dimensión | Peso | Mide |
|-----------|------|------|
| whale_sustained | 20% | Composite max + mean multispecies |
| bio_richness | 20% | Conteo + scores bio de YAMNet |
| acoustic_diversity | 20% | Especies + tipos de vocalización |
| humpback_coverage | 15% | Fracción de ventanas con humpback |
| cross_model_agreement | 15% | Convergencia entre modelos |
| humpback_peak | 5% | Score máximo humpback |
| yamnet_top_quality | 5% | Si top-1 YAMNet es biológico |

**Tiers:** CRITICAL (≥65), HIGH (≥45), MODERATE (≥25), LOW (≥10), MINIMAL (<10)

---

## Dataset analizado

- **100 grabaciones** del deployment Pilot (48 kHz, ~5 min c/u)
- **Filenames:** `YYMMDD_SEQUENCE.wav` (ej: `190806_3754.wav` = 6 ago 2019)
- **1 solo WAV** en el repo (`190806_3754.wav`, 15.9s). Los otros 99 se procesaron externamente.

### Resultados actuales

| Métrica | Valor |
|---------|-------|
| CRITICAL | 3 archivos |
| HIGH | 35 |
| MODERATE | 40 |
| LOW | 19 |
| MINIMAL | 3 |
| YAMNet bio signals | 70/100 |
| any_whale_detected | 61/100 |
| humpback_detected | **99/100** (sospechoso — ver notas) |

### Advertencias científicas

1. **El contenido biológico NO está verificado** por expertos de dominio. Los modelos detectan patrones, no confirman presencia.
2. **99/100 humpback** es probablemente artefacto: threshold=0.1 es muy bajo, y ruido de botes se superpone con frecuencias de humpback (100-1000 Hz).
3. **21/100 archivos** tienen "Speech" como detección biológica porque `'speech'` está en `YAMNET_BIO_KEYWORDS`. Esto es un bug.
4. **Los dB son relativos**, no calibrados a µPa.

---

## Estructura del repo

```
hackathon_sala2026/
├── PROJECT_OVERVIEW.md     ← ESTE ARCHIVO (leer primero)
├── README.md               ← Intro + quickstart
├── FRONTEND_AUDIT.md       ← Bugs frontend + TODO features + prompts Claude
├── BACKEND_AUDIT.md        ← Bugs backend + TODO + coherencia teórica
├── PAPER_NOTES.md          ← Notas de papers científicos relevantes
│
├── backend/
│   ├── analyze_marine_audio.py    ← Band analysis (output/)
│   ├── cascade_classifier.py      ← YAMNet + Multispecies + Humpback (output2/)
│   ├── rank_biological_importance.py ← Scoring (output2/)
│   ├── data/raw_data/             ← 1 WAV
│   ├── output/                    ← analysis_results.json + spectrograms/ + annotations/
│   ├── output2/                   ← cascade_results.json + ranked_importance.json + spectrograms/ + annotations/
│   ├── CASCADE_PIPELINE.md
│   ├── RANKING_METHODOLOGY.md
│   └── src/                       ← Utilidades (silence filter, clipper, etc.)
│
└── frontend/
    ├── src/
    │   ├── main.jsx, App.jsx      ← Entry + router
    │   ├── config.js              ← Tiers, species map, scoring dimensions
    │   ├── utils.js               ← Data loaders, CSV export
    │   ├── styles.css             ← Tema dark+light (CSS custom properties)
    │   ├── context/ThemeContext.jsx
    │   ├── pages/
    │   │   ├── LandingPage.jsx
    │   │   ├── SingleObservation.jsx
    │   │   └── MultipleObservations.jsx
    │   └── components/
    │       ├── Navbar.jsx, Sidebar.jsx
    │       ├── PipelineDiagram.jsx
    │       ├── SpectrogramViewer.jsx  ← Zoom, pan, audio, timeline
    │       ├── Charts.jsx             ← Doughnut, Bar, Line, Radar
    │       ├── ReportTable.jsx        ← Sort, filter, CSV export
    │       ├── AnalysisPanel.jsx      ← Score, radar, 3 classifiers, charts
    │       ├── DetailModal.jsx
    │       └── TierBadge.jsx
    ├── vite.config.js             ← Middleware sirve data de backend/
    └── package.json               ← React 18, Vite 6, Chart.js
```

---

## Schemas de datos (referencia rápida)

### cascade_results.json → por archivo

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
  any_whale_detected: bool (threshold ≥0.1)
  num_windows: int
  ⚠ top_time_series: BORRADO del JSON (existe en annotations individuales)

stage3_humpback:
  max_score: float
  mean_score: float
  fraction_above_threshold: float
  humpback_detected: bool (threshold ≥0.1)
  num_windows: int
  ⚠ time_series: BORRADO del JSON (existe en annotations individuales)
```

### ranked_importance.json → por archivo

```
rank, filename, score (0-100), tier (CRITICAL/HIGH/MODERATE/LOW/MINIMAL)
components: {whale_sustained, bio_richness, acoustic_diversity,
             humpback_coverage, cross_model_agreement, humpback_peak,
             yamnet_top_quality}
cascade_flags: [string]
top_species: string
```

### analysis_results.json → por archivo

```
band_analysis: {
  infrasonic_whales: {freq_range_hz, mean_energy_db, temporal_std, transient_events}
  low_freq_fish: ...
  mid_freq_dolphins: ...
  high_freq_clicks: ...
}
annotations: [string]
spectrogram: "filename_spectrogram.png"
```

### Clases del modelo Multispecies (12 total)

**Especies (7):** Oo (Orca), Mn (Humpback), Eg (Right whale), Bp (Fin), Bm (Blue), Ba (Minke), Be (Beaked)
**Vocalizaciones (5):** Call, Echolocation, Gunshot, Upcall, Whistle

Solo se detectan en nuestros datos: Bm, Bp, Eg, Mn, Oo + Call, Echolocation, Gunshot, Upcall, Whistle. Ba y Be nunca aparecen.

---

## API Routes (Vite middleware)

| Ruta | Sirve desde | Contenido |
|------|------------|-----------|
| `/api/output/*` | `backend/output/` | analysis_results.json, spectrograms/, annotations/ |
| `/api/output2/*` | `backend/output2/` | cascade_results.json, ranked_importance.json, spectrograms/, annotations/ |
| `/api/audio/*` | `backend/data/raw_data/` | WAV files (HTTP 206 range) |

---

## Bugs conocidos (resumen — ver audits para detalle)

### Frontend
- **time_series no existe en JSON** → Event timeline vacío, time series charts no renderizan
- **SPECIES_MAP incompleto** → Falta Call, Echolocation, Gunshot, Upcall, Whistle
- **"99 Humpback Signals"** se presenta sin contexto de que puede ser artefacto del modelo
- **Falta disclaimer** de contenido biológico no verificado

### Backend
- **time_series se borra** antes de guardar en JSON consolidado (L544-549)
- **"Speech" como bio** → 21 archivos afectados
- **INPUT_DIR inexistente** → apunta a `Music_Soundtrap_Pilot`
- **Cascade sin gates** → los 3 modelos se ejecutan siempre
- **No hay requirements.txt**

---

## Convenciones de código

### Frontend
- CSS: todo en `styles.css` con custom properties. Mantener `[data-theme="dark"]` Y `[data-theme="light"]`
- Data: usar funciones de `utils.js` (loadRankedData, loadCascadeResults, etc.)
- Charts: componentes en `Charts.jsx` usando react-chartjs-2
- Config: species map, tiers, dimensiones en `config.js`
- Componentes: un archivo por componente en `components/`

### Backend
- Pipeline execution order: `analyze_marine_audio.py` → `cascade_classifier.py` → `rank_biological_importance.py`
- Output dirs: `output/` (stage 0 band analysis), `output2/` (cascade + ranking)

---

## Contexto hackathon

- **Evento:** SALA 2026 AI Hackathon
- **Demo:** 3 minutos, 5 slides máx
- **Judging:** Originality (30%), Technical Execution (30%), Impact & Relevance (25%), Presentation (15%)
- **Key pitch points:**
  - Herramienta para biólogos marinos que prioriza qué grabaciones revisar
  - 7 dimensiones de scoring, no solo un threshold simple
  - 100 archivos analizados, 3 CRITICAL identificados
  - Galápagos: 23 especies de cetáceos, 14 residentes/visitantes
  - Contenido no verificado = honestidad científica (valor para jueces)
- **Future vision:** similarity search (Agile Modeling), PCEN, más unidades, active learning

---

## Prompt base para Claude Opus 4.6

```
Trabajo en "Dragon Ocean Analyzer" — dashboard React + pipeline Python para
bioacústica marina, hackathon SALA 2026 (Galápagos Marine Reserve).

LEE PRIMERO: PROJECT_OVERVIEW.md (contexto completo del proyecto)
LUEGO LEE: FRONTEND_AUDIT.md o BACKEND_AUDIT.md según tu tarea

Repo: hackathon_sala2026/
  backend/  — Python pipeline (analyze → cascade → rank)
  frontend/ — React 18 + Vite 6 + Chart.js

Mi tarea es: [DESCRIBE]
```
