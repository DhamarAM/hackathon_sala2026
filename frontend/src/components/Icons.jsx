// Inline SVG icons — no emoji, no external dependencies
// Each returns an <svg> element at current font color

const s = { width: '1em', height: '1em', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', verticalAlign: 'middle' }
const sf = { ...s, fill: 'currentColor', stroke: 'none' }

export const IconWave = ({ size = 24 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <path d="M2 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0" />
    <path d="M2 17c2-3 4-3 6 0s4 3 6 0 4-3 6 0" opacity="0.5" />
    <path d="M2 7c2-3 4-3 6 0s4 3 6 0 4-3 6 0" opacity="0.5" />
  </svg>
)

export const IconSpectrum = ({ size = 24 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <rect x="3" y="14" width="3" height="7" rx="1" fill="currentColor" opacity="0.4" />
    <rect x="8" y="9" width="3" height="12" rx="1" fill="currentColor" opacity="0.6" />
    <rect x="13" y="4" width="3" height="17" rx="1" fill="currentColor" opacity="0.8" />
    <rect x="18" y="7" width="3" height="14" rx="1" fill="currentColor" />
  </svg>
)

export const IconSearch = ({ size = 24 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <circle cx="11" cy="11" r="7" />
    <path d="M21 21l-4.35-4.35" />
  </svg>
)

export const IconWhale = ({ size = 24 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <path d="M3 13c0-4 3-8 8-8 4 0 7 2 9 5l1-3v6h-3c-1 3-4 5-7 5-5 0-8-2-8-5z" />
    <circle cx="8" cy="11" r="1" fill="currentColor" />
    <path d="M2 17c1 1 3 2 5 2" opacity="0.5" />
  </svg>
)

export const IconRanking = ({ size = 24 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <path d="M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7z" />
  </svg>
)

export const IconHeadphones = ({ size = 24 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <path d="M3 18v-6a9 9 0 0118 0v6" />
    <path d="M21 19a2 2 0 01-2 2h-1a2 2 0 01-2-2v-3a2 2 0 012-2h3v5zM3 19a2 2 0 002 2h1a2 2 0 002-2v-3a2 2 0 00-2-2H3v5z" />
  </svg>
)

export const IconBrain = ({ size = 24 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <path d="M12 2a5 5 0 00-4.8 3.6A4 4 0 004 9.5a4 4 0 00.5 5.1A4.5 4.5 0 007 20h10a4.5 4.5 0 002.5-5.4A4 4 0 0020 9.5a4 4 0 00-3.2-3.9A5 5 0 0012 2z" />
    <path d="M12 2v20" strokeDasharray="2 3" opacity="0.4" />
  </svg>
)

export const IconExport = ({ size = 24 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
)

export const IconVolumeHigh = ({ size = 16 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="currentColor" stroke="none" />
    <path d="M15.54 8.46a5 5 0 010 7.07" />
    <path d="M19.07 4.93a10 10 0 010 14.14" opacity="0.4" />
  </svg>
)

export const IconVolumeMute = ({ size = 16 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="currentColor" stroke="none" />
    <line x1="23" y1="9" x2="17" y2="15" />
    <line x1="17" y1="9" x2="23" y2="15" />
  </svg>
)

// Sidebar / Navigation icons
export const IconHome = ({ size = 16 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
    <polyline points="9 22 9 12 15 12 15 22" />
  </svg>
)

export const IconWaveform = ({ size = 16 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <line x1="4" y1="8" x2="4" y2="16" />
    <line x1="8" y1="4" x2="8" y2="20" />
    <line x1="12" y1="6" x2="12" y2="18" />
    <line x1="16" y1="4" x2="16" y2="20" />
    <line x1="20" y1="8" x2="20" y2="16" />
  </svg>
)

export const IconList = ({ size = 16 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <line x1="8" y1="6" x2="21" y2="6" />
    <line x1="8" y1="12" x2="21" y2="12" />
    <line x1="8" y1="18" x2="21" y2="18" />
    <line x1="3" y1="6" x2="3.01" y2="6" strokeWidth="3" />
    <line x1="3" y1="12" x2="3.01" y2="12" strokeWidth="3" />
    <line x1="3" y1="18" x2="3.01" y2="18" strokeWidth="3" />
  </svg>
)

// Upload area
export const IconUpload = ({ size = 40 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size, opacity: 0.6 }}>
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
)

// Chart / bar chart
export const IconBarChart = ({ size = 24 }) => (
  <svg viewBox="0 0 24 24" style={{ ...s, width: size, height: size }}>
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
  </svg>
)
