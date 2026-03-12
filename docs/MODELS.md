# Modelos del Pipeline — Dragon Ocean Analyzer

Documentación de los 8 modelos utilizados: 6 de ensemble para detección bioacústica y 2 para clustering de similitud acústica.

---

## Modelos de Ensemble (Detección Bioacústica)

### 1. Perch 2.0 — Google Bioacoustic Classifier

**Publicación:** 2023 (v1 en *Scientific Reports*); v2 presentado en NeurIPS 2025 Workshop on AI for Non-Human Animal Communication (arXiv:2508.04665).

**Autores / Institución:** Burooj Ghani, Tom Denton, Stefan Kahl, Holger Klinck — Google Research + Cornell Lab of Ornithology (v1). Bart van Merriënboer et al. — Google DeepMind (v2).

**Entrenamiento:** Entrenado en Xeno-canto y otros datasets de vocalización de fauna silvestre. La v2 amplía el corpus a 14,597 especies (aves, mamíferos, anfibios, insectos) usando auto-destilación y aprendizaje por prototipos. Produce vectores de embedding de 1536 dimensiones y scores de clasificación para miles de especies.

**Fortalezas:**
- Embeddings de transferencia excepcionales; supera modelos entrenados específicamente en mamíferos marinos en tareas zero-shot.
- Cubre 14,597+ especies; estado del arte en benchmarks BirdSet y BEANS.
- Diseñado para clasificación few-shot en taxones nuevos con pocas muestras.

**Debilidades:**
- Entrenado principalmente en aves terrestres; la cobertura marina es limitada.
- No produce conteos de eventos ni identificación individual.
- La razón teórica por la que funciona bien fuera de aves está descrita como hipótesis, no como conclusión validada.

**Cita:**
> Ghani, B., Denton, T., Kahl, S., & Klinck, H. (2023). Global birdsong embeddings enable superior transfer learning for bioacoustic classification. *Scientific Reports*, 13, 22876. https://doi.org/10.1038/s41598-023-49989-z

---

### 2. Multispecies Whale Model v2 — Google / NOAA

**Publicación:** Sin paper dedicado independiente. Extensión directa de Allen et al. (2021), desarrollada internamente por Google Research en colaboración con NOAA PIFSC. Disponible en Kaggle desde 2023.

**Autores / Institución:** Matt Harvey, Aren Jansen, Lauren Harrell, Julie Cattiau (Google Research) + NOAA Pacific Islands Fisheries Science Center.

**Entrenamiento:** Extiende la arquitectura ResNet-CNN + Per-Channel Energy Normalization (PCEN) del detector de ballenas jorobadas. Entrenado sobre registros multi-año de hidrófonos HARP de NOAA en multiple cuencas oceánicas. Usa aprendizaje activo para dirigir la anotación hacia tipos de error subrepresentados. Clasifica 7 especies de cetáceos y 5 tipos de vocalización en ventanas deslizantes.

**Fortalezas:**
- Detecta 7 especies y 5 tipos de vocalización en un único modelo.
- AUC-ROC ~0.99 en ballena jorobada; objetivos similares en otras especies.
- Procesamiento pasivo a escala de cientos de miles de horas de grabación.

**Debilidades:**
- No existe paper peer-reviewed exclusivo para la v2 multiespecie.
- Rendimiento muy variable entre especies según la disponibilidad de datos de entrenamiento.
- Entrenado principalmente en el Pacífico Norte; la generalización a otras cuencas (incluyendo Galápagos, Pacífico Sur) puede degradarse.

**Cita:**
> Allen, A.N., Harvey, M., Harrell, L., Jansen, A., Merkens, K.P., Wall, C.C., Cattiau, J., & Oleson, E.M. (2021). A convolutional neural network for automated detection of humpback whale song. *Frontiers in Marine Science*, 8, 607321. https://doi.org/10.3389/fmars.2021.607321

---

### 3. Humpback Whale Detector — Google / NOAA

**Publicación:** Marzo 2021. *Frontiers in Marine Science*, vol. 8. DOI: 10.3389/fmars.2021.607321.

