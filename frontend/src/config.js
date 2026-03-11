export const API = {
  cascadeResults:  '/api/pipeline/analysis/results.json',
  rankedImportance:'/api/pipeline/ranking/ranked.json',
  rankedCsv:       '/api/pipeline/ranking/ranked.csv',
  spectrogram:        (filename) => `/api/pipeline/analysis/spectrograms/${filename}`,
  cascadeSpectrogram: (filename) => `/api/pipeline/analysis/spectrograms/${filename}`,
  cascadeAnnotation:  (id)       => `/api/pipeline/analysis/annotations/${id}_cascade.json`,
  audio:              (filename) => `/api/audio/${filename}`,
}

export const TIER_CONFIG = {
  CRITICAL: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', label: 'Critical', icon: '!!' },
  HIGH:     { color: '#f97316', bg: 'rgba(249,115,22,0.12)', label: 'High', icon: '!' },
  MODERATE: { color: '#eab308', bg: 'rgba(234,179,8,0.12)', label: 'Moderate', icon: '~' },
  LOW:      { color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', label: 'Low', icon: '-' },
  MINIMAL:  { color: '#6b7280', bg: 'rgba(107,114,128,0.12)', label: 'Minimal', icon: '.' },
}

export const SPECIES_MAP = {
  Oo: 'Orcinus orca (Orca)',
  Mn: 'Megaptera novaeangliae (Humpback)',
  Eg: 'Eubalaena glacialis (Right whale)',
  Be: 'Beaked whale',
  Bp: 'Balaenoptera physalus (Fin whale)',
  Bm: 'Balaenoptera musculus (Blue whale)',
  Ba: 'Balaenoptera acutorostrata (Minke whale)',
}

export const SCORING_DIMENSIONS = [
  { key: 'whale_sustained', label: 'Whale Sustained', weight: 0.20 },
  { key: 'bio_richness', label: 'Bio Richness', weight: 0.20 },
  { key: 'acoustic_diversity', label: 'Acoustic Diversity', weight: 0.20 },
  { key: 'humpback_coverage', label: 'Humpback Coverage', weight: 0.15 },
  { key: 'cross_model', label: 'Cross-Model Agreement', weight: 0.15 },
  { key: 'humpback_peak', label: 'Humpback Peak', weight: 0.05 },
  { key: 'yamnet_top_quality', label: 'YAMNet Quality', weight: 0.05 },
]

export const BAND_CONFIG = {
  infrasonic_whales: { label: 'Infrasonic Whales', color: '#ef4444', range: '10-100 Hz' },
  low_freq_fish:     { label: 'Low Freq Fish', color: '#f97316', range: '50-500 Hz' },
  mid_freq_dolphins: { label: 'Mid Freq Dolphins', color: '#22c55e', range: '500-5000 Hz' },
  high_freq_clicks:  { label: 'High Freq Clicks', color: '#8b5cf6', range: '5-24 kHz' },
}
