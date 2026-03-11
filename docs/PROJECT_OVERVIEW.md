# PROJECT OVERVIEW — Dragon Ocean Analyzer

> **Este es el documento maestro.** Cualquier AI (Claude, etc.) que trabaje en este
> proyecto debe leer este archivo primero. Contiene todo el contexto necesario.

---

## Qué es este proyecto

**Dragon Ocean Analyzer** es un dashboard web para el hackathon SALA 2026 que visualiza resultados de un pipeline de clasificación de audio subacuático. Presentación de 3 minutos.

**Problema:** La Bahía de San Cristóbal (Galápagos) tiene hidrófonos SoundTrap ST300 que grabaron ~926 archivos WAV (~97 horas). Los biólogos marinos necesitan saber cuáles revisar primero.

**Nuestra solución:** Un pipeline de 6 stages (segmentación + 3 modelos AI + soundscape + clustering) + un ranking de importancia biológica + un frontend interactivo que muestra todo.

---

## Pipeline (stages 0-6)

```
WAV → Stage 0: AudioClipper    (silence filter + segmentación)
    → Stage 1: YAMNet          (521 clases AudioSet, bio vs ruido)
    → Stage 2: Multispecies    (12 clases: 7 especies + 5 vocalizaciones)
    → Stage 3: Humpback Whale  (binario por ventana de 1s)
    → Stage 4: Ranking v2      (7 dimensiones ponderadas, score 0-100, 5 tiers)
    → Stage 5: Soundscape      (NDSI — penaliza dominancia de barcos)
    → Stage 6: Clustering      (UMAP + HDBSCAN, bonus por cluster biológico)
```

**IMPORTANTE:** Los 3 modelos (stages 1-3) se ejecutan SIEMPRE (no hay gating). No es un cascade real — es un pipeline paralelo. Ver BACKEND_AUDIT.md §4.1.

### Modelos

| Stage | Modelo | Input SR | Output |
|-------|--------|----------|--------|
| 1 | YAMNet (TFHub google/yamnet/1) | 16 kHz | 521 clases, embeddings |
| 2 | Multispecies Whale (Kaggle google/multispecies-whale/TF2/default/2) | 24 kHz | 12 clases por ventana 5s |
| 3 | Humpback Whale (TFHub google/humpback_whale/1) | 10 kHz | score binario por ventana 1s |

### Ranking v2 (9 dimensiones)

| Dimensión (key) | Peso | Mide |
|-----------------|------|------|
| `whale_sustained` | 18% | Composite max + mean multispecies |
| `bio_richness` | 15% | Conteo + scores bio de YAMNet |
| `acoustic_diversity` | 15% | Especies + tipos de vocalización |
| `humpback_coverage` | 12% | Fracción de ventanas con humpback |
| `cross_model` | 12% | Convergencia entre modelos |
| `ndsi_score` | 10% | NDSI marino (Stage 5, penaliza barcos) |
| `cluster_signal` | 8% | Bonus por cluster biológico (Stage 6) |
| `humpback_peak` | 5% | Score máximo humpback |
| `yamnet_quality` | 5% | Si top-1 YAMNet es biológico |

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
2. **Humpback FP reducidos:** threshold subido de 0.1 → 0.3. Cifra exacta depende del dataset activo.
3. `'singing'`/`'speech'`/`'music'` removidos de `YAMNET_BIO_KEYWORDS` — ya no inflan bio_richness.
4. **Los dB son relativos**, no calibrados a µPa.

---

## Estructura del repo

```
dragon-ocean-analyzer/
├── README.md               ← Intro + quickstart
├── LICENSE
├── requirements.txt        ← Deps Python (librosa, tensorflow, etc.)
├── .gitignore
│
├── backend/                ← Python ML pipeline
│   ├── config.py           ← Todas las constantes del pipeline
│   ├── run.py              ← Entry point: ejecuta stages 0-6
│   ├── stage0_clip.py      ← Silence filter + segmentación de WAVs
│   ├── stage1_3_cascade.py ← YAMNet + Multispecies + Humpback
│   ├── stage4_rank.py      ← Ranking 9-dimensional (score 0-100)
│   ├── stage5_soundscape.py← NDSI (scikit-maad)
│   └── stage6_cluster.py   ← UMAP + HDBSCAN embeddings
│
├── frontend/               ← React 18 + Vite 6
│   ├── src/
│   │   ├── main.jsx, App.jsx      ← Entry + router
│   │   ├── config.js              ← Tiers, species map, scoring dimensions
│   │   ├── utils.js               ← Data loaders, CSV export
│   │   ├── styles.css             ← Tema dark+light (CSS custom properties)
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
│   ├── vite.config.js             ← Middleware sirve outputs/
│   └── package.json               ← React 18, Vite 6, Chart.js
│
├── scripts/                ← Utilidades y despliegue
│   ├── r2_download.py      ← Descarga datos desde Cloudflare R2
│   ├── manifest.json       ← Manifiesto del dataset hackathon
│   ├── r2_manifest_template.json
│   ├── runpod_run.sh       ← Lanzador para RunPod GPU
│   └── data_download.ipynb ← Notebook interactivo de descarga
│
├── docs/                   ← Documentación del proyecto
│   ├── PROJECT_OVERVIEW.md ← ESTE ARCHIVO (leer primero)
│   ├── FRONTEND_AUDIT.md
│   ├── PAPER_NOTES.md
│   └── guidelines.md
│
└── outputs/        ← Generado por run.py (gitignored)
    ├── clips/              ← WAVs segmentados (Stage 0)
    ├── analysis/           ← results.json + spectrograms/ + annotations/
    ├── ranking/            ← ranked.json + ranked.csv
    ├── soundscape/         ← Stage 5 output
    └── clusters/           ← Stage 6 output
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
  any_whale_detected: bool (threshold ≥ MULTISPECIES_DETECTION_THR = 0.10)
  num_windows: int
  top_time_series: [float]  ← incluido en JSON desde Bug 1.1 fix

stage3_humpback:
  max_score: float
  mean_score: float
  fraction_above_threshold: float
  humpback_detected: bool (threshold ≥ HUMPBACK_THRESHOLD = 0.30)
  num_windows: int
  time_series: [float]  ← incluido en JSON desde Bug 1.1 fix
```

