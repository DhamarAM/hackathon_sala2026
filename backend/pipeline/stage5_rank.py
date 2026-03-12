"""
backend/stage5_rank.py — Stage 4: model-equal ranking by biological importance.

Each of the 6 cascade models contributes its bio_signal_score [0, 1] with equal
weight. Final score = mean(6 scores) × 100. Models that agree on biological
content push the score up linearly — same philosophy as enhanced_classifier.py.

Models:
    perch        — Perch 2.0 / TF Hub bird-vocalization (acoustic complexity proxy)
    multispecies — Google Multispecies Whale (12 cetacean classes)
    humpback     — Google Humpback Whale (binary)
    naturelm     — NatureLM-BEATs (bioacoustic transformer)
    biolingual   — BioLingual (zero-shot bioacoustic)
    dasheng      — Dasheng (self-supervised structural complexity)

Usage:
    from backend.pipeline.stage5_rank import rank_results

    rank_results(results_dict, output_dir=Path("outputs/ranking"))
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from backend.config import RANK_MODELS, RANK_TIERS, RANKING_DIR

logger = logging.getLogger(__name__)

# Maps RANK_MODELS names → results.json stage keys
_STAGE_KEYS = {
    'perch':        'stage1_perch',
    'multispecies': 'stage2_multispecies',
    'humpback':     'stage3_humpback',
    'naturelm':     'stage4_naturelm',
    'biolingual':   'stage5_biolingual',
    'dasheng':      'stage6_dasheng',
}


def _score(result: dict) -> dict:
    """Returns bio_signal_score per model. Score = mean × 100."""
    return {
        model: round(result.get(_STAGE_KEYS[model], {}).get('bio_signal_score', 0.0), 4)
        for model in RANK_MODELS
    }


def _tier(score: float) -> str:
    for name, threshold in sorted(RANK_TIERS.items(), key=lambda x: -x[1]):
        if score >= threshold:
            return name
    return 'MINIMAL'


def rank_results(
    results: Dict[str, dict],
    soundscape: Optional[Dict[str, dict]] = None,
    clusters:   Optional[Dict[str, dict]] = None,
    output_dir: Path = RANKING_DIR,
) -> List[dict]:
    """
    Ranks cascade results by biological importance.

    Args:
        results:    Cascade output (Stages 1–6).
        soundscape: (optional) Stage 5 soundscape output — stored as metadata.
        clusters:   (optional) Stage 6 cluster output — stored as metadata.
        output_dir: Folder where ranked.csv and ranked.json are written.

    Returns:
        List of dicts sorted by descending score.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    rankings = []

    for fname, result in results.items():
        if result.get('status') in ('error', 'silent'):
            continue

        components = _score(result)
        bio_score = sum(components.values()) / len(components) * 100

        # Soundscape metadata
        ndsi       = None
        boat_score = None
        if soundscape and fname in soundscape:
            ndsi       = soundscape[fname].get('ndsi_underwater')
            boat_score = soundscape[fname].get('boat_score')

        # boat_score is metadata only — does not affect the ranking score.
        # Rationale: BioLingual already has "boat engine noise" as a label; if a clip is
        # dominated by boat noise its bio_signal_scores will be low without any extra penalty.
        # Applying an additional penalty would double-count the same signal.
        # boat_score is kept in the CSV/JSON as context for the marine biologist reviewer.
        total = round(bio_score, 2)

        # Cluster metadata
        cluster_id = None
        if clusters and fname in clusters:
            cluster_id = clusters[fname].get('cluster_id')

        rankings.append({
            'filename':        fname,
            'score':           total,
            'tier':            _tier(total),
            'components':      components,
            'duration_s':      result.get('duration_s', 0),
            'cascade_flags':   result.get('cascade_flags', []),
            'cascade_summary': result.get('cascade_summary', ''),
            'top_species':     result.get('stage2_multispecies', {}).get('top_species_name', ''),
            'annotations':     result.get('annotations', []),
            'source_path':     result.get('source_path', ''),
            'ndsi':            ndsi,
            'boat_score':      boat_score,
            'cluster_id':      cluster_id,
        })

    rankings.sort(key=lambda x: -x['score'])
    for i, r in enumerate(rankings, 1):
        r['rank'] = i

    tier_dist = {}
    for r in rankings:
        tier_dist[r['tier']] = tier_dist.get(r['tier'], 0) + 1

    # JSON
    json_out = output_dir / "ranked.json"
    json_out.write_text(json.dumps({
        'methodology':       'equal weight per model — mean(bio_signal_score) × 100',
        'models':            RANK_MODELS,
        'tier_thresholds':   RANK_TIERS,
        'total_ranked':      len(rankings),
        'tier_distribution': tier_dist,
        'rankings':          rankings,
    }, indent=2))

    # CSV
    csv_out = output_dir / "ranked.csv"
    with open(csv_out, 'w') as f:
        header = ['rank', 'filename', 'score', 'tier', 'duration_s'] + RANK_MODELS + ['boat_score', 'flags', 'top_species']
        f.write(','.join(header) + '\n')
        for r in rankings:
            c = r['components']
            row = [r['rank'], r['filename'], r['score'], r['tier'], r['duration_s']] + \
                  [c[m] for m in RANK_MODELS] + \
                  [r['boat_score'] if r['boat_score'] is not None else '',
                   '|'.join(r['cascade_flags']), r['top_species']]
            f.write(','.join(str(x) for x in row) + '\n')

    logger.info("Stage 4 done — %d clips ranked", len(rankings))
    logger.info("  Tier distribution: %s", tier_dist)
    if rankings:
        top = rankings[0]
        logger.info("  #1: %s  score=%.1f  tier=%s", top['filename'], top['score'], top['tier'])
    logger.info("  → %s", json_out)
    logger.info("  → %s", csv_out)
    return rankings