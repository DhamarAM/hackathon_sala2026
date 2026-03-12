export const API = {
  cascadeResults:     '/api/pipeline/analysis/results.json',
  rankedImportance:   '/api/pipeline/ranking/ranked.json',
  rankedCsv:          '/api/pipeline/ranking/ranked.csv',
  spectrogram:        (id) => `/api/pipeline/spectrograms/${id}.png`,
  cascadeSpectrogram: (filename) => `/api/pipeline/analysis/spectrograms/${filename}`,
  cleanSpectrogram:   (filename) => `/api/clean-spectrogram/${filename}`,
  cascadeAnnotation:  (id)       => `/api/pipeline/analysis/annotations/${id}_cascade.json`,
  chartData:          (id) => `/api/pipeline/analysis/charts/${id}_charts.json`,
  audio:              (filename) => `/api/audio/${filename}`,
  audioStatus:        (filename) => `/api/audio/status/${filename}`,
  audioDownload:      (filename) => `/api/audio/download/${filename}`,
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
  Mn: 'Megaptera novaeangliae (Humpback whale)',
  Eg: 'Eubalaena glacialis (Right whale)',
  Bp: 'Balaenoptera physalus (Fin whale)',
  Bm: 'Balaenoptera musculus (Blue whale)',
  Ba: 'Balaenoptera acutorostrata (Minke whale)',
  Be: 'Mesoplodon/Ziphius (Beaked whale)',
  Call: 'Whale call (generic vocalization)',
  Echolocation: 'Echolocation click (odontocetes)',
  Gunshot: 'Gunshot call (right whale surface)',
  Upcall: 'Upcall (right whale contact call)',
  Whistle: 'Dolphin/whale whistle (tonal FM)',
}

export const VOCALIZATION_CODES = ['Call', 'Echolocation', 'Gunshot', 'Upcall', 'Whistle']
export const SPECIES_CODES = ['Oo', 'Mn', 'Eg', 'Bp', 'Bm', 'Ba', 'Be']

// Equal-weight model scoring: score = mean(bio_signal_score per model) × 100
export const SCORING_DIMENSIONS = [
  { key: 'perch',        label: 'Perch 2.0',         weight: 1/6 },
  { key: 'multispecies', label: 'Multispecies Whale', weight: 1/6 },
  { key: 'humpback',     label: 'Humpback',           weight: 1/6 },
  { key: 'naturelm',     label: 'NatureLM',           weight: 1/6 },
  { key: 'biolingual',   label: 'BioLingual',         weight: 1/6 },
  { key: 'dasheng',      label: 'Dasheng',            weight: 1/6 },
]

export const BAND_CONFIG = {
  infrasonic_whales: { label: 'Infrasonic Whales', color: '#ef4444', range: '10-100 Hz', note: 'Mysticete moans (bio range extends to 4 kHz)' },
  low_freq_fish:     { label: 'Low Freq Fish', color: '#f97316', range: '50-500 Hz', note: 'Fish chorus, overlaps boat noise 100-1000 Hz' },
  mid_freq_dolphins: { label: 'Mid Freq Dolphins', color: '#22c55e', range: '500-5000 Hz', note: 'Dolphin whistles extend to 20 kHz in nature' },
  high_freq_clicks:  { label: 'High Freq Clicks', color: '#8b5cf6', range: '5-24 kHz', note: 'Limited by 48 kHz Pilot SR (Nyquist = 24 kHz)' },
}
