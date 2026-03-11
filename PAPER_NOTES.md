# Notas de Papers — Relevantes para Dragon Ocean Analyzer

> Extraído de 3 papers del proyecto. Solo incluye lo que afecta directamente al frontend,
> a la correcta representación de datos, o a funcionalidades que deberíamos implementar.

---

## 1. Especies y frecuencias de Galápagos (VERIFICAR en nuestro frontend)

Los papers confirman que las aguas de Galápagos albergan **al menos 23 especies de cetáceos**, de las cuales **14 son residentes o visitantes comunes**. Incluyen:
- 9 delfínidos (dolphin family)
- 1 zifio (beaked whale — `Be` en nuestro config)
- 1 cachalote (*Physeter macrocephalus* — **NO está en nuestro SPECIES_MAP**)
- 3 balenoptéridos (*B. musculus* blue whale, *B. edeni* Bryde's whale — **Bryde's NO está en SPECIES_MAP**)

**Rangos de frecuencia correctos por taxón** (de Paper 1, tabla):

| Grupo | Frecuencia | Sonidos típicos |
|-------|-----------|-----------------|
| Ballenas barbadas (Mysticetes) | **10 Hz – 4 kHz** | Moans tonales, upcalls, cantos estructurados |
| Ballenas dentadas (Odontocetes) | **2 kHz – 160+ kHz** | Clicks ecolocalización, burst pulses, silbidos FM |
| Peces (Sciaenidae, etc.) | **100 Hz – 3 kHz** | Coros LF, knocks, grunts |
| Invertebrados (shrimp, etc.) | **2 kHz – 200+ kHz** | Snaps broadband transitorios |

**Impacto en frontend:** Nuestras bandas en `config.js` son:
- `infrasonic_whales: 10-100 Hz` — Esto es **demasiado estrecho**. Los misticetos llegan hasta 4 kHz.
- `low_freq_fish: 50-500 Hz` — Razonable, pero overlap con boats (100-1000 Hz).
- `mid_freq_dolphins: 500-5000 Hz` — Los silbidos están en 5-20 kHz realmente.
- `high_freq_clicks: 5-24 kHz` — OK para pilot (48 kHz SR), pero clicks reales son >100 kHz.

**Acción:** No cambiar las bandas (vienen del backend `analyze_marine_audio.py`), pero **en la UI debemos explicar** que estas son bandas de análisis simplificadas para la SR de 48 kHz del Pilot, no los rangos biológicos completos. Esto muestra sofisticación científica en el pitch.

---

## 2. El modelo Humpback — por qué 99/100 detecta

Paper 2 y 3 explican que el modelo Google Humpback funciona con audio **resampleado a 10 kHz** y es un detector binario (sí/no por ventana de 1 segundo). Los papers mencionan:

> "Even a negative result ('no humpbacks detected') is useful information."

Las ballenas jorobadas producen cantos entre **100 Hz y 4 kHz**, con armónicos hasta 8 kHz. El modelo está entrenado en cantos de humpback del Pacífico Norte. Dado que la Bahía de San Cristóbal tiene mucho **ruido de botes en 100-1000 Hz** que parcialmente *se superpone* con frecuencias de humpback, es plausible que el modelo genere falsos positivos por ruido de barcos.

**Impacto en frontend:** Nuestro landing page dice "99 Humpback Signals" como si fuera un logro. Esto es probablemente un artefacto del modelo. Debemos:
1. Mostrar `fraction_above_threshold` (actualmente lo mostramos en AnalysisPanel — bien)
2. Agregar contexto: "Señales consistentes con patrón humpback (no verificado por expertos)"
3. Enfatizar que `humpback_detected=true` **no confirma presencia** — solo que el score supera un umbral configurable

---

## 3. Las 12 clases del Multispecies Model — vocalizaciones son tipos, no especies

Paper 1 confirma que el modelo Google Multispecies clasifica **12 clases de whale/dolphin**. Nuestros datos contienen:

**Especies (7):** Oo (Orca), Mn (Humpback), Eg (Right), Bp (Fin), Bm (Blue), Ba (Minke), Be (Beaked)
**Vocalizaciones (5):** Call, Echolocation, Gunshot, Upcall, Whistle