**Autores / Institución:** Ann N. Allen, Karlina P. Merkens, Erin M. Oleson (NOAA PIFSC); Matt Harvey, Aren Jansen, Lauren Harrell, Julie Cattiau (Google); Carrie C. Wall (University of Colorado Boulder / NOAA NCEI).

**Entrenamiento:** Corpus de 187,000+ horas de grabaciones de 13 sitios del Pacífico Norte (2005–2019) de hidrófonos HARP de fondo marino. Audio convertido a mel-espectrogramas; clasificador binario CNN tipo ResNet (presencia/ausencia de canto de ballena jorobada en ventanas de 75 segundos). PCEN reemplaza log-mel para mayor robustez en condiciones variables. El avance clave fue el **aprendizaje activo**: rondas iterativas donde las predicciones del modelo dirigían la anotación experta hacia los errores más raros.

**Fortalezas:**
- Precisión promedio 0.97; AUC-ROC promedio 0.992 en sitios y años de prueba.
- Generaliza sin fine-tuning específico por sitio.
- Permitió descubrir cantos de ballena jorobada en Kingman Reef (5° N), un registro sin precedentes.

**Debilidades:**
- Clasificación binaria por segmento únicamente: no cuenta llamados ni identifica individuos.
- Entrenado en población del Pacífico Norte; validación en el Hemisferio Sur o Atlántico incompleta.
- Susceptible a falsos positivos con ruido de motores en el rango 100–500 Hz.

**Cita:**
> Allen, A.N., Harvey, M., Harrell, L., Jansen, A., Merkens, K.P., Wall, C.C., Cattiau, J., & Oleson, E.M. (2021). A convolutional neural network for automated detection of humpback whale song. *Frontiers in Marine Science*, 8, 607321. https://doi.org/10.3389/fmars.2021.607321

---

### 4. NatureLM-BEATs — Earth Species Project

**Publicación:** Noviembre 2024. arXiv:2411.07186. Basado en BEATs (Chen et al., ICML 2023, arXiv:2212.09058).

**Autores / Institución:** David Robinson, Marius Miron, Masato Hagiwara et al. — **Earth Species Project**. La arquitectura BEATs subyacente fue desarrollada por Sanyuan Chen, Yu Wu et al. — **Microsoft Research**.

**Entrenamiento:** Dos capas de entrenamiento:
- *BEATs*: auto-supervisado iterativo con predicción de tokens acústicos enmascarados (masked token prediction). Itera entre entrenar un tokenizador acústico y un transformer de audio, mejorando ambos en cada ronda.
- *NatureLM-audio*: modelo audio-lenguaje grande entrenado en pares texto-audio curados en bioacústica, habla y música; transfiere representaciones de dominios con mayor disponibilidad de datos para compensar la escasez de datos bioacústicos.

**Fortalezas:**
- Estado del arte en AudioSet-2M (50.6% mAP) y ESC-50 (98.1%) para BEATs.
- Primer modelo audio-lenguaje concebido específicamente para bioacústica.
- Clasificación zero-shot de especies no vistas durante el entrenamiento.

**Debilidades:**
- El entrenamiento iterativo de BEATs multiplica el costo computacional respecto a métodos SSL de un solo paso.
- La tokenización de audio es intrínsecamente más difícil que la de texto: no existen unidades discretas naturales equivalentes a fonemas.
- La escasez de datos bioacústicos etiquetados sigue siendo una limitante estructural.

**Cita:**
> Robinson, D., Miron, M., Hagiwara, M., Weck, B., Keen, S., Alizadeh, M., Narula, G., Geist, M., & Pietquin, O. (2024). NatureLM-audio: an Audio-Language Foundation Model for Bioacoustics. arXiv:2411.07186. https://arxiv.org/abs/2411.07186

---

### 5. BioLingual — CLAP para Bioacústica

**Publicación:** Agosto 2023. arXiv:2308.04978 (preprint; sin publicación peer-reviewed en revista o conferencia a la fecha).

