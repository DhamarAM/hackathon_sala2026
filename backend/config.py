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
MULTISPECIES_MIN_S = 5.0        # Minimum required by the multispecies model (120k samples @ 24kHz)

# ─── Stage 1: YAMNet ─────────────────────────────────────────────────────────

YAMNET_TOP_K        = 5
YAMNET_BIO_THRESHOLD = 0.05     # Minimum score to flag a biological class

YAMNET_BIO_KEYWORDS = {
    'animal', 'whale', 'bird', 'insect', 'frog', 'cricket',
    'roar', 'howl', 'bark', 'chirp', 'squawk',
}
YAMNET_MARINE_KEYWORDS = {
    'whale', 'water', 'ocean', 'rain', 'stream', 'splash', 'waves',
}
YAMNET_NOISE_KEYWORDS = {
    'silence', 'white noise', 'static', 'hum', 'buzz',
}

# ─── Stage 2: Multispecies Whale ─────────────────────────────────────────────

MULTISPECIES_THRESHOLD     = 0.01   # Minimum score to list species in detections[]
MULTISPECIES_DETECTION_THR = 0.10   # Minimum score for confirmed detection (activates whale_species flag)

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

RANK_WEIGHTS = {
    'whale_sustained':    0.18,
    'bio_richness':       0.15,
    'acoustic_diversity': 0.15,
    'humpback_coverage':  0.12,
    'cross_model':        0.12,
    'humpback_peak':      0.05,
    'yamnet_quality':     0.05,
    'ndsi_score':         0.10,  # Stage 5: penalizes boat noise dominance
    'cluster_signal':     0.08,  # Stage 6: bonus for biological cluster
}

RANK_TIERS = {
    'CRITICAL': 65,
    'HIGH':     45,
    'MODERATE': 25,
    'LOW':      10,
    'MINIMAL':   0,
}