**Contexto importante que debemos mostrar:**
- `Echolocation` = clicks de ecolocalización de odontocetos (delfines, orcas, cachalotes)
- `Call` = llamada genérica de ballena (no específica a una especie)
- `Upcall` = llamada ascendente típica de ballena franca (*Eg*)
- `Gunshot` = sonido impulsivo tipo disparo (ballena franca en superficie)
- `Whistle` = silbido tonal de delfín/ballena

**Acción:** Ya lo teníamos identificado en FRONTEND_AUDIT.md. Actualizar SPECIES_MAP y mostrar vocalizaciones como categoría separada de las especies.

---

## 4. Spectrogramas — lo que realmente representan

Los papers detallan que un espectrograma estándar se genera con:
- **STFT** (Short-Time Fourier Transform) con ventanas Hamming de ~20ms y hop de ~10ms
- **Escala logarítmica** (dB) en el eje de magnitud
- **Mel filterbank** (128 o 256 filtros) opcionalmente en el eje de frecuencia

Nuestros spectrogramas (PNG generados por `analyze_marine_audio.py`) son imágenes estáticas. Paper 1 y Paper 3 enfatizan que **PCEN** (Per-Channel Energy Normalization) es mejor que log para suprimir ruido estacionario. Esto no afecta el frontend directamente, pero es un punto a mencionar en el pitch:

> "Nuestros espectrogramas usan normalización logarítmica estándar. Para futuras iteraciones, se puede implementar PCEN que reduce falsos positivos en un factor de 5-50x (según la literatura)."

---

## 5. La jerarquía temporal CORRECTA de los SoundTrap

Paper 3 detalla la convención de nombres:
- **Pilot:** `YYMMDD_sequence.wav` → `190806_3754` = 6 agosto 2019, secuencia 3754
- **Unit 6478:** `6478.YYMMDDHHMMSS.wav` → `6478.230723151251` = 23 jul 2023, 15:12:51
- **Unit 5783:** mismo patrón que 6478

**Dato crítico:** Los timestamps en los nombres de archivos del Pilot **están en hora local**, no UTC. El reloj interno del SoundTrap está en UTC, pero al offload se convierte a la zona horaria del PC.

**Impacto en frontend:** Si implementamos patrones temporales (hora del día, fecha), debemos:
1. Parsear `YYMMDD` del filename como fecha (ya lo tenemos como idea en FRONTEND_AUDIT)
2. Advertir que la hora puede no ser UTC exacto
3. Para el Pilot, solo tenemos fecha, no hora (el `sequence` no da hora)

---

## 6. WaveSurfer.js — recomendado por la literatura

Paper 1, sección de frontends, **específicamente recomienda wavesurfer.js** para plataformas de bioacústica:

> "Frontends integrate HTML5 Canvas and Web Audio API libraries, prominently wavesurfer.js. When a point is selected, wavesurfer.js dynamically fetches the corresponding audio file, rendering an interactive, navigable waveform and spectrogram directly within the browser UI."

Esto valida nuestra feature planeada. Para el pitch, podemos decir que seguimos las recomendaciones de la literatura actual.

---

## 7. Similarity Search / Agile Modeling — idea diferenciadora

Paper 1 describe una arquitectura completa de **"similarity search frontend"** donde:
1. Se extraen embeddings de cada ventana de audio con un foundation model (Perch 2.0)
2. Se almacenan en una base de datos vectorial (Milvus)
3. El usuario selecciona un sonido "semilla" y busca similares por distancia coseno
4. Active learning: el biólogo valida resultados, se entrena clasificador logístico instantáneo

**Esto podría ser nuestra feature diferenciadora para el pitch.** Aunque no podemos implementar el backend vector DB en este hackathon, podemos:
- Mostrar en el frontend una UI de "Find Similar Recordings" que agrupe archivos por score de multispecies
- Simular un espacio de embeddings con los scores que ya tenemos (7 dimensiones de scoring = vector)
- Mencionar en el pitch que esto es la base para un "Agile Modeling" workflow

---

## 8. Índices acústicos que debemos considerar