**Autores / Institución:** David Robinson, Adelaide Robinson, Lily Akrapongpisak (Earth Species Project).

**Entrenamiento:** Basado en **CLAP (Contrastive Language-Audio Pretraining)** con el encoder de audio HTSAT-unfused. Entrenado de forma contrastiva sobre **AnimalSpeak**: más de 1 millón de pares audio-descripción de texto cubriendo 1,000+ especies y contextos de vocalización. La pérdida contrastiva alinea los embeddings de audio y texto en un espacio latente compartido, habilitando clasificación zero-shot mediante consultas en lenguaje natural en inferencia.

**Fortalezas:**
- Clasificación zero-shot sobre 1,000+ especies sin etiquetas específicas por tarea.
- Estado del arte en 9 tareas del benchmark BEANS tras fine-tuning.
- Las consultas son texto libre: no se necesitan clases predefinidas.
- Pesos, dataset AnimalSpeak y código de entrenamiento publicados abiertamente.

**Debilidades:**
- El rendimiento está acotado por la calidad de las descripciones en AnimalSpeak; captions genéricos degradan el alineamiento.
- No es un modelo de audio general: diseñado exclusivamente para sonidos animales.
- Sin publicación peer-reviewed: los resultados aún no han pasado revisión formal.
- Procesa máximo 30 segundos de audio por clip.

**Cita:**
> Robinson, D., Robinson, A., & Akrapongpisak, L. (2023). Transferable Models for Bioacoustics with Human Language Supervision. arXiv:2308.04978. https://arxiv.org/abs/2308.04978

---

### 6. Dasheng — Self-Supervised Audio at Scale

**Publicación:** Junio 2024. *Proceedings of Interspeech 2024*. arXiv:2406.06992.

**Autores / Institución:** Heinrich Dinkel, Zhiyong Yan, Yongqing Wang, Junbo Zhang, Yujun Wang, Bin Wang — organización `mispeech` (HuggingFace / GitHub).

**Entrenamiento:** Encoder auto-supervisado basado en **Masked Autoencoder (MAE)** para audio. Escala el paradigma MAE a **272,000 horas** de audio (VGGSound + AudioSet + MTG-Jamendo + ACAV100M), superando en un orden de magnitud a trabajos anteriores (~10,000 horas). Disponible en tres tamaños: Base (86M parámetros), 0.6B y 1.2B. Entrenamiento con `bf16` mixed precision vía Hugging Face Accelerate. Fine-tuning con clasificador LayerNorm + Linear alcanza 49.7 mAP en AudioSet.

**Fortalezas:**
- Estado del arte en el benchmark HEAR a través de múltiples dominios de audio.
- Las representaciones aprendidas contienen información rica de habla, música y sonido ambiental.
- Instalable con `pip install dasheng`; licencia Apache 2.0.
- Tres tamaños disponibles para balance cómputo/rendimiento.

**Debilidades:**
- Persiste una brecha de generalización entre habla y otros dominios de sonido, aunque reducida.
- El modelo de 1.2B requiere memoria GPU significativa para inferencia.
- No está diseñado específicamente para bioacústica underwater: sus representaciones son de propósito general.

**Cita:**
> Dinkel, H., Yan, Z., Wang, Y., Zhang, J., Wang, Y., & Wang, B. (2024). Scaling up masked audio encoder learning for general audio classification. *Proceedings of Interspeech 2024*. arXiv:2406.06992. https://arxiv.org/abs/2406.06992

---

## Modelos de Clustering

Los embeddings de 768 dimensiones generados por NatureLM-BEATs en Stage 4 se proyectan a 2D con UMAP y se agrupan con HDBSCAN para producir un mapa de similitud acústica entre clips.

---

### 7. UMAP — Reducción de Dimensionalidad

**Publicación:** Febrero 2018. arXiv:1802.03426 (stat.ML / cs.LG). Software paper en *Journal of Open Source Software*, 2018.

**Autores / Institución:** Leland McInnes, John Healy, James Melville — Tutte Institute for Mathematics and Computing (Canadá).

