"""
backend/config.py — Centralized backend configuration.
"""

from pathlib import Path

# ─── Default paths ────────────────────────────────────────────────────────────

ROOT_DIR    = Path(__file__).resolve().parent.parent
OUTPUT_DIR  = ROOT_DIR / "outputs"

CLIPS_DIR        = OUTPUT_DIR / "clips"
ANALYSIS_DIR     = OUTPUT_DIR / "analysis"
SPECTROGRAMS_DIR = ANALYSIS_DIR / "spectrograms"
ANNOTATIONS_DIR  = ANALYSIS_DIR / "annotations"
RESULTS_FILE     = ANALYSIS_DIR / "results.json"
SOUNDSCAPE_DIR   = OUTPUT_DIR / "soundscape"   # Stage 5
CLUSTER_DIR      = OUTPUT_DIR / "clusters"     # Stage 6
RANKING_DIR      = OUTPUT_DIR / "ranking"

# ─── Stage 0: AudioClipper ────────────────────────────────────────────────────

SILENCE_THRESHOLD  = 50.0       # RMS int16 units (~-56 dBFS)
CHUNK_FRAMES       = 144_000    # 1s at 144kHz; adapts to actual sr
PADDING_S          = 1.0        # Padding around each active segment
MERGE_GAP_S        = 2.0        # Silence ≤ N s → merge segments
MIN_SEGMENT_S      = 2.0        # Discard clips shorter than this
MAX_CLIP_S         = 30.0       # Hard cap per clip — longer segments are split into sub-clips.
                                 # Prevents OOM on transformer models (BEATs attention is quadratic).
MULTISPECIES_MIN_S = 5.0        # Minimum required by the multispecies model (120k samples @ 24kHz)

# ─── Stage 1: Perch 2.0 ──────────────────────────────────────────────────────

PERCH_BIO_THRESHOLD          = 0.05   # Minimum sigmoid probability to flag a bio class
PERCH_FALLBACK_BIO_THRESHOLD = 0.02   # Threshold when class names unavailable (TF Hub fallback):
                                       # bio_signal = std(embeddings)/2 → typical range 0.02-0.08
                                       # for hydrophone recordings

PERCH_BIO_KEYWORDS = {
    'animal', 'bird', 'mammal', 'whale', 'dolphin', 'porpoise',
    'seal', 'orca', 'humpback', 'fin whale', 'blue whale',
    'fish', 'shrimp', 'reef', 'marine', 'frog', 'insect',
    'bat', 'vocalization', 'call', 'song',
}
PERCH_MARINE_KEYWORDS = {
    'whale', 'dolphin', 'porpoise', 'seal', 'orca', 'humpback',
    'fin whale', 'blue whale', 'marine', 'underwater',
    'ocean', 'fish', 'shrimp', 'reef', 'cetacean',
}

# ─── Stage 5b: BioLingual ─────────────────────────────────────────────────────

BIOLINGUAL_LABELS = [
    "humpback whale song", "dolphin clicks and whistles",
    "orca killer whale call", "fish sounds", "shrimp snapping",
    "seal barking", "ocean ambient noise", "boat engine noise",
    "silence", "bird calls",
]
BIOLINGUAL_BIO_LABELS = {
    "humpback whale song", "dolphin clicks and whistles",
    "orca killer whale call", "fish sounds", "shrimp snapping",
    "seal barking", "bird calls",
}

# ─── Stage 2: Multispecies Whale ─────────────────────────────────────────────

MULTISPECIES_THRESHOLD     = 0.005  # Minimum score to list species in detections[]
MULTISPECIES_DETECTION_THR = 0.01   # Minimum score for confirmed detection (activates whale_species flag)
                                    # Lowered from 0.10: hydrophone recordings produce 10-50x lower scores
                                    # than surface/aerial recordings the model was calibrated on

WHALE_SPECIES = {
    'Oo':          'Orcinus orca (Orca)',
    'Mn':          'Megaptera novaeangliae (Humpback whale)',
    'Eg':          'Eubalaena glacialis (Right whale)',
    'Be':          'Mesoplodon/Ziphius (Beaked whale)',
    'Bp':          'Balaenoptera physalus (Fin whale)',
    'Bm':          'Balaenoptera musculus (Blue whale)',
    'Ba':          'Balaenoptera acutorostrata (Minke whale)',
    'Upcall':      'Right whale upcall',
    'Call':        'Generic whale call',
    'Gunshot':     'Right whale gunshot',
    'Echolocation':'Odontocete echolocation',
    'Whistle':     'Dolphin/whale whistle',
}

# ─── Stage 3: Humpback Whale ─────────────────────────────────────────────────

HUMPBACK_THRESHOLD = 0.3        # Minimum score per 1s window (0.1 produced ~99% detections)

# ─── Stage 4: Ranking ─────────────────────────────────────────────────────────

# Scoring: each model contributes its bio_signal_score [0,1] with equal weight.
# final_score = mean(6 model scores) × 100  (same philosophy as enhanced_classifier.py)
RANK_MODELS = ['perch', 'multispecies', 'humpback', 'naturelm', 'biolingual', 'dasheng']

RANK_TIERS = {
    'CRITICAL': 70,
    'HIGH':     50,
    'MODERATE': 30,
    'LOW':      15,
    'MINIMAL':   0,
}

# ─── Stage 5: Soundscape characterization ────────────────────────────────────

# Marine-calibrated frequency bands (Hz).
# Boat/ship noise peaks below 500 Hz (propellers, engines).
# Humpback whale song spans 20–4000 Hz — keeping ANTHRO ≤500 Hz avoids
# misclassifying low-frequency cetacean calls as anthropogenic noise.
SOUNDSCAPE_ANTHRO_HZ   = (50,      500)   # boat/ship noise
SOUNDSCAPE_BIO_LOW_HZ  = (500,   2_000)   # low-freq biology: humpback, fish choruses
SOUNDSCAPE_BIO_BAND_HZ = (2_000, 20_000)  # main marine biology: shrimp, dolphins
SOUNDSCAPE_MID_HZ      = (2_000, 10_000)  # shrimp, low dolphins
SOUNDSCAPE_HIGH_HZ     = (10_000, 48_000) # echolocation, high dolphins

SOUNDSCAPE_WELCH_NPERSEG = 4096   # Welch FFT window size (samples)
SOUNDSCAPE_BOAT_SCALE    = 5.0    # empirical multiplier: p_low → boat_score [0, 1]

# ─── Stage 6: Clustering ──────────────────────────────────────────────────────

CLUSTER_UMAP_N_COMPONENTS   = 2
CLUSTER_UMAP_N_NEIGHBORS    = 5    # low because datasets are small
CLUSTER_UMAP_MIN_DIST       = 0.1
CLUSTER_HDBSCAN_MIN_CLUSTER = 3    # minimum clips per cluster

# ─── Stage 6: Dasheng thresholds (marine-calibrated) ─────────────────────────
# Marine audio is stationary — terrestrial defaults (3.0, 0.3) are too high.
# Temporal variance in ocean recordings is typically 0.1–1.0 (vs 1–5 terrestrial).
# Cosine diversity between clip halves is typically 0.02–0.15 (vs 0.1–0.5 terrestrial).
DASHENG_TEMPORAL_SCALE  = 0.5   # saturates at temporal_variance ≥ 0.5
DASHENG_DIVERSITY_SCALE = 0.1   # saturates at diversity_score ≥ 0.1
DASHENG_BIO_THRESHOLD   = 0.3   # minimum bio_signal_score to flag as dasheng_complex
