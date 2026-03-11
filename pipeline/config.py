"""
pipeline/config.py — Configuración centralizada del pipeline.
"""

from pathlib import Path

# ─── Rutas por defecto ────────────────────────────────────────────────────────

ROOT_DIR    = Path(__file__).resolve().parent.parent
OUTPUT_DIR  = ROOT_DIR / "pipeline_output"

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
CHUNK_FRAMES       = 144_000    # 1s a 144kHz; se adapta al sr real
PADDING_S          = 1.0        # Padding alrededor de cada segmento activo
MERGE_GAP_S        = 2.0        # Silencio ≤ N s → fusionar segmentos
MIN_SEGMENT_S      = 2.0        # Descartar clips más cortos que esto
MULTISPECIES_MIN_S = 5.0        # Mínimo requerido por el modelo multispecies (120k samples @ 24kHz)

# ─── Stage 1: YAMNet ─────────────────────────────────────────────────────────

YAMNET_TOP_K        = 5
YAMNET_BIO_THRESHOLD = 0.05     # Score mínimo para flagear clase biológica

YAMNET_BIO_KEYWORDS = {
    'animal', 'whale', 'bird', 'insect', 'frog', 'cricket',
    'roar', 'howl', 'bark', 'chirp', 'squawk', 'singing',
}
YAMNET_MARINE_KEYWORDS = {
    'whale', 'water', 'ocean', 'rain', 'stream', 'splash', 'waves',
}
YAMNET_NOISE_KEYWORDS = {
    'silence', 'white noise', 'static', 'hum', 'buzz',
}

# ─── Stage 2: Multispecies Whale ─────────────────────────────────────────────

MULTISPECIES_THRESHOLD = 0.01   # Score mínimo para reportar especie

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

HUMPBACK_THRESHOLD = 0.1        # Score mínimo por ventana de 1s

# ─── Stage 4: Ranking ─────────────────────────────────────────────────────────

RANK_WEIGHTS = {
    'whale_sustained':    0.18,
    'bio_richness':       0.15,
    'acoustic_diversity': 0.15,
    'humpback_coverage':  0.12,
    'cross_model':        0.12,
    'humpback_peak':      0.05,
    'yamnet_quality':     0.05,
    'ndsi_score':         0.10,  # Stage 5: penaliza dominancia de barcos
    'cluster_signal':     0.08,  # Stage 6: bonus por cluster biológico
}

RANK_TIERS = {
    'CRITICAL': 65,
    'HIGH':     45,
    'MODERATE': 25,
    'LOW':      10,
    'MINIMAL':   0,
}
