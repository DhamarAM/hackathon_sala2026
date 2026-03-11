# Metodología de Ponderación para Importancia Biológica (v2)

## Objetivo

Ordenar los 100 archivos de audio procesados por el pipeline de clasificación en cascada según su **importancia biológica**, permitiendo a los investigadores concentrar su esfuerzo de revisión manual en los archivos con contenido más rico y relevante.

## Problema

Los tres modelos del pipeline en cascada generan múltiples métricas por archivo:
- YAMNet: 521 clases, detecciones biológicas, detecciones marinas
- Multispecies Whale: 12 clases con scores por ventana temporal
- Humpback Whale: probabilidad por ventana temporal de 1 segundo

¿Cómo combinar estas métricas heterogéneas en un **score único y ordenable** que refleje el valor biológico real de cada grabación?

## Evolución: v1 → v2

### Problema con la ponderación v1

La v1 asignaba 35% del peso al **score máximo** del modelo multispecies. Esto causaba que archivos con un único pico transitorio de Orca (0.98 en una ventana de 5 segundos) dominaran el ranking, incluso cuando:

- Su clase top en YAMNet era "Speech" o "Silence" (no biológica)
- La actividad era un spike aislado, no una señal sostenida
- Otros archivos tenían señales biológicas más ricas pero distribuidas

