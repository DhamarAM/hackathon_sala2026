"""
Rank audio files by biological importance using a weighted scoring system (v2).

Reads cascade_results.json and produces a ranked list based on seven
weighted dimensions that capture different aspects of biological value:

  1. Whale sustained presence (20%) — composite of max + mean multispecies scores
  2. Biological signal richness (20%) — YAMNet bio detection count + score strength
  3. Acoustic diversity (20%) — species + vocalization types detected
  4. Humpback temporal coverage (15%) — fraction of time windows with humpback signal
  5. Cross-model agreement (15%) — bonus when multiple independent models converge
  6. Humpback peak confidence (5%) — max humpback score (low weight: too uniform)
  7. YAMNet top-class quality (5%) — bonus when top YAMNet class is biological

v2 changes from v1:
  - Replaced pure max whale score (35%) with sustained presence composite (20%)
    that combines max AND mean scores — rewards sustained activity, not just spikes
  - Doubled biological signal richness weight (10% → 20%) — files where YAMNet
    clearly identifies "Animal" are more valuable than "Silence"/"Speech" files
  - Doubled acoustic diversity weight (15% → 20%) and lowered vocalization threshold
  - Added top-class quality dimension to distinguish "Animal" from "Speech" top labels
  - Increased cross-model agreement (10% → 15%) — convergence matters
  - Reduced humpback peak (10% → 5%) — nearly all files detect humpback (99/100)

Outputs:
  - output2/ranked_importance.json — full ranked results with scores
  - output2/ranked_importance.csv — simplified CSV for quick reference
  - Console summary with tier classification

Usage:
    python3 -u rank_biological_importance.py
"""

import json
import csv
from pathlib import Path

RESULTS_FILE = Path("output2/cascade_results.json")
OUTPUT_JSON = Path("output2/ranked_importance.json")
OUTPUT_CSV = Path("output2/ranked_importance.csv")

# ─── Weight configuration (v2) ───────────────────────────────────────────────
# Revised to balance sustained biological activity vs transient peaks.
# See RANKING_METHODOLOGY.md for full justification.

WEIGHTS = {
    'whale_sustained':       0.20,  # Composite max+mean: rewards persistent cetacean presence
    'bio_richness':          0.20,  # YAMNet bio count + score: clear biological signal
    'acoustic_diversity':    0.20,  # Species + vocalization types: richer = more valuable
    'humpback_coverage':     0.15,  # Temporal extent of humpback activity
    'cross_model_agreement': 0.15,  # Convergent evidence across independent models
    'humpback_peak':         0.05,  # Peak humpback score (nearly uniform, low discriminant)
    'yamnet_top_quality':    0.05,  # Bonus for biological top-class vs noise/speech
}

# Species codes in the multispecies model (excluding vocalization types)
SPECIES_CODES = {'Oo', 'Mn', 'Eg', 'Be', 'Bp', 'Bm', 'Ba'}
VOCALIZATION_CODES = {'Call', 'Echolocation', 'Whistle', 'Gunshot', 'Upcall'}

# Tier thresholds (applied to final 0–100 score)
TIER_THRESHOLDS = {
    'CRITICAL':  65,  # Top priority — rich, multi-species, sustained activity
    'HIGH':      45,  # Strong detections — clear whale presence
    'MODERATE':  25,  # Some detections — worth reviewing
    'LOW':       10,  # Weak or single-model signals
    'MINIMAL':    0,  # Little to no biological content detected
}

# YAMNet classes that indicate the audio is genuinely biological
# (as opposed to "Speech", "Silence", "White noise" which are less informative)
YAMNET_BIO_TOP_CLASSES = {
    'animal', 'wild animals', 'insect', 'bird', 'frog', 'cricket',
    'whale vocalization', 'livestock', 'cattle', 'fowl', 'roar',
}


