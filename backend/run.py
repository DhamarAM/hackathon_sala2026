"""
backend/run.py — Main entrypoint for the integrated backend.

Full pipeline:
    Stage 0:   AudioClipper      → clips WAVs to active segments
    Stage 1-3: Cascade           → YAMNet + Multispecies Whale + Humpback
    Stage 5:   Soundscape        → marine acoustic indices (no GPU)
    Stage 6:   Embeddings+Cluster→ BirdNET/MFCC + UMAP + HDBSCAN (GPU optional)
    Stage 4:   Enhanced Ranking  → 9-dimensional score + CSV/JSON

Usage:
    python -m backend.run --source <folder_with_wavs>

    # Options:
    python -m backend.run --source data/raw --output outputs
    python -m backend.run --source data/raw --skip-clip      # use existing clips
    python -m backend.run --source data/raw --skip-cascade   # rank only
    python -m backend.run --source data/raw --no-cluster     # skip Stage 6 (no GPU)
    python -m backend.run --skip-clip --skip-cascade --no-cluster  # Stages 5+4 only
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
    Runs the full or partial backend pipeline.

    Args:
        source_dir:      Folder containing the original WAVs.
        output_dir:      Root folder for all outputs.
        skip_clip:       If True, assumes clips already exist in output_dir/clips/.
        skip_cascade:    If True, assumes cascade results already exist.
        skip_soundscape: If True, loads existing soundscape.json (Stage 5).
        skip_cluster:    If True, loads existing clusters.json (Stage 6).
        no_cluster:      If True, does not run Stage 6 at all.

    Returns:
        Dict with {clips, results, soundscape, clusters, rankings}.
    """
    from backend.pipeline.stage1_clip       import AudioClipper
    from backend.pipeline.stage2_cascade    import run_cascade
    from backend.pipeline.stage3_soundscape import run_soundscape
    from backend.pipeline.stage4_cluster    import run_clustering
    from backend.pipeline.stage5_rank       import rank_results

    clips_dir     = output_dir / "clips"
    analysis_dir  = output_dir / "analysis"
    soundscape_dir = output_dir / "soundscape"
    cluster_dir   = output_dir / "clusters"
    ranking_dir   = output_dir / "ranking"

    # ── Stage 0: Clipper ─────────────────────────────────────────────────────
    if skip_clip:
        clip_paths = sorted(clips_dir.rglob("*.wav"))
        logger.info("Stage 0 skipped — using %d existing clips in %s",
                    len(clip_paths), clips_dir)
    else:
        logger.info("=" * 60)
        logger.info("STAGE 0 — AudioClipper")
        logger.info("  Source: %s", source_dir)
        clipper    = AudioClipper(source_dir=source_dir, output_dir=clips_dir)
        clip_paths = clipper.run()
        logger.info("  Clips generated: %d", len(clip_paths))

    if not clip_paths:
        logger.warning("No clips to analyze. Check the source folder.")
        return {'clips': [], 'results': {}, 'soundscape': {}, 'clusters': None, 'rankings': []}

    # ── Stage 1-3: Cascade ───────────────────────────────────────────────────
    results_file = analysis_dir / "results.json"
    if skip_cascade and results_file.exists():
        logger.info("Stage 1-3 skipped — loading results from %s", results_file)
        data    = json.loads(results_file.read_text())
        results = data.get('files', {})
    else:
        logger.info("=" * 60)
        logger.info("STAGE 1-3 — Cascade (YAMNet + Multispecies + Humpback)")
        results = run_cascade(clip_paths, output_dir=analysis_dir)

    # ── Stage 5: Soundscape ──────────────────────────────────────────────────
    soundscape_file = soundscape_dir / "soundscape.json"
    if skip_soundscape and soundscape_file.exists():
        logger.info("Stage 5 skipped — loading soundscape from %s", soundscape_file)
        soundscape = json.loads(soundscape_file.read_text())
    else:
        logger.info("=" * 60)
        logger.info("STAGE 5 — Soundscape characterization")
        soundscape = run_soundscape(clip_paths, output_dir=soundscape_dir)

    # ── Stage 6: Clustering (opcional) ───────────────────────────────────────
    clusters = None
    if no_cluster:
        logger.info("Stage 6 — disabled (--no-cluster)")
    else:
        clusters_file = cluster_dir / "clusters.json"
        if skip_cluster and clusters_file.exists():
            logger.info("Stage 6 skipped — loading clusters from %s", clusters_file)
            clusters = json.loads(clusters_file.read_text())
        else:
            logger.info("=" * 60)
            logger.info("STAGE 6 — Embeddings + Clustering")
            clusters = run_clustering(clip_paths, output_dir=cluster_dir, soundscape=soundscape)

    # ── Stage 4: Enhanced Ranking ─────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STAGE 4 — Biological ranking (9 dimensions)")
    rankings = rank_results(
        results,
        soundscape=soundscape,
        clusters=clusters,
        output_dir=ranking_dir,
    )

    # ── Final summary ─────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("  Clips analyzed   : %d", len(results))
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

    logger.info("  Outputs at       : %s", output_dir)
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
        description='Marine acoustic analysis pipeline — Galapagos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m backend.run --source data/raw_data
  python -m backend.run --source hackathon_data/marine-acoustic/6478
  python -m backend.run --source data/raw --skip-clip
  python -m backend.run --skip-clip --skip-cascade --no-cluster   # Stage 5+4 only
  python -m backend.run --skip-clip --skip-cascade --skip-cluster  # reuse Stage 6 as well
        """,
    )
    default_source = Path(__file__).resolve().parent.parent / "hackathon_data" / "marine-acoustic"
    default_output = Path(__file__).resolve().parent.parent / "outputs"

    parser.add_argument('--source',          default=default_source, type=Path,
                        help=f'Folder with the original WAVs (default: {default_source})')
    parser.add_argument('--output',          default=default_output, type=Path,
                        help='Output folder (default: outputs/)')
    parser.add_argument('--skip-clip',       action='store_true',
                        help='Skip Stage 0, use existing clips')
    parser.add_argument('--skip-cascade',    action='store_true',
                        help='Skip Stage 1-3, use existing results')
    parser.add_argument('--skip-soundscape', action='store_true',
                        help='Skip Stage 5, use existing soundscape.json')
    parser.add_argument('--skip-cluster',    action='store_true',
                        help='Skip Stage 6, use existing clusters.json')
    parser.add_argument('--no-cluster',      action='store_true',
                        help='Do not run Stage 6 (useful without GPU)')

    args = parser.parse_args()

    if not args.source.exists():
        logger.error("Source folder does not exist: %s", args.source)
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
