# Backend Audit — Dragon Ocean Analyzer

> Para el equipo de backend. Lista bugs, inconsistencias, organización y
> discrepancias con la teoría del proyecto. NO se modificaron archivos.

---

## 1. BUGS CRÍTICOS

### 1.1 `time_series` se genera pero se BORRA antes de guardar

**Archivo:** `cascade_classifier.py` L244,293 (genera) → L544-549 (borra)

Genera `top_time_series` (multispecies) y `time_series` (humpback). Se usan en las PNG. Pero se borran del JSON consolidado:
```python
result['stage2_multispecies'].pop('top_time_series', None)
result['stage3_humpback'].pop('time_series', None)
```
**Impacto:** Frontend no puede mostrar gráficos temporales. **Fix:** Dejar de borrar (~50KB extra).

### 1.2 `INPUT_DIR` apunta a carpeta inexistente

`INPUT_DIR = Path("Music_Soundtrap_Pilot")` — no existe en el repo. WAVs están en `data/raw_data/`.

### 1.3 `bit_depth: 24` hardcodeado

`analyze_marine_audio.py` L228 — valor fijo, no leído del WAV.

### 1.4 "Speech" y "Music" cuentan como detección biológica

`cascade_classifier.py` L50-54: `YAMNET_BIO_KEYWORDS` incluye `'singing'`, `'music'`, `'speech'`. Resultado: **21/100** archivos tienen "Speech" como bio detection. Infla `bio_richness` en ranking.

**Fix:** Quitar esas 3 keywords.

### 1.5 Doble threshold para multispecies

- `MULTISPECIES_THRESHOLD = 0.01` → lista detections
- `any_whale_detected` usa `>= 0.1`

Frontend muestra toda la lista como detecciones, pero muchas son 0.01-0.09.

---

## 2. INCONSISTENCIAS DE DATOS

### 2.1 output/ vs output2/ desalineados

| Campo | output/ | output2/ |
|-------|---------|----------|
| `has_biological_interest` | ✅ | ❌ (usa `cascade_flags`) |
| `rms` | ❌ | ✅ |
| `band_analysis` | ✅ | ❌ |
| `stage1_yamnet` | ❌ | ✅ |

Frontend combina ambos. Considerar un `merged_results.json`.

### 2.2 No hay `requirements.txt`

Deps: numpy, librosa, matplotlib, scipy, tensorflow, tensorflow_hub, soundfile, boto3. Sin requirements nadie puede reproducir.

---

## 3. ORGANIZACIÓN DE ARCHIVOS

### Problemas:
1. `.idea/` y `__pycache__/` en el repo — agregar a `.gitignore`
2. `r2_download.py` duplicado (raíz Y `src/marine-acoustic-monitoring/`)
3. 3 scripts principales sueltos sin runner ni orden documentado
4. `Music_Soundtrap_Pilot` hardcodeado, no existe
5. No hay `run_pipeline.py` ni coordinador

### Estructura recomendada:
```
backend/
├── requirements.txt
├── run_pipeline.py           ← ejecuta analyze → cascade → rank
├── pipeline/
│   ├── analyze_marine_audio.py
│   ├── cascade_classifier.py
│   └── rank_biological_importance.py
├── utils/
│   ├── categorize_audio.py
│   ├── clip_audio.py
│   └── audio_tester.py
├── data/raw_data/
├── output/ + output2/
└── docs/
    ├── CASCADE_PIPELINE.md
    └── RANKING_METHODOLOGY.md
```

---

## 4. COHERENCIA CON LA TEORÍA

### 4.1 El cascade NO es un cascade real

El README describe gates: Stage 1 filtra → Stage 2 → Stage 3. Pero en el código **los 3 modelos se ejecutan SIEMPRE** (L389-396), sin condicionar. Un archivo "Silence" pasa por multispecies y humpback igual.

**Fix:** Condicionar Stage 2 y 3 al resultado del stage anterior.

### 4.2 PCEN no implementado

Papers recomiendan PCEN en vez de log-power (reduce FP 5-50x). El código usa `librosa.power_to_db`. librosa tiene `librosa.pcen(S)` integrado. Solo afecta band analysis; los modelos TFHub hacen su propio preprocessing.

### 4.3 No hay calibración a µPa

Energías son relativas, no calibradas. Aceptable para hackathon, pero debe documentarse.

### 4.4 No se parsean metadatos XML

Papers recomiendan extraer `SamplingStartTimeUTC`, `Temperature`, `Gain`, sampling gaps de `.log.xml`. Nada se extrae.

### 4.5 Bandas simplificadas

`infrasonic_whales: 10-100 Hz` pero mysticetos llegan a 4 kHz. `mid_freq_dolphins: 500-5000 Hz` pero odontocetos van a 160+ kHz. Para el pitch: "bandas simplificadas para Pilot 48 kHz".

### 4.6 Humpback threshold genera 99% detección

`HUMPBACK_THRESHOLD = 0.1` → 99/100 detectados. Modelo posiblemente confunde ruido de botes con humpback. Considerar subir a 0.3-0.5.

---

## 5. TODO

### Urgentes (afectan demo)
- [ ] Dejar de borrar time_series (L544-549)
- [ ] Quitar 'speech'/'music'/'singing' de YAMNET_BIO_KEYWORDS
- [ ] Crear requirements.txt
- [ ] .gitignore: .idea/, __pycache__/

### Precisión
- [ ] Implementar gates en el cascade
- [ ] Considerar PCEN
- [ ] Evaluar humpback threshold (0.1 → 0.3?)
- [ ] Agregar confidence_level a detections

### Organización
- [ ] Parametrizar INPUT_DIR
- [ ] Crear run_pipeline.py
- [ ] Eliminar r2_download.py duplicado

---

## 6. PROMPT PARA CLAUDE (Backend)

```
Trabajo en el backend de "Dragon Ocean Analyzer" — pipeline Python de bioacústica
marina para el hackathon SALA 2026 (Galapagos Marine Reserve).

ESTRUCTURA:
  backend/
  ├── analyze_marine_audio.py   ← Band analysis + spectrograms (output/)
  ├── cascade_classifier.py     ← YAMNet + Multispecies + Humpback (output2/)
  ├── rank_biological_importance.py ← Scoring 7-dimensional (output2/)
  ├── data/raw_data/            ← WAV files
  └── output/ + output2/        ← Results

BUGS CRÍTICOS (ver BACKEND_AUDIT.md):
1. time_series se genera pero se borra antes de guardar (L544-549)
2. INPUT_DIR="Music_Soundtrap_Pilot" no existe en el repo
3. 'speech'/'music' cuentan como detección biológica
4. El cascade NO filtra — los 3 modelos se ejecutan siempre
5. HUMPBACK_THRESHOLD=0.1 genera 99/100 detecciones

MODELOS:
- YAMNet: TFHub google/yamnet/1 (16kHz, 521 AudioSet classes)
- Multispecies: Kaggle google/multispecies-whale/TF2/default/2 (24kHz, 12 classes)
- Humpback: TFHub google/humpback_whale/1 (10kHz, binary 1s windows)

Mi tarea es: [DESCRIBE]
```