Paper 2 y el hackathon README mencionan estos índices estándar:
- **Shannon entropy** — diversidad del paisaje sonoro (alto = muchos tipos de sonido)
- **NDSI** (Normalized Difference Soundscape Index) — ratio bio vs antropogénico.
  **IMPORTANTE:** Los rangos default de NDSI en `scikit-maad` son para bosques (bio: 2-8 kHz, human: 1-2 kHz). **Para océano, deben ser:** bio: 2-20 kHz, human: 100-1000 Hz
- **ACI** (Acoustic Complexity Index) — variabilidad espectral momento a momento

Nuestro backend ya calcula `band_analysis` con 4 bandas y métricas de energía. Estos son análogos simplificados, pero no son los índices estándar de la literatura. Para el pitch, podemos:
1. Mencionar que nuestras bandas de análisis cubren las frecuencias clave
2. Proponer NDSI y ACI como mejoras futuras
3. Mostrar que entendemos que los defaults no aplican para océano

---

## 9. Datos sin calibrar — disclaimer necesario

Paper 3 enfatiza:

> "SoundTrap provee calibración end-to-end. Convertir cal_dB a ratio y multiplicar la señal para obtener µPa."

Nuestros datos **NO están calibrados**. Las energías en `band_analysis` son relativas, no en µPa absolutos. El hackathon README también lo dice: "all sound levels are relative."

**Acción en frontend:** En el Band Energy Chart o donde mostremos dB, agregar label: "Relative dB (not calibrated to µPa)". Esto muestra rigor científico.

---

## 10. Formato .sud — potencial para más datos

Hay **~223 archivos .sud** sin convertir (23 de unit 5783, ~200 de unit 6478). Si el equipo de backend logra convertirlos (usando SUD2WAV Docker o PAMGuard), el dataset se multiplicaría significativamente. Esto es un punto fuerte para "Future Vision" en el pitch.

---

## 11. Arquitectura de frontends bioacústicos (del Paper 1)

Paper 1 describe las plataformas de referencia actuales:

| Plataforma | Stack | Lo que hace |
|-----------|-------|------------|
| Audio Atlas | WebGL + React + DeepScatter | Exploración de embeddings contrastivos |
| A2O Search Platform | Next.js + React + Milvus | Similarity search sobre petabytes |
| Geono-Cluster | JavaScript + D3.js | Refinamiento visual de clusters (drag-and-drop) |
| PAMGuard | Java + SQLite | Estándar industrial para .sud, detección clásica |
| OpenSoundscape | Python + PyTorch | Training de CNNs, espectrogramas, RIBBIT |

Nuestro stack (React + Vite + Chart.js) está alineado con lo que la literatura recomienda para frontends bioacústicos. Para escalar, necesitaríamos:
- **WebGL** (DeepScatter o similar) para visualizar embeddings de miles de puntos
- **Vector database** para similarity search
- Integración con **wavesurfer.js** para playback interactivo

---

## Resumen de acciones para el frontend

### Urgente (afecta correctness)
- [ ] Agregar disclaimer de "contenido biológico no verificado" en la UI
- [ ] Actualizar SPECIES_MAP con las 5 clases de vocalización
- [ ] Corregir etiquetas: "dB relativos", no absolutos
- [ ] Contextualizar "99 humpback signals" como modelo potencialmente sobre-sensible

### Para el pitch (diferenciadores)
- [ ] Mencionar PCEN como mejora futura (reduce FP 5-50x)
- [ ] Citar Agile Modeling / similarity search como dirección futura
- [ ] Mostrar que nuestras bandas de frecuencia son diseño consciente para 48 kHz SR
- [ ] Mencionar .sud → WAV como potencial de expansión del dataset
- [ ] Citar los papers como fundamento teórico del pipeline

### Mejoras de funcionalidad
- [ ] Implementar parsing temporal de filenames (YYMMDD → fecha)
- [ ] Integrar wavesurfer.js (recomendado por la literatura)
- [ ] Mostrar vocalizaciones y especies como categorías separadas en charts
- [ ] Agregar vista de "recordings similares" basada en componentes de score existentes
