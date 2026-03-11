"""
pipeline/stage6_cluster.py — Stage 6: Audio embeddings + unsupervised clustering.

Extrae embeddings acústicos de 1024 dimensiones con BirdNET (via opensoundscape),
reduce a 2D con UMAP y agrupa con HDBSCAN. Produce un cluster_id por clip y
un mapa visual de similaridad acústica.

Output por clip:
  cluster_id           — int (-1 = outlier/ruido)
  umap_x, umap_y       — coordenadas 2D
  cluster_size         — cuántos clips en ese cluster
  cluster_dominant_band — banda espectral más común en el cluster (de Stage 5)

Uso:
    from pipeline.stage6_cluster import run_clustering
    clusters = run_clustering(clip_paths, output_dir=Path("pipeline_output/clusters"))
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ─── Hiperparámetros ─────────────────────────────────────────────────────────

_UMAP_N_COMPONENTS  = 2
_UMAP_N_NEIGHBORS   = 5     # bajo porque los datasets son pequeños
_UMAP_MIN_DIST      = 0.1
_HDBSCAN_MIN_CLUSTER = 3    # mínimo 3 clips por cluster


def _extract_birdnet_embeddings(wav_paths: List[Path]) -> np.ndarray:
    """
    Extrae embeddings BirdNET para cada WAV usando opensoundscape.
    Devuelve array (N, D) donde D suele ser 1024.
    Usa GPU automáticamente si CUDA disponible.
    """
    try:
        from opensoundscape.ml.cnn import load_model
        from opensoundscape import Audio
    except ImportError:
        raise ImportError(
            "opensoundscape no está instalado. "
            "Instala con: pip install opensoundscape>=0.10"
        )

    embeddings = []
    for path in wav_paths:
        try:
            audio = Audio.from_file(str(path), sample_rate=48_000)
            # opensoundscape BirdNET embedding: shape (n_windows, 1024)
            # tomamos la media temporal como representación del clip
            emb = audio.birdnet_embeddings()
            if emb is not None and len(emb) > 0:
                embeddings.append(np.mean(emb, axis=0))
            else:
                embeddings.append(np.zeros(1024))
        except Exception as exc:
            logger.warning("  %s — embedding error: %s", path.name, exc)
            embeddings.append(np.zeros(1024))

    result = np.array(embeddings, dtype=np.float32)
    if not any(np.any(e != 0) for e in result):
        raise RuntimeError("birdnet_embeddings API incompatible — todos los clips fallaron")
    return result


def _extract_librosa_embeddings(wav_paths: List[Path]) -> np.ndarray:
    """
    Fallback: MFCCs + spectral features con librosa (no requiere opensoundscape).
    Devuelve array (N, 148).
    """
    import librosa

    embeddings = []
    for path in wav_paths:
        try:
            y, sr = librosa.load(str(path), sr=None, mono=True, duration=30.0)
            mfcc   = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            melban = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64)
            meldb  = librosa.power_to_db(melban)

            feat = np.concatenate([
                np.mean(mfcc, axis=1),   np.std(mfcc, axis=1),    # 80
                np.mean(chroma, axis=1), np.std(chroma, axis=1),  # 24
                np.mean(meldb, axis=1),  np.std(meldb, axis=1),   # 128 → truncado
            ])
            embeddings.append(feat[:148])
        except Exception as exc:
            logger.warning("  %s — librosa error: %s", path.name, exc)
            embeddings.append(np.zeros(148))

    return np.array(embeddings, dtype=np.float32)


def _reduce_umap(embeddings: np.ndarray) -> np.ndarray:
    """UMAP reduction a 2D."""
    from umap import UMAP

    n = len(embeddings)
    n_neighbors = min(_UMAP_N_NEIGHBORS, n - 1) if n > 1 else 1
    reducer = UMAP(
        n_components=_UMAP_N_COMPONENTS,
        n_neighbors=n_neighbors,
        min_dist=_UMAP_MIN_DIST,
        random_state=42,
        verbose=False,
    )
    return reducer.fit_transform(embeddings)


def _cluster_hdbscan(embedding_2d: np.ndarray) -> np.ndarray:
    """HDBSCAN clustering sobre el espacio 2D de UMAP."""
    import hdbscan

    n = len(embedding_2d)
    min_size = min(_HDBSCAN_MIN_CLUSTER, max(2, n // 4))
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_size, min_samples=1)
    return clusterer.fit_predict(embedding_2d)


def _dominant_band_for_cluster(
    cluster_id: int,
    labels: np.ndarray,
    filenames: List[str],
    soundscape: Optional[Dict[str, dict]],
) -> str:
    """Retorna la banda dominante más común en el cluster."""
    if soundscape is None:
        return 'UNKNOWN'
    mask = labels == cluster_id
    bands = [
        soundscape.get(filenames[i], {}).get('dominant_band', 'UNKNOWN')
        for i in range(len(filenames)) if mask[i]
    ]
    if not bands:
        return 'UNKNOWN'
    counts = {}
    for b in bands:
        counts[b] = counts.get(b, 0) + 1
    return max(counts, key=counts.get)


def _plot_umap(
    embedding_2d: np.ndarray,
    labels: np.ndarray,
    filenames: List[str],
    output_dir: Path,
) -> None:
    """Genera umap_clusters.png con colores por cluster."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
    except ImportError:
        return

    unique_labels = sorted(set(labels))
    n_clusters = len([l for l in unique_labels if l >= 0])
    colors = cm.tab10(np.linspace(0, 1, max(n_clusters, 1)))
    color_map = {l: colors[i % len(colors)] for i, l in enumerate(unique_labels) if l >= 0}
    color_map[-1] = (0.5, 0.5, 0.5, 0.4)  # gris para outliers

    fig, ax = plt.subplots(figsize=(8, 6))
    for label in unique_labels:
        mask = labels == label
        color = color_map[label]
        lbl = f'Cluster {label}' if label >= 0 else 'Outliers'
        ax.scatter(
            embedding_2d[mask, 0], embedding_2d[mask, 1],
            c=[color], label=lbl, s=60, alpha=0.85, edgecolors='white', linewidths=0.5,
        )
    # Anotar con nombres cortos
    for i, fname in enumerate(filenames):
        ax.annotate(
            Path(fname).stem[:12],
            (embedding_2d[i, 0], embedding_2d[i, 1]),
            fontsize=5, alpha=0.6,
        )

    ax.set_title(f'UMAP Audio Clusters ({n_clusters} clusters, {(labels==-1).sum()} outliers)')
    ax.set_xlabel('UMAP-1')
    ax.set_ylabel('UMAP-2')
    ax.legend(fontsize=7, loc='best')
    plt.tight_layout()
    out = output_dir / 'umap_clusters.png'
    fig.savefig(out, dpi=130)
    plt.close(fig)
    logger.info("  → %s", out)