**Algoritmo:** Opera en dos fases:
1. **Construcción del grafo:** Modela los datos como un complejo simplicial difuso (fuzzy simplicial complex). Para cada punto calcula una métrica riemanniana local de modo que la bola unitaria alcance el k-ésimo vecino más cercano. Los pesos de aristas conflictivos entre vecindades locales se reconcilian con unión probabilística: `w = a + b − a·b`.
2. **Optimización del embedding:** Minimiza la entropía cruzada entre las estructuras topológicas en alta y baja dimensión usando gradiente estocástico descendente con muestreo negativo e inicialización espectral.

**Fortalezas:**
- Preserva más estructura global que t-SNE manteniendo calidad de visualización comparable.
- Muy superior en velocidad de ejecución en datasets grandes.
- Soporta extensiones supervisadas, semi-supervisadas y por métrica personalizada.
- Sin restricción en la dimensión de salida: útil para extracción de features, no solo visualización.

**Debilidades:**
- Sensible a los hiperparámetros `n_neighbors` y `min_dist`; sin criterio formal para elegirlos.
- Las distancias inter-cluster en el gráfico UMAP no son interpretables como distancias reales en alta dimensión.
- Estocástico: sin semilla fija, los resultados varían entre ejecuciones.
- No soporta datos en streaming; requiere re-entrenamiento completo para nuevos puntos.

**Cita:**
> McInnes, L., Healy, J., & Melville, J. (2018). UMAP: Uniform Manifold Approximation and Projection for Dimension Reduction. arXiv:1802.03426. https://arxiv.org/abs/1802.03426

---

### 8. HDBSCAN — Clustering Jerárquico por Densidad

**Publicación:** 2013. *Proceedings of the 17th Pacific-Asia Conference on Knowledge Discovery and Data Mining (PAKDD 2013)*. Lecture Notes in Computer Science, vol. 7819, pp. 160–172. Springer. DOI: 10.1007/978-3-642-37456-2_14.

**Autores / Institución:** Ricardo J.G.B. Campello, Davoud Moulavi, Joerg Sander — University of Alberta (Canadá) y University of São Paulo (Brasil).

**Algoritmo:** Construye una jerarquía de clusters densa y extrae una partición plana por estabilidad. Cinco pasos:
1. Transforma distancias con **mutual reachability distance**: `max(core_dist(p), core_dist(q), d(p,q))`, expandiendo regiones dispersas.
2. Construye el **árbol de expansión mínima (MST)** sobre el grafo de reachability.
3. Genera la **jerarquía de clusters** removiendo aristas del MST en orden descendente de peso.
4. **Condensa el árbol** usando `min_cluster_size`: divisiones que crean clusters más pequeños se descarten como ruido.
5. Extrae clusters por **estabilidad**: `Σ(λ_death − λ_birth)` por punto miembro; se seleccionan los clusters con mayor estabilidad que la suma de sus hijos.

**Fortalezas:**
- Maneja clusters de **densidad variable** sin requerir un epsilon fijo (limitación de DBSCAN).
- Etiqueta puntos ruidosos naturalmente en lugar de forzarlos a un cluster.
- Produce **probabilidades de pertenencia suaves** por punto.
- Solo requiere un parámetro principal: `min_cluster_size`.

**Debilidades:**
- Sensible a `min_cluster_size` y `min_samples`: valores bajos fragmentan clusters reales; valores altos descartan clusters legítimos pequeños como ruido.
- Costoso computacionalmente en datasets muy grandes (construcción del MST O(n² log n) en el peor caso).
- La maldición de la dimensionalidad degrada la mutual reachability distance en espacios de alta dimensión (como los embeddings de 768D antes de proyectar con UMAP).

**Cita:**
> Campello, R.J.G.B., Moulavi, D., & Sander, J. (2013). Density-Based Clustering Based on Hierarchical Density Estimates. In: *Advances in Knowledge Discovery and Data Mining: PAKDD 2013*. Lecture Notes in Computer Science, vol. 7819, pp. 160–172. Springer. https://doi.org/10.1007/978-3-642-37456-2_14