def compute_score(result):
    """Compute the weighted biological importance score for a single file.
    Returns (total_score, component_scores_dict)."""

    s1 = result.get('stage1_yamnet', {})
    s2 = result.get('stage2_multispecies', {})
    s3 = result.get('stage3_humpback', {})

    detections = s2.get('detections', [])

    # ── Dimension 1: Whale sustained presence (0–1) ──────────────────────
    # Composite of max score (peak evidence) and mean score (sustained presence).
    # A single orca spike of 0.98 in one 5s window is less biologically
    # interesting than sustained presence of 0.30 across many windows.
    # Formula: 0.5 * max + 0.5 * (sum_of_means * 5, capped at 1)
    max_score = max((d['max_score'] for d in detections), default=0.0)
    sum_means = sum(d['mean_score'] for d in detections)
    sustained_component = min(sum_means * 5.0, 1.0)  # Scale means up (they're tiny)
    whale_sustained = 0.5 * max_score + 0.5 * sustained_component

    # ── Dimension 2: Biological signal richness (0–1) ────────────────────
    # Combines YAMNet bio detection count with their aggregate score strength.
    # A file with 8 bio detections ("Animal", "Wild animals", "Insect"...)
    # is a stronger biological signal than 1 detection of "Speech".
    bio_dets = s1.get('bio_detections', [])
    bio_count = len(bio_dets)
    bio_score_sum = sum(d['score'] for d in bio_dets)
    # Blend count (normalized to 8) with score mass (normalized to 1.0)
    count_norm = min(bio_count / 8.0, 1.0)
    score_norm = min(bio_score_sum / 1.0, 1.0)  # Sum of scores, cap at 1.0
    bio_richness = 0.5 * count_norm + 0.5 * score_norm

    # ── Dimension 3: Acoustic diversity (0–1, normalized) ────────────────
    # Count distinct species (score >= 0.01) + vocalization types (score >= 0.01).
    # Lower threshold than v1 (was 0.05 for voc types) to capture weak but
    # present signals that indicate acoustic complexity.
    # Species and voc types weighted equally — both indicate richness.
    n_species = len([d for d in detections
                     if d['class_code'] in SPECIES_CODES and d['max_score'] >= 0.01])
    n_voc_types = len([d for d in detections
                       if d['class_code'] in VOCALIZATION_CODES and d['max_score'] >= 0.01])
    diversity_raw = n_species + n_voc_types
    acoustic_diversity = min(diversity_raw / 7.0, 1.0)

    # ── Dimension 4: Humpback temporal coverage (0–1) ────────────────────
    # Fraction of time windows where humpback was detected above threshold.
    # High coverage = sustained vocalization, not a transient artifact.
    humpback_coverage = s3.get('fraction_above_threshold', 0.0)

    # ── Dimension 5: Cross-model agreement (0–1) ────────────────────────
    # Bonus when multiple independent models converge on biological content.
    # Stronger weighting for biological signals, marine environment is a bonus.
    agreement = 0.0
    if s1.get('has_bio_signal'):
        agreement += 0.30
    if s1.get('has_marine_signal'):
        agreement += 0.10
    if s2.get('any_whale_detected'):
        agreement += 0.35
    if s3.get('humpback_detected'):
        agreement += 0.25

    # ── Dimension 6: Humpback peak confidence (0–1) ──────────────────────
    # Max humpback score. Low weight because 99/100 files have detection,
    # making this dimension nearly uniform and low-discriminant.
    humpback_peak = s3.get('max_score', 0.0)

    # ── Dimension 7: YAMNet top-class quality (0–1) ──────────────────────
    # Bonus when the YAMNet TOP-1 class is genuinely biological.
    # "Animal" as top-1 is a much stronger signal than "Speech" or "Silence"
    # being top-1 with a small "Animal" somewhere in the list.
    top_classes = s1.get('top_classes', [])
    yamnet_top_quality = 0.0
    if top_classes:
        top1_name = top_classes[0]['class'].lower()
        top1_score = top_classes[0]['score']
        # Check if top-1 is a biological class
        is_bio_top = any(kw in top1_name for kw in YAMNET_BIO_TOP_CLASSES)
        if is_bio_top:
            yamnet_top_quality = min(top1_score * 3.0, 1.0)  # Scale up, cap at 1
        # Penalty-free: if top is "Silence" or "Speech", just 0

    # ── Weighted combination ──────────────────────────────────────────────
    components = {
        'whale_sustained': whale_sustained,
        'bio_richness': bio_richness,
        'acoustic_diversity': acoustic_diversity,
        'humpback_coverage': humpback_coverage,
        'cross_model_agreement': agreement,
        'humpback_peak': humpback_peak,
        'yamnet_top_quality': yamnet_top_quality,
    }

    total = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    # Scale to 0–100
    total_score = round(total * 100, 2)

    return total_score, {k: round(v, 4) for k, v in components.items()}


def assign_tier(score):
    """Assign a priority tier based on the final score."""
    for tier, threshold in sorted(TIER_THRESHOLDS.items(),
                                  key=lambda x: -x[1]):
        if score >= threshold:
            return tier
    return 'MINIMAL'