**Caso de estudio**: `190807_3963.wav` (rank #19 en v1, ahora #5 en v2)

| Métrica | 190807_3963 (era #19) | 190806_3811 (era #1) |
|---------|----------------------|---------------------|
| YAMNet top-1 | **"Animal" (0.25)** | "Speech" (0.39) |
| YAMNet bio detections | **8** | 2 |
| Multispecies max | 0.34 (Orca) | **0.98 (Orca)** |
| Multispecies mean (Orca) | 0.013 | 0.040 |
| Tipos de vocalización | Orca, Call, Echo, Whistle | Orca, Call, Echo, Whistle, Mn, Bp |
| Humpback cobertura | 23% | **65%** |
| Espectrograma | Bandas de energía continuas 500-4000 Hz | Spikes intensos pero esporádicos |

El archivo `3963` tiene la **señal biológica más clara y sostenida** según YAMNet (top-1 = "Animal", 8 detecciones biológicas), pero la v1 lo penalizaba por tener un pico multispecies "solo" de 0.34.

### Cambios clave en v2

| Dimensión | v1 | v2 | Razón del cambio |
|-----------|-----|-----|-----------------|
| Whale confidence | 35% (solo max) | 20% (composite max+mean) | Un spike no es tan valioso como presencia sostenida |
| Bio richness (YAMNet) | 10% (solo count) | 20% (count + score) | "Animal" como top-1 es la señal más directa de contenido biológico |
| Acoustic diversity | 15% (threshold alto) | 20% (threshold bajo) | Capturar más tipos de vocalización indica escena acústica más rica |
| Humpback coverage | 20% | 15% | Sigue importante pero más balanceado |
| Cross-model agreement | 10% | 15% | Convergencia entre modelos es clave para confiabilidad |
| Humpback peak | 10% | 5% | 99/100 archivos detectan humpback — bajo poder discriminante |
| YAMNet top quality | — | 5% (nueva) | Distinguir "Animal" vs "Speech" como clase principal |

## Diseño del Sistema de Ponderación v2

### Principios

1. **Señal biológica clara > pico de especie aislado**: Cuando YAMNet clasifica un audio como "Animal" es una señal más fuerte que un spike de 0.98 en una ventana de 5 segundos
2. **Persistencia temporal > picos transitorios**: La presencia sostenida (mean score alto) vale tanto como el pico máximo
3. **Diversidad acústica = riqueza del ecosistema**: Más tipos de sonido = más valor científico
4. **Convergencia de modelos > modelo individual**: Tres modelos coincidiendo es más confiable que uno solo con score alto
5. **Discriminación efectiva**: Las dimensiones con poca variabilidad entre archivos (e.g., humpback peak) reciben menos peso

### Las 7 Dimensiones

El score final es una combinación lineal ponderada de 7 dimensiones, cada una normalizada a [0, 1]:

```
Score = Σ (dimensión_i × peso_i) × 100
```

---

#### Dimensión 1: Presencia Sostenida de Cetáceos (20%)

```
whale_sustained = 0.5 × max_score + 0.5 × min(sum_of_mean_scores × 5, 1.0)
```

**¿Por qué composite y no solo max?** Porque el score máximo captura el **mejor momento** del archivo, pero el mean score captura la **presencia promedio** a lo largo de toda la grabación. Un archivo con:
- max = 0.34, mean_sum = 0.025 (presencia moderada pero persistente)
- vale más que uno con max = 0.98, mean_sum = 0.001 (un spike aislado)

El factor ×5 en los means compensa que los mean scores son típicamente 10-100× menores que los max scores (porque las vocalizaciones de cetáceos son intermitentes, no continuas).

**Rango observado**: 0.0 – 0.93

---

#### Dimensión 2: Riqueza de Señal Biológica YAMNet (20%)

```
bio_richness = 0.5 × min(n_bio_detections / 8, 1.0) + 0.5 × min(sum_bio_scores / 1.0, 1.0)
```

**¿Por qué 20% (era 10%)?** El análisis de los espectrogramas reveló que los archivos donde YAMNet clasifica el top-1 como "Animal" o "Wild animals" tienen visualmente las señales biológicas más claras y estructuradas. En contraste, archivos donde el top-1 es "Speech" o "Silence" — aunque tengan picos altos de multispecies — tienen señales más ruidosas y esporádicas.

Esta dimensión combina:
- **Cantidad** de detecciones biológicas (normalizada a 8): más tipos de sonido biológico detectados = señal más rica
- **Intensidad** de esas detecciones (suma de scores): detecciones más fuertes = señal más clara

Aunque YAMNet fue entrenado con audio terrestre, sus clasificaciones "Animal", "Wild animals", "Insect" en audio subacuático correlacionan fuertemente con vocalizaciones marinas visibles en los espectrogramas.

**Rango observado**: 0.0 – 1.0

---

#### Dimensión 3: Diversidad Acústica (20%)

```
diversity = min((n_especies + n_tipos_vocalización) / 7, 1.0)
```

Donde:
- `n_especies`: especies con score ≥ 0.01 (Oo, Mn, Eg, Be, Bp, Bm, Ba)
- `n_tipos_vocalización`: tipos con score ≥ 0.01 (Call, Echolocation, Whistle, Gunshot, Upcall)

**Cambios vs v1**:
- Threshold de vocalizaciones bajó de 0.05 a **0.01**: un silbido débil (Whistle = 0.02) sigue indicando que hay delfines presentes
- Especies y vocalizaciones pesan **igual**: un tipo de vocalización nuevo es tan informativo como una especie nueva en el contexto de audio sin labels
- Normalización a 7.0 (máximo observado en los datos)

**Rango observado**: 0.0 – 1.0

---

#### Dimensión 4: Cobertura Temporal de Humpback (15%)

```
humpback_coverage = fracción de ventanas de 1s con score ≥ 0.1
```

**¿Por qué bajó de 20% a 15%?** Sigue siendo importante (presencia sostenida > transitoria), pero se redistribuyó peso hacia bio_richness y diversity que demostraron ser mejores discriminantes. La cobertura de humpback complementa las otras dimensiones sin dominar.

**Rango observado**: 0.0 – 0.71

---

#### Dimensión 5: Acuerdo Entre Modelos (15%)

```
agreement = 0.30×(YAMNet bio) + 0.10×(YAMNet marine) + 0.35×(multispecies whale) + 0.25×(humpback)
```

**¿Por qué subió de 10% a 15%?** Porque la convergencia es especialmente valiosa con audio sin labels. Cuando tres modelos **independientes** (diferentes arquitecturas, datos de entrenamiento, frecuencias de muestreo) coinciden, la probabilidad de falso positivo disminuye multiplicativamente.

Los sub-pesos internos reflejan la especificidad de cada modelo:
- Multispecies (0.35): más específico para cetáceos
- YAMNet bio (0.30): confirma que el audio "suena biológico"
- Humpback (0.25): detector especializado
- YAMNet marine (0.10): confirma contexto acuático

---

#### Dimensión 6: Confianza Pico de Humpback (5%)

```
humpback_peak = max_score del detector de humpback
```

**¿Por qué solo 5%?** 99 de 100 archivos tienen detección de humpback (max_score > 0.1), y la mayoría tiene scores > 0.5. Esta dimensión es **casi uniforme** en nuestro dataset, lo que significa que no discrimina bien entre archivos. Le damos peso mínimo para no inflar artificialmente los scores.

---

#### Dimensión 7: Calidad de Clasificación Top YAMNet (5%)

```
yamnet_top_quality = min(top1_score × 3.0, 1.0)  si top-1 es clase biológica
                   = 0.0                           si top-1 es "Speech", "Silence", etc.
```

**Dimensión nueva en v2**. Captura una señal importante: cuando el **top-1** de YAMNet (la clase más probable para todo el archivo) es una clase biológica como "Animal" o "Wild animals", eso indica que la mayor parte del audio está dominada por sonidos biológicos. En contraste, si top-1 es "Speech" (modelo confundiendo canto de ballena con habla) o "Silence", las detecciones biológicas son probablemente eventos aislados dentro de un archivo mayormente silencioso.

Clases biológicas reconocidas: Animal, Wild animals, Insect, Bird, Frog, Cricket, Whale vocalization, Livestock, Cattle, Fowl, Roar.

---

## Clasificación en Niveles (Tiers)

El score final (0–100) se clasifica en 5 niveles de prioridad (umbrales ajustados en v2 para reflejar la nueva distribución):

| Nivel | Score | Interpretación | Acción Recomendada |
|-------|-------|---------------|-------------------|
| **CRITICAL** | ≥ 65 | Contenido excepcionalmente rico: múltiples dimensiones altas | Revisión prioritaria inmediata |
| **HIGH** | ≥ 45 | Señales biológicas claras desde múltiples modelos | Revisión detallada |
| **MODERATE** | ≥ 25 | Señales detectadas con confianza moderada | Revisión cuando sea posible |
| **LOW** | ≥ 10 | Señales débiles o de un solo modelo | Revisión opcional |
| **MINIMAL** | < 10 | Poca o ninguna evidencia biológica | Baja prioridad |

### Distribución observada (v2)

| Nivel | Archivos |
|-------|----------|
| CRITICAL | 3 |
| HIGH | 35 |
| MODERATE | 40 |
| LOW | 19 |
| MINIMAL | 3 |

## Comparación v1 vs v2

### Cambios de posición más significativos

| Archivo | Rank v1 | Rank v2 | Razón |
|---------|---------|---------|-------|
| 190807_3963 | #19 | **#5** | YAMNet top="Animal" (8 bio dets), señal biológica claramente estructurada |
| 190807_3970 | #12 | **#4** | 8 bio dets, alta diversidad acústica |
| 190808_4237 | #24 | **#9** | top="Wild animals", 6 bio dets, presencia sostenida |
| 190807_4100 | #11 | #38 | Spike Orca 0.93 pero 0 bio dets YAMNet, top="Silence" |
| 190808_4352 | #14 | #56 | Spike Orca 0.97 pero 0 bio dets YAMNet |

**Patrón**: Los archivos que **suben** son los que tienen señales biológicas claras y sostenidas visibles en el espectrograma. Los que **bajan** tenían spikes aislados de alta intensidad pero sin la "firma" biológica general que confirma contenido valioso.

## Limitaciones y Consideraciones

### Sesgos conocidos

1. **Sesgo hacia orcas en multispecies**: El modelo tiene alta sensibilidad para *Orcinus orca*, lo que puede inflar scores para archivos con patrones acústicos similares.

2. **Sesgo geográfico**: Los modelos fueron entrenados con datos del Atlántico Norte y Pacífico Norte. Las especies de Galápagos (ballena jorobada del Pacífico Sur, delfín nariz de botella, ballena de Bryde) pueden no estar perfectamente representadas.

3. **Humpback casi universal**: 99/100 archivos detectan humpback, reduciendo el poder discriminante de esa dimensión. Puede indicar presencia real generalizada o sesgo del detector hacia patrones de baja frecuencia.

4. **YAMNet fuera de dominio**: Entrenado con audio terrestre (YouTube). Sin embargo, empíricamente sus clasificaciones "Animal" correlacionan bien con vocalizaciones marinas visibles en espectrogramas de estos datos.

5. **Transferencia de dominio de YAMNet**: Cuando YAMNet clasifica audio subacuático como "Insect" o "Cricket", probablemente está respondiendo a patrones rítmicos de snapping shrimp o coros de peces, no a insectos reales.

### Interpretación responsable

- Los scores **NO son probabilidades** de presencia de especies
- Un score alto indica **mayor valor potencial para revisión humana**, no certeza científica
- La clasificación final siempre debe ser validada por un experto en bioacústica marina
- Los archivos en niveles bajos no deben descartarse — pueden contener especies o patrones no cubiertos por los modelos

### Calibración futura

A medida que los investigadores revisen y anoten archivos manualmente, estos pesos deberían recalibrarse usando:
1. Correlación entre scores del modelo y anotaciones de expertos
2. Análisis de falsos positivos/negativos por dimensión
3. Ajuste de thresholds específicos para el ecosistema de Galápagos
4. Posible incorporación de Perch 2.0 embeddings como dimensión adicional

## Uso

```bash
cd dataset2
python3 -u rank_biological_importance.py
```

Genera:
- `output2/ranked_importance.json` — resultados completos con scores por dimensión
- `output2/ranked_importance.csv` — CSV simplificado para importar en hojas de cálculo