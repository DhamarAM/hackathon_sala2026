"""
backend/run.py — Entrypoint principal del backend integrado.

Flujo completo:
    Stage 0:   AudioClipper      → recorta WAVs a segmentos activos
    Stage 1-3: Cascade           → YAMNet + Multispecies Whale + Humpback
    Stage 5:   Soundscape        → índices acústicos marinos (sin GPU)
    Stage 6:   Embeddings+Cluster→ BirdNET/MFCC + UMAP + HDBSCAN (GPU opcional)
    Stage 4:   Enhanced Ranking  → score 9-dimensional + CSV/JSON

Uso:
    python -m backend.run --source <carpeta_con_wavs>

    # Opciones:
    python -m backend.run --source data/raw --output outputs
    python -m backend.run --source data/raw --skip-clip      # usa clips previos
    python -m backend.run --source data/raw --skip-cascade   # solo rankea
    python -m backend.run --source data/raw --no-cluster     # sin Stage 6 (sin GPU)
    python -m backend.run --skip-clip --skip-cascade --no-cluster  # solo Stages 5+4
"""

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def run(
    source_dir: Path,
    output_dir: Path,
    skip_clip: bool = False,
    skip_cascade: bool = False,
    skip_soundscape: bool = False,
    skip_cluster: bool = False,
    no_cluster: bool = False,
) -> dict:
    """
    Ejecuta el backend completo o parcial.

    Args:
        source_dir:      Carpeta con los WAVs originales.
        output_dir:      Carpeta raíz para todos los outputs.
        skip_clip:       Si True, asume clips ya existentes en output_dir/clips/.
        skip_cascade:    Si True, asume resultados del cascade ya existentes.
        skip_soundscape: Si True, carga soundscape.json existente (Stage 5).
        skip_cluster:    Si True, carga clusters.json existente (Stage 6).
        no_cluster:      Si True, no corre Stage 6 en absoluto.

    Returns:
        Dict con {clips, results, soundscape, clusters, rankings}.
    """
    from backend.stage0_clip      import AudioClipper
    from backend.stage1_3_cascade import run_cascade
    from backend.stage4_rank      import rank_results
    from backend.stage5_soundscape import run_soundscape
    from backend.stage6_cluster    import run_clustering

    clips_dir     = output_dir / "clips"
    analysis_dir  = output_dir / "analysis"
    soundscape_dir = output_dir / "soundscape"
    cluster_dir   = output_dir / "clusters"
    ranking_dir   = output_dir / "ranking"

    # ── Stage 0: Clipper ─────────────────────────────────────────────────────
    if skip_clip:
        clip_paths = sorted(clips_dir.rglob("*.wav"))
        logger.info("Stage 0 skipped — usando %d clips existentes en %s",
                    len(clip_paths), clips_dir)
    else:
        logger.info("=" * 60)
        logger.info("STAGE 0 — AudioClipper")
        logger.info("  Fuente: %s", source_dir)
        clipper    = AudioClipper(source_dir=source_dir, output_dir=clips_dir)
        clip_paths = clipper.run()
        logger.info("  Clips generados: %d", len(clip_paths))

    if not clip_paths:
        logger.warning("No hay clips para analizar. Verifica la carpeta fuente.")
        return {'clips': [], 'results': {}, 'soundscape': {}, 'clusters': None, 'rankings': []}

    # ── Stage 1-3: Cascade ───────────────────────────────────────────────────
    results_file = analysis_dir / "results.json"
    if skip_cascade and results_file.exists():
        logger.info("Stage 1-3 skipped — cargando resultados desde %s", results_file)
        data    = json.loads(results_file.read_text())
        results = data.get('files', {})
    else:
        logger.info("=" * 60)
        logger.info("STAGE 1-3 — Cascade (YAMNet + Multispecies + Humpback)")
        results = run_cascade(clip_paths, output_dir=analysis_dir)

    # ── Stage 5: Soundscape ──────────────────────────────────────────────────
    soundscape_file = soundscape_dir / "soundscape.json"
    if skip_soundscape and soundscape_file.exists():
        logger.info("Stage 5 skipped — cargando soundscape desde %s", soundscape_file)
        soundscape = json.loads(soundscape_file.read_text())
    else:
        logger.info("=" * 60)
        logger.info("STAGE 5 — Soundscape characterization")
        soundscape = run_soundscape(clip_paths, output_dir=soundscape_dir)

    # ── Stage 6: Clustering (opcional) ───────────────────────────────────────
    clusters = None
    if no_cluster:
        logger.info("Stage 6 — deshabilitado (--no-cluster)")
    else:
        clusters_file = cluster_dir / "clusters.json"
        if skip_cluster and clusters_file.exists():
            logger.info("Stage 6 skipped — cargando clusters desde %s", clusters_file)
            clusters = json.loads(clusters_file.read_text())
        else:
            logger.info("=" * 60)
            logger.info("STAGE 6 — Embeddings + Clustering")
            clusters = run_clustering(clip_paths, output_dir=cluster_dir, soundscape=soundscape)

    # ── Stage 4: Enhanced Ranking ─────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STAGE 4 — Ranking biológico (9 dimensiones)")
    rankings = rank_results(
        results,
        soundscape=soundscape,
        clusters=clusters,
        output_dir=ranking_dir,
    )

    # ── Resumen final ─────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETADO")
    logger.info("  Clips analizados : %d", len(results))
    bio      = sum(1 for r in results.values() if 'biological_audio' in r.get('cascade_flags', []))
    whale    = sum(1 for r in results.values() if 'whale_species'    in r.get('cascade_flags', []))
    humpback = sum(1 for r in results.values() if 'humpback'         in r.get('cascade_flags', []))
    logger.info("  Bio signals      : %d", bio)
    logger.info("  Whale species    : %d", whale)
    logger.info("  Humpback         : %d", humpback)

    tier_dist = {}
    for r in rankings:
        tier_dist[r['tier']] = tier_dist.get(r['tier'], 0) + 1
    logger.info("  Tiers            : %s", tier_dist)

    if rankings:
        top = rankings[0]
        logger.info("  Top clip         : %s  (score=%.1f, %s)",
                    top['filename'], top['score'], top['tier'])

    logger.info("  Outputs en       : %s", output_dir)
    logger.info("=" * 60)

    return {
        'clips':     clip_paths,
        'results':   results,
        'soundscape': soundscape,
        'clusters':  clusters,
        'rankings':  rankings,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pipeline de análisis acústico marino — Galápagos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python -m backend.run --source data/raw_data
  python -m backend.run --source hackathon_data/marine-acoustic/6478
  python -m backend.run --source data/raw --skip-clip
  python -m backend.run --skip-clip --skip-cascade --no-cluster   # solo Stage 5+4
  python -m backend.run --skip-clip --skip-cascade --skip-cluster  # reusar Stage 6 también
        """,
    )
    default_source = Path(__file__).resolve().parent.parent / "hackathon_data" / "marine-acoustic"
    default_output = Path(__file__).resolve().parent.parent / "outputs"

    parser.add_argument('--source',          default=default_source, type=Path,
                        help=f'Carpeta con los WAVs originales (default: {default_source})')
    parser.add_argument('--output',          default=default_output, type=Path,
                        help='Carpeta de salida (default: outputs/)')
    parser.add_argument('--skip-clip',       action='store_true',
                        help='Saltar Stage 0, usar clips ya existentes')
    parser.add_argument('--skip-cascade',    action='store_true',
                        help='Saltar Stage 1-3, usar resultados ya existentes')
    parser.add_argument('--skip-soundscape', action='store_true',
                        help='Saltar Stage 5, usar soundscape.json existente')
    parser.add_argument('--skip-cluster',    action='store_true',
                        help='Saltar Stage 6, usar clusters.json existente')
    parser.add_argument('--no-cluster',      action='store_true',
                        help='No correr Stage 6 (útil sin GPU)')

    args = parser.parse_args()

    if not args.source.exists():
        logger.error("La carpeta fuente no existe: %s", args.source)
        sys.exit(1)

    run(
        source_dir=args.source,
        output_dir=args.output,
        skip_clip=args.skip_clip,
        skip_cascade=args.skip_cascade,
        skip_soundscape=args.skip_soundscape,
        skip_cluster=args.skip_cluster,
        no_cluster=args.no_cluster,
    )


if __name__ == '__main__':
    main()