### ranked.json → por archivo (outputs/ranking/)

```
total_ranked: int
tier_distribution: {CRITICAL, HIGH, MODERATE, LOW, MINIMAL}
rankings: [{
  rank, filename, score (0-100), tier
  components: {whale_sustained, bio_richness, acoustic_diversity,
               humpback_coverage, cross_model, ndsi_score,
               cluster_signal, humpback_peak, yamnet_quality}
  cascade_flags: [string]
  top_species: string  ← nombre completo, no código
  annotations: [string]
}]
```

### Clases del modelo Multispecies (12 total)

**Especies (7):** Oo (Orca), Mn (Humpback), Eg (Right whale), Bp (Fin), Bm (Blue), Ba (Minke), Be (Beaked)
**Vocalizaciones (5):** Call, Echolocation, Gunshot, Upcall, Whistle

Solo se detectan en nuestros datos: Bm, Bp, Eg, Mn, Oo + Call, Echolocation, Gunshot, Upcall, Whistle. Ba y Be nunca aparecen.

---

## API Routes (Vite middleware)

| Ruta | Sirve desde | Contenido |
|------|------------|-----------|
| `/api/pipeline/analysis/*` | `outputs/analysis/` | results.json, spectrograms/, annotations/ |
| `/api/pipeline/ranking/*` | `outputs/ranking/` | ranked.json, ranked.csv |
| `/api/pipeline/soundscape/*` | `outputs/soundscape/` | soundscape.json |
| `/api/pipeline/clusters/*` | `outputs/clusters/` | clusters.json |
| `/api/audio/*` | `backend/data/raw_data/` | WAV files (HTTP 206 range) |

---

## Bugs conocidos (resumen — ver audits para detalle)

### Frontend
- ✅ **time_series no existía en JSON** → corregido, ahora incluido
- ✅ **API routes desconectadas** → corregido, ahora `/api/pipeline/*`
- ✅ **cross_model_agreement** → corregido a `cross_model`
- ✅ **threshold visual 0.5** → corregido a 0.3 en TimeSeriesChart
- **SPECIES_MAP incompleto** → falta Call, Echolocation, Gunshot, Upcall, Whistle (ver `docs/FRONTEND_AUDIT.md` §1.2)
- **Falta disclaimer** de contenido biológico no verificado

### Backend
- ✅ **time_series se borraba** del JSON consolidado — corregido
- ✅ **'singing'/'speech'/'music' como bio** — removidos de YAMNET_BIO_KEYWORDS
- ✅ **HUMPBACK_THRESHOLD = 0.1** (99% FP) → subido a 0.3
- ✅ **0.1 hardcodeado** en stage1_3_cascade.py → extraído como MULTISPECIES_DETECTION_THR en config.py
- ✅ **No hay requirements.txt** — ya existe
- **Cascade sin gates** → los 3 modelos se ejecutan siempre (decisión pendiente — ver análisis: YAMNet no detecta cetáceos en este dataset, un gate basado en YAMNet bloquearía el pipeline)

---

## Convenciones de código

### Frontend
- CSS: todo en `styles.css` con custom properties. Mantener `[data-theme="dark"]` Y `[data-theme="light"]`
- Data: usar funciones de `utils.js` (loadRankedData, loadCascadeResults, etc.)
- Charts: componentes en `Charts.jsx` usando react-chartjs-2
- Config: species map, tiers, dimensiones en `config.js`
- Componentes: un archivo por componente en `components/`

### Backend
- Pipeline execution: `python -m backend.run --source <data_dir>` (orquesta stages 0-6)
- Output dir: `outputs/` (clips/, analysis/, ranking/, soundscape/, clusters/)

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

## Prompt base para Claude

```
Trabajo en "Dragon Ocean Analyzer" — dashboard React + pipeline Python para
bioacústica marina, hackathon SALA 2026 (Galápagos Marine Reserve).

LEE PRIMERO: docs/PROJECT_OVERVIEW.md (contexto completo del proyecto)
LUEGO LEE: docs/FRONTEND_AUDIT.md según tu tarea

Repo:
  backend/          — Python pipeline stages 0-6
  frontend/src/     — React 18 + Vite 6 + Chart.js
  scripts/          — utilidades de descarga y despliegue
  docs/             — documentación
  outputs/  — artefactos generados (gitignored)

Mi tarea es: [DESCRIBE]
```