def run_clustering(
    wav_paths: List[Path],
    output_dir: Path,
    soundscape: Optional[Dict[str, dict]] = None,
) -> Dict[str, dict]:
    """
    Extrae embeddings, aplica UMAP + HDBSCAN y guarda resultados.

    Args:
        wav_paths:  Lista de rutas WAV (clips del Stage 0).
        output_dir: Carpeta destino para clusters.json, embeddings.npy y PNG.
        soundscape: (opcional) Dict de Stage 5 para enriquecer labels de cluster.

    Returns:
        Dict {filename: cluster_info}
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if not wav_paths:
        logger.warning("Stage 6 — sin clips, saltando clustering.")
        return {}

    filenames = [p.name for p in wav_paths]
    logger.info("Stage 6 — Embeddings + clustering (%d clips)", len(wav_paths))

    # ── 1. Feature extraction ────────────────────────────────────────────────
    logger.info("  Extrayendo embeddings…")
    try:
        embeddings = _extract_birdnet_embeddings(wav_paths)
        logger.info("  BirdNET embeddings: shape=%s", embeddings.shape)
    except Exception as exc:
        logger.warning("  BirdNET no disponible (%s) → fallback a librosa MFCCs", exc)
        embeddings = _extract_librosa_embeddings(wav_paths)
        logger.info("  Librosa embeddings: shape=%s", embeddings.shape)

    # Guardar embeddings crudos
    emb_out = output_dir / 'embeddings.npy'
    np.save(str(emb_out), embeddings)
    logger.info("  → %s", emb_out)

    # ── 2. UMAP ──────────────────────────────────────────────────────────────
    if len(wav_paths) < 2:
        logger.warning("  Muy pocos clips para UMAP/clustering, devolviendo cluster 0 para todos.")
        clusters = {fname: {'cluster_id': 0, 'umap_x': 0.0, 'umap_y': 0.0,
                            'cluster_size': len(wav_paths),
                            'cluster_dominant_band': 'UNKNOWN'}
                    for fname in filenames}
    else:
        logger.info("  Reduciendo con UMAP…")
        try:
            embedding_2d = _reduce_umap(embeddings)
        except Exception as exc:
            logger.warning("  UMAP falló (%s) → usando PCA como fallback", exc)
            from sklearn.decomposition import PCA
            embedding_2d = PCA(n_components=2).fit_transform(embeddings)

        # ── 3. HDBSCAN ───────────────────────────────────────────────────────
        logger.info("  Clustering con HDBSCAN…")
        try:
            labels = _cluster_hdbscan(embedding_2d)
        except Exception as exc:
            logger.warning("  HDBSCAN falló (%s) → asignando cluster único", exc)
            labels = np.zeros(len(wav_paths), dtype=int)

        # ── 4. Cluster sizes ──────────────────────────────────────────────────
        label_counts = {}
        for l in labels:
            label_counts[int(l)] = label_counts.get(int(l), 0) + 1

        # ── 5. Dominant band por cluster ──────────────────────────────────────
        unique_clusters = set(labels)
        dominant_per_cluster = {
            c: _dominant_band_for_cluster(c, labels, filenames, soundscape)
            for c in unique_clusters if c >= 0
        }
        dominant_per_cluster[-1] = 'UNKNOWN'

        # ── 6. Ensamblar resultado ────────────────────────────────────────────
        clusters = {}
        for i, fname in enumerate(filenames):
            cid = int(labels[i])
            clusters[fname] = {
                'cluster_id':            cid,
                'umap_x':                round(float(embedding_2d[i, 0]), 4),
                'umap_y':                round(float(embedding_2d[i, 1]), 4),
                'cluster_size':          label_counts.get(cid, 1),
                'cluster_dominant_band': dominant_per_cluster.get(cid, 'UNKNOWN'),
            }

        # ── 7. Visualización ──────────────────────────────────────────────────
        _plot_umap(embedding_2d, labels, filenames, output_dir)

        n_clusters = len([l for l in set(labels) if l >= 0])
        n_outliers = int((labels == -1).sum())
        logger.info("  Clusters: %d  Outliers: %d", n_clusters, n_outliers)

    # ── 8. Guardar JSON ───────────────────────────────────────────────────────
    json_out = output_dir / 'clusters.json'
    json_out.write_text(json.dumps(clusters, indent=2))
    logger.info("Stage 6 done — clusters.json escrito")
    logger.info("  → %s", json_out)

    return clusters