def main():
    with open(RESULTS_FILE) as f:
        data = json.load(f)

    files = data['files']
    ranked = []

    for fname, result in files.items():
        if result.get('status') != 'analyzed':
            continue

        score, components = compute_score(result)
        tier = assign_tier(score)

        ranked.append({
            'rank': 0,  # filled after sorting
            'filename': fname,
            'score': score,
            'tier': tier,
            'components': components,
            'duration_s': result.get('duration_s', 0),
            'cascade_flags': result.get('cascade_flags', []),
            'top_species': result.get('stage2_multispecies', {}).get('top_species', ''),
            'annotations_count': len(result.get('annotations', [])),
        })

    # Sort by score descending
    ranked.sort(key=lambda x: -x['score'])
    for i, entry in enumerate(ranked):
        entry['rank'] = i + 1

    # ── Console output ────────────────────────────────────────────────────
    print(f"{'=' * 90}")
    print(f"BIOLOGICAL IMPORTANCE RANKING — {len(ranked)} files")
    print(f"{'=' * 90}")
    print(f"{'Rank':<6}{'Score':<8}{'Tier':<12}{'Filename':<25}{'WhaleSust':<11}"
          f"{'BioRich':<9}{'Diversity':<11}{'Flags'}")
    print(f"{'-' * 90}")

    tier_counts = {}
    for entry in ranked:
        tier_counts[entry['tier']] = tier_counts.get(entry['tier'], 0) + 1
        c = entry['components']
        flags = ','.join(entry['cascade_flags']) if entry['cascade_flags'] else '---'
        print(f"{entry['rank']:<6}{entry['score']:<8.1f}{entry['tier']:<12}"
              f"{entry['filename']:<25}{c['whale_sustained']:<11.4f}"
              f"{c['bio_richness']:<9.3f}{c['acoustic_diversity']:<11.3f}"
              f"{flags}")

    print(f"\n{'=' * 90}")
    print("TIER DISTRIBUTION")
    print(f"{'=' * 90}")
    for tier in ['CRITICAL', 'HIGH', 'MODERATE', 'LOW', 'MINIMAL']:
        count = tier_counts.get(tier, 0)
        bar = '#' * count
        print(f"  {tier:<12} {count:>3} files  {bar}")

    print(f"\n{'=' * 90}")
    print("WEIGHT CONFIGURATION")
    print(f"{'=' * 90}")
    for dim, weight in WEIGHTS.items():
        print(f"  {dim:<30} {weight:.0%}")

    # ── Top 10 detail ─────────────────────────────────────────────────────
    print(f"\n{'=' * 90}")
    print("TOP 10 — HIGHEST BIOLOGICAL IMPORTANCE")
    print(f"{'=' * 90}")
    for entry in ranked[:10]:
        c = entry['components']
        print(f"\n  #{entry['rank']} {entry['filename']} — Score: {entry['score']:.1f} ({entry['tier']})")
        print(f"      Whale sustained:       {c['whale_sustained']:.4f}  (weight: {WEIGHTS['whale_sustained']:.0%})")
        print(f"      Bio richness:          {c['bio_richness']:.3f}   (weight: {WEIGHTS['bio_richness']:.0%})")
        print(f"      Acoustic diversity:    {c['acoustic_diversity']:.3f}   (weight: {WEIGHTS['acoustic_diversity']:.0%})")
        print(f"      Humpback coverage:     {c['humpback_coverage']:.3f}   (weight: {WEIGHTS['humpback_coverage']:.0%})")
        print(f"      Cross-model agreement: {c['cross_model_agreement']:.3f}   (weight: {WEIGHTS['cross_model_agreement']:.0%})")
        print(f"      Humpback peak:         {c['humpback_peak']:.4f}  (weight: {WEIGHTS['humpback_peak']:.0%})")
        print(f"      YAMNet top quality:    {c['yamnet_top_quality']:.3f}   (weight: {WEIGHTS['yamnet_top_quality']:.0%})")

    # ── Save JSON ─────────────────────────────────────────────────────────
    output = {
        'methodology': 'Weighted multi-dimensional biological importance scoring',
        'weights': WEIGHTS,
        'tier_thresholds': TIER_THRESHOLDS,
        'total_ranked': len(ranked),
        'tier_distribution': tier_counts,
        'rankings': ranked,
    }
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(output, f, indent=2)

    # ── Save CSV ──────────────────────────────────────────────────────────
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'rank', 'filename', 'score', 'tier', 'duration_s',
            'whale_sustained', 'bio_richness', 'acoustic_diversity',
            'humpback_coverage', 'cross_model_agreement',
            'humpback_peak', 'yamnet_top_quality', 'flags',
        ])
        for entry in ranked:
            c = entry['components']
            writer.writerow([
                entry['rank'], entry['filename'], entry['score'], entry['tier'],
                entry['duration_s'],
                c['whale_sustained'], c['bio_richness'], c['acoustic_diversity'],
                c['humpback_coverage'], c['cross_model_agreement'],
                c['humpback_peak'], c['yamnet_top_quality'],
                '|'.join(entry['cascade_flags']),
            ])

    print(f"\n  Results saved to:")
    print(f"    {OUTPUT_JSON}")
    print(f"    {OUTPUT_CSV}")


if __name__ == '__main__':
    main()