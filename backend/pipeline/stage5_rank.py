"""
backend/stage4_rank.py — Stage 4: multidimensional ranking by biological importance.

Takes cascade results and assigns a 0-100 score to each clip
based on 9 weighted dimensions. Produces sorted CSV and JSON.

Dimensions 1-7: cascade (YAMNet + Multispecies + Humpback)
Dimension 8: ndsi_score  — marine soundscape index (Stage 5, optional)
Dimension 9: cluster_signal — biological cluster signal (Stage 6, optional)

Usage:
    from backend.pipeline.stage5_rank import rank_results

    rank_results(results_dict, output_dir=Path("outputs/ranking"))
    rank_results(results_dict, soundscape=soundscape, clusters=clusters, ...)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from backend.config import RANK_WEIGHTS, RANK_TIERS, RANKING_DIR

logger = logging.getLogger(__name__)


def _score(result: dict) -> dict:
    """Computes the 7 score components for a result."""
    s2 = result.get('stage2_multispecies', {})
    s3 = result.get('stage3_humpback', {})
    s1 = result.get('stage1_yamnet', {})

    detections = s2.get('detections', [])
    flags      = result.get('cascade_flags', [])

    # 1. Whale sustained presence: combines peak and sustained activity
    top_max  = s2.get('top_max_score', 0.0)
    sum_mean = sum(d['mean_score'] for d in detections)
    whale_sustained = min(1.0, 0.5 * top_max + 0.5 * min(sum_mean * 5, 1.0))

    # 2. Biological signal richness (YAMNet)
    bio_count = len(s1.get('bio_detections', []))
    bio_score = sum(d['score'] for d in s1.get('bio_detections', []))
    bio_richness = min(1.0, 0.5 * (bio_count / 8) + 0.5 * min(bio_score, 1.0))

    # 3. Acoustic diversity: distinct species/types detected
    n_species      = sum(1 for d in detections if d['class_code'] in {'Oo','Mn','Eg','Be','Bp','Bm','Ba'} and d['max_score'] >= 0.01)
    n_vocalizations= sum(1 for d in detections if d['class_code'] in {'Upcall','Call','Gunshot','Echolocation','Whistle'} and d['max_score'] >= 0.01)
    acoustic_diversity = min(1.0, (n_species + n_vocalizations) / 7)

    # 4. Humpback temporal coverage
    humpback_coverage = s3.get('fraction_above_threshold', 0.0)

    # 5. Cross-model agreement: bonus when multiple models agree
    cross = 0.0
    if 'biological_audio' in flags:   cross += 0.30
    if 'marine_environment' in flags: cross += 0.10
    if 'whale_species' in flags:      cross += 0.35
    if 'humpback' in flags:           cross += 0.25
    cross_model = min(1.0, cross)

    # 6. Humpback peak confidence
    humpback_peak = min(1.0, s3.get('max_score', 0.0))

    # 7. YAMNet top-class quality: penaliza si el top es Speech/Silence
    top_classes = s1.get('top_classes', [])
    yamnet_quality = 0.0
    if top_classes:
        top1 = top_classes[0]
        name = top1['class'].lower()
        if 'speech' not in name and 'silence' not in name and 'noise' not in name:
            yamnet_quality = min(1.0, top1['score'] * 3)

    return {
        'whale_sustained':    round(whale_sustained, 4),
        'bio_richness':       round(bio_richness, 4),
        'acoustic_diversity': round(acoustic_diversity, 4),
        'humpback_coverage':  round(humpback_coverage, 4),
        'cross_model':        round(cross_model, 4),
        'humpback_peak':      round(humpback_peak, 4),
        'yamnet_quality':     round(yamnet_quality, 4),
        # Placeholders — overwritten by rank_results if soundscape/clusters present
        'ndsi_score':         0.0,
        'cluster_signal':     0.0,
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
        results:    Cascade output (Stage 1-3).
        soundscape: (optional) Stage 5 output with ndsi_underwater per clip.
        clusters:   (optional) Stage 6 output with cluster_id and dominant_band.
        output_dir: Folder where ranked.csv and ranked.json are written.

    Returns:
        List of dicts sorted by descending score.
        Backward-compatible: if soundscape and clusters are None, behaves as before.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    w = RANK_WEIGHTS
    rankings = []

    for fname, result in results.items():
        if result.get('status') in ('error', 'silent'):
            continue

        components = _score(result)

        # ── Dimension 8: ndsi_score (Stage 5) ────────────────────────────────
        if soundscape and fname in soundscape:
            ss = soundscape[fname]
            ndsi = ss.get('ndsi_underwater', 0.0)
            # map [-1, 1] → [0, 1]: high NDSI = good biology
            components['ndsi_score'] = round(float(np.clip((ndsi + 1) / 2, 0.0, 1.0)), 4)
        # else: stays at 0.0 (from _score placeholder)

        # ── Dimension 9: cluster_signal (Stage 6) ─────────────────────────────
        if clusters and fname in clusters:
            cl = clusters[fname]
            cid   = cl.get('cluster_id', -1)
            dom   = cl.get('cluster_dominant_band', 'UNKNOWN')
            csize = cl.get('cluster_size', 1)
            # bonus if in a real cluster (not outlier) and band is not LOW
            if cid >= 0 and dom != 'LOW':
                # scale by cluster size (more similar clips = more confidence)
                components['cluster_signal'] = round(min(1.0, 0.5 + 0.1 * csize), 4)
            elif cid >= 0:
                components['cluster_signal'] = 0.3  # LOW cluster (probable boat)
            # outlier (cid == -1): stays at 0.0

        total = sum(components[k] * w[k] * 100 for k in w)

        rankings.append({
            'filename':   fname,
            'score':      round(total, 2),
            'tier':       _tier(total),
            'components': components,
            'duration_s': result.get('duration_s', 0),
            'cascade_flags':    result.get('cascade_flags', []),
            'cascade_summary':  result.get('cascade_summary', ''),
            'top_species':      result.get('stage2_multispecies', {}).get('top_species_name', ''),
            'annotations':      result.get('annotations', []),
            'source_path':      result.get('source_path', ''),
        })

    rankings.sort(key=lambda x: -x['score'])
    for i, r in enumerate(rankings, 1):
        r['rank'] = i

    # Tier distribution
    tier_dist = {}
    for r in rankings:
        tier_dist[r['tier']] = tier_dist.get(r['tier'], 0) + 1

    # JSON
    json_out = output_dir / "ranked.json"
    json_out.write_text(json.dumps({
        'total_ranked':    len(rankings),
        'tier_distribution': tier_dist,
        'weights':         w,
        'tier_thresholds': RANK_TIERS,
        'rankings':        rankings,
    }, indent=2))

    # CSV
    csv_out = output_dir / "ranked.csv"
    with open(csv_out, 'w') as f:
        header = ['rank', 'filename', 'score', 'tier', 'duration_s',
                  'whale_sustained', 'bio_richness', 'acoustic_diversity',
                  'humpback_coverage', 'cross_model', 'humpback_peak',
                  'yamnet_quality', 'ndsi_score', 'cluster_signal',
                  'flags', 'top_species']
        f.write(','.join(header) + '\n')
        for r in rankings:
            c = r['components']
            row = [
                r['rank'], r['filename'], r['score'], r['tier'], r['duration_s'],
                c['whale_sustained'], c['bio_richness'], c['acoustic_diversity'],
                c['humpback_coverage'], c['cross_model'], c['humpback_peak'],
                c['yamnet_quality'], c['ndsi_score'], c['cluster_signal'],
                '|'.join(r['cascade_flags']), r['top_species'],
            ]
            f.write(','.join(str(x) for x in row) + '\n')

    # Log summary
    logger.info("Stage 4 done — %d clips ranked", len(rankings))
    logger.info("  Tier distribution: %s", tier_dist)
    if rankings:
        top = rankings[0]
        logger.info("  #1: %s  score=%.1f  tier=%s", top['filename'], top['score'], top['tier'])

    logger.info("  → %s", json_out)
    logger.info("  → %s", csv_out)
    return rankings
