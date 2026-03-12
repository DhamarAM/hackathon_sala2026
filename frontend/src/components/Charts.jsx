import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, PointElement, LineElement,
  ArcElement, RadialLinearScale, Filler, Tooltip, Legend,
} from 'chart.js'
import { Bar, Doughnut, Line, Radar, Scatter } from 'react-chartjs-2'
import { TIER_CONFIG, SCORING_DIMENSIONS, SPECIES_MAP, VOCALIZATION_CODES } from '../config'

ChartJS.register(
  CategoryScale, LinearScale, BarElement, PointElement, LineElement,
  ArcElement, RadialLinearScale, Filler, Tooltip, Legend,
)

const chartFont = { family: "'Inter', system-ui, sans-serif", size: 11 }
const gridColor = 'rgba(56,189,248,0.06)'
const tickColor = '#64748b'

// Tier Distribution Doughnut
export function TierDistributionChart({ distribution }) {
  if (!distribution) return null
  const tiers = ['CRITICAL', 'HIGH', 'MODERATE', 'LOW', 'MINIMAL']
  const data = {
    labels: tiers,
    datasets: [{
      data: tiers.map(t => distribution[t] || 0),
      backgroundColor: tiers.map(t => TIER_CONFIG[t].color),
      borderWidth: 0,
      hoverOffset: 6,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '55%',
    plugins: {
      legend: {
        position: 'right',
        labels: { color: tickColor, font: chartFont, padding: 12, usePointStyle: true, pointStyleWidth: 10 },
      },
      tooltip: {
        backgroundColor: '#0f1a2e',
        borderColor: 'rgba(56,189,248,0.2)',
        borderWidth: 1,
        titleFont: chartFont,
        bodyFont: chartFont,
        padding: 10,
      },
    },
  }
  return (
    <div className="chart-container">
      <h3>Tier Distribution</h3>
      <div style={{ height: 220 }}><Doughnut data={data} options={options} /></div>
    </div>
  )
}

// Score Histogram
export function ScoreHistogramChart({ rankings }) {
  if (!rankings?.length) return null
  const bins = Array.from({ length: 10 }, (_, i) => ({ min: i * 10, max: (i + 1) * 10, count: 0 }))
  rankings.forEach(r => {
    const idx = Math.min(Math.floor(r.score / 10), 9)
    bins[idx].count++
  })
  const data = {
    labels: bins.map(b => `${b.min}-${b.max}`),
    datasets: [{
      label: 'Files',
      data: bins.map(b => b.count),
      backgroundColor: bins.map((b, i) => {
        if (b.min >= 65) return TIER_CONFIG.CRITICAL.color
        if (b.min >= 45) return TIER_CONFIG.HIGH.color
        if (b.min >= 25) return TIER_CONFIG.MODERATE.color
        if (b.min >= 10) return TIER_CONFIG.LOW.color
        return TIER_CONFIG.MINIMAL.color
      }),
      borderWidth: 0,
      borderRadius: 4,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: '#0f1a2e', borderColor: 'rgba(56,189,248,0.2)', borderWidth: 1, titleFont: chartFont, bodyFont: chartFont },
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: tickColor, font: chartFont } },
      y: { grid: { color: gridColor }, ticks: { color: tickColor, font: chartFont } },
    },
  }
  return (
    <div className="chart-container">
      <h3>Score Distribution</h3>
      <div style={{ height: 220 }}><Bar data={data} options={options} /></div>
    </div>
  )
}

// Radar Chart for scoring dimensions (all 6 models)
export function ScoringRadarChart({ components }) {
  if (!components) return null
  const data = {
    labels: SCORING_DIMENSIONS.map(d => d.label),
    datasets: [{
      label: 'Score Components',
      data: SCORING_DIMENSIONS.map(d => (components[d.key] || 0) * 100),
      backgroundColor: 'rgba(56,189,248,0.15)',
      borderColor: '#38bdf8',
      borderWidth: 2,
      pointBackgroundColor: '#38bdf8',
      pointRadius: 4,
      pointHoverRadius: 6,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: '#0f1a2e', borderColor: 'rgba(56,189,248,0.2)', borderWidth: 1, titleFont: chartFont, bodyFont: chartFont },
    },
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        grid: { color: gridColor },
        angleLines: { color: gridColor },
        pointLabels: { color: tickColor, font: { ...chartFont, size: 10 } },
        ticks: { display: false },
      },
    },
  }
  return (
    <div className="chart-container">
      <h3>All Models</h3>
      <div style={{ height: 280 }}><Radar data={data} options={options} /></div>
    </div>
  )
}

// CNN Family Radar (Perch, Multispecies, Humpback)
const CNN_MODELS = [
  { key: 'perch',        label: 'Perch 2.0',         desc: 'General bioacoustic triage' },
  { key: 'multispecies', label: 'Multispecies Whale', desc: 'Cetacean species ID' },
  { key: 'humpback',     label: 'Humpback',           desc: 'Humpback vocalization' },
]

// Transformer Family Radar (NatureLM, BioLingual, Dasheng)
const TRANSFORMER_MODELS = [
  { key: 'naturelm',     label: 'NatureLM-BEATs', desc: 'Structural complexity' },
  { key: 'biolingual',   label: 'BioLingual',     desc: 'Zero-shot semantic' },
  { key: 'dasheng',      label: 'Dasheng',         desc: 'Temporal diversity' },
]

function makeRadarOptions(subtitle) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0f1a2e',
        borderColor: 'rgba(56,189,248,0.2)',
        borderWidth: 1,
        titleFont: chartFont,
        bodyFont: chartFont,
        callbacks: {
          label: (ctx) => `${ctx.label}: ${ctx.raw.toFixed(1)}%`,
        },
      },
    },
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        grid: { color: gridColor },
        angleLines: { color: gridColor },
        pointLabels: { color: tickColor, font: { ...chartFont, size: 10 } },
        ticks: { display: false },
      },
    },
  }
}

export function ModelFamilyRadars({ components }) {
  if (!components) return null

  const cnnMean = CNN_MODELS.reduce((s, m) => s + (components[m.key] || 0), 0) / CNN_MODELS.length * 100
  const transMean = TRANSFORMER_MODELS.reduce((s, m) => s + (components[m.key] || 0), 0) / TRANSFORMER_MODELS.length * 100

  const cnnData = {
    labels: CNN_MODELS.map(m => m.label),
    datasets: [{
      label: 'CNN Bio Signal',
      data: CNN_MODELS.map(m => (components[m.key] || 0) * 100),
      backgroundColor: 'rgba(239,68,68,0.12)',
      borderColor: '#ef4444',
      borderWidth: 2,
      pointBackgroundColor: '#ef4444',
      pointRadius: 5,
      pointHoverRadius: 7,
    }],
  }

  const transData = {
    labels: TRANSFORMER_MODELS.map(m => m.label),
    datasets: [{
      label: 'Transformer Bio Signal',
      data: TRANSFORMER_MODELS.map(m => (components[m.key] || 0) * 100),
      backgroundColor: 'rgba(45,212,191,0.12)',
      borderColor: '#2dd4bf',
      borderWidth: 2,
      pointBackgroundColor: '#2dd4bf',
      pointRadius: 5,
      pointHoverRadius: 7,
    }],
  }

  return (
    <div className="grid-2">
      <div className="chart-container">
        <h3>CNN Models <span style={{ fontSize: 11, fontWeight: 400, color: tickColor }}>(domain-specific)</span></h3>
        <div style={{ height: 220 }}><Radar data={cnnData} options={makeRadarOptions('CNN')} /></div>
        <div style={{ fontSize: 11, color: tickColor, textAlign: 'center', marginTop: 4 }}>
          Mean: <span style={{ fontWeight: 700, color: '#ef4444' }}>{cnnMean.toFixed(1)}%</span>
        </div>
        <div style={{ fontSize: 10, color: tickColor, textAlign: 'center', marginTop: 2, fontStyle: 'italic' }}>
          Trained on labeled cetacean/bird data. High precision for known species.
        </div>
      </div>
      <div className="chart-container">
        <h3>Transformer Models <span style={{ fontSize: 11, fontWeight: 400, color: tickColor }}>(domain-agnostic)</span></h3>
        <div style={{ height: 220 }}><Radar data={transData} options={makeRadarOptions('Transformer')} /></div>
        <div style={{ fontSize: 11, color: tickColor, textAlign: 'center', marginTop: 4 }}>
          Mean: <span style={{ fontWeight: 700, color: '#2dd4bf' }}>{transMean.toFixed(1)}%</span>
        </div>
        <div style={{ fontSize: 10, color: tickColor, textAlign: 'center', marginTop: 2, fontStyle: 'italic' }}>
          Self-supervised / zero-shot. More robust to out-of-domain audio.
        </div>
      </div>
    </div>
  )
}

// YAMNet Top Classes Bar Chart
export function YamnetBarChart({ topClasses }) {
  if (!topClasses?.length) return null
  const sorted = [...topClasses].sort((a, b) => b.score - a.score).slice(0, 8)
  const data = {
    labels: sorted.map(c => c.class),
    datasets: [{
      label: 'Score',
      data: sorted.map(c => c.score),
      backgroundColor: sorted.map((_, i) => i === 0 ? '#38bdf8' : 'rgba(56,189,248,0.4)'),
      borderWidth: 0,
      borderRadius: 4,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: '#0f1a2e', borderColor: 'rgba(56,189,248,0.2)', borderWidth: 1, titleFont: chartFont, bodyFont: chartFont },
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: tickColor, font: chartFont }, max: 1 },
      y: { grid: { display: false }, ticks: { color: tickColor, font: chartFont } },
    },
  }
  return (
    <div className="chart-container">
      <h3>Perch 2.0 Top Classes</h3>
      <div style={{ height: Math.max(140, sorted.length * 32) }}><Bar data={data} options={options} /></div>
    </div>
  )
}

// Time Series Line Chart (multispecies or humpback)
export function TimeSeriesChart({ title, dataSeries, threshold, color = '#38bdf8' }) {
  if (!dataSeries?.length) return null
  const many = dataSeries.length > 30
  const labels = many
    ? dataSeries.map((_, i) => (i % Math.ceil(dataSeries.length / 15) === 0) ? `${i + 1}` : '')
    : dataSeries.map((_, i) => `W${i + 1}`)
  const datasets = [{
    label: title,
    data: dataSeries,
    borderColor: color,
    backgroundColor: color.replace(')', ',0.1)').replace('rgb', 'rgba'),
    fill: true,
    tension: 0.3,
    pointRadius: many ? 0 : 3,
    pointHoverRadius: many ? 3 : 5,
    borderWidth: many ? 1.5 : 2,
  }]
  if (threshold !== undefined) {
    datasets.push({
      label: `Threshold (${threshold})`,
      data: dataSeries.map(() => threshold),
      borderColor: '#ef4444',
      borderWidth: 1,
      borderDash: [6, 4],
      pointRadius: 0,
      fill: false,
    })
  }
  const data = { labels, datasets }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: datasets.length > 1, labels: { color: tickColor, font: chartFont, usePointStyle: true } },
      tooltip: { backgroundColor: '#0f1a2e', borderColor: 'rgba(56,189,248,0.2)', borderWidth: 1, titleFont: chartFont, bodyFont: chartFont },
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: tickColor, font: chartFont } },
      y: { grid: { color: gridColor }, ticks: { color: tickColor, font: chartFont }, beginAtZero: true },
    },
  }
  return (
    <div className="chart-container">
      <h3>{title}</h3>
      <div style={{ height: 200 }}><Line data={data} options={options} /></div>
    </div>
  )
}

// Band Energy Bar Chart
export function BandEnergyChart({ bandAnalysis }) {
  if (!bandAnalysis) return null
  const bands = Object.entries(bandAnalysis)
  const colors = ['#ef4444', '#f97316', '#22c55e', '#8b5cf6']
  const data = {
    labels: bands.map(([key]) => key.replace(/_/g, ' ')),
    datasets: [{
      label: 'Mean Energy (relative dB)',
      data: bands.map(([, v]) => v.mean_energy_db),
      backgroundColor: colors,
      borderWidth: 0,
      borderRadius: 4,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: '#0f1a2e', borderColor: 'rgba(56,189,248,0.2)', borderWidth: 1, titleFont: chartFont, bodyFont: chartFont },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: tickColor, font: { ...chartFont, size: 10 } } },
      y: { grid: { color: gridColor }, ticks: { color: tickColor, font: chartFont } },
    },
  }
  return (
    <div className="chart-container">
      <h3>Band Energy Analysis</h3>
      <div style={{ height: 200 }}><Bar data={data} options={options} /></div>
      <div style={{ fontSize: 10, color: '#64748b', marginTop: 6, textAlign: 'center' }}>
        Relative dB (not calibrated to &micro;Pa). Analysis bands optimized for 48 kHz sample rate.
      </div>
    </div>
  )
}

// BioLingual Label Scores Bar Chart
export function BioLingualChart({ labelScores }) {
  if (!labelScores) return null
  const sorted = Object.entries(labelScores).sort((a, b) => b[1] - a[1])
  const BIO_LABELS = new Set([
    'humpback whale song', 'dolphin clicks and whistles', 'shrimp snapping',
    'seal barking', 'bird calls', 'orca killer whale call', 'fish sounds',
  ])
  const data = {
    labels: sorted.map(([label]) => label),
    datasets: [{
      label: 'Score',
      data: sorted.map(([, score]) => score),
      backgroundColor: sorted.map(([label]) => BIO_LABELS.has(label) ? 'rgba(45,212,191,0.7)' : 'rgba(100,116,139,0.4)'),
      borderWidth: 0,
      borderRadius: 4,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: '#0f1a2e', borderColor: 'rgba(56,189,248,0.2)', borderWidth: 1, titleFont: chartFont, bodyFont: chartFont },
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: tickColor, font: chartFont }, max: 1 },
      y: { grid: { display: false }, ticks: { color: tickColor, font: chartFont } },
    },
  }
  return (
    <div className="chart-container">
      <h3>BioLingual Zero-Shot Classification</h3>
      <div style={{ height: Math.max(140, sorted.length * 28) }}><Bar data={data} options={options} /></div>
      <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginTop: 8 }}>
        <span style={{ fontSize: 10, color: tickColor, display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: 'rgba(45,212,191,0.7)', display: 'inline-block' }} /> Biological
        </span>
        <span style={{ fontSize: 10, color: tickColor, display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: 'rgba(100,116,139,0.4)', display: 'inline-block' }} /> Non-bio
        </span>
      </div>
    </div>
  )
}

export function SpeciesDetectionChart({ cascadeData }) {
  if (!cascadeData?.files) return null
  const counts = {}
  Object.values(cascadeData.files).forEach(file => {
    const dets = file.stage2_multispecies?.detections || []
    dets.forEach(d => {
      counts[d.class_code] = (counts[d.class_code] || 0) + 1
    })
  })
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1])
  if (sorted.length === 0) return null

  const isVocalization = (code) => VOCALIZATION_CODES.includes(code)
  const data = {
    labels: sorted.map(([code]) => {
      const full = SPECIES_MAP[code]
      if (!full) return code
      // Extract just the common name part after the scientific name
      const match = full.match(/\(([^)]+)\)$/)
      return match ? match[1] : full
    }),
    datasets: [{
      label: 'Files with detection',
      data: sorted.map(([, count]) => count),
      backgroundColor: sorted.map(([code]) =>
        isVocalization(code) ? 'rgba(56,189,248,0.7)' : 'rgba(45,212,191,0.7)'
      ),
      borderWidth: 0,
      borderRadius: 4,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0f1a2e',
        borderColor: 'rgba(56,189,248,0.2)',
        borderWidth: 1,
        titleFont: chartFont,
        bodyFont: chartFont,
        callbacks: {
          title: (items) => {
            // Find original code by reverse-looking up from sorted array
            const idx = items[0]?.dataIndex
            if (idx === undefined) return ''
            const [code] = sorted[idx]
            return `${code} — ${SPECIES_MAP[code] || code}`
          },
          label: (item) => `${item.raw} / ${cascadeData.total_files} files`,
        },
      },
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: tickColor, font: chartFont }, title: { display: true, text: 'Number of files', color: tickColor, font: chartFont } },
      y: { grid: { display: false }, ticks: { color: tickColor, font: { ...chartFont, weight: 'bold' } } },
    },
  }
  return (
    <div className="chart-container">
      <h3>Species & Vocalization Detections</h3>
      <div style={{ height: Math.max(180, sorted.length * 28) }}><Bar data={data} options={options} /></div>
      <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginTop: 8 }}>
        <span style={{ fontSize: 10, color: tickColor, display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: 'rgba(45,212,191,0.7)', display: 'inline-block' }} /> Species
        </span>
        <span style={{ fontSize: 10, color: tickColor, display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: 'rgba(56,189,248,0.7)', display: 'inline-block' }} /> Vocalization
        </span>
      </div>
    </div>
  )
}

// ─── Cluster Scatter Chart ────────────────────────────────────────────────────

const CLUSTER_PALETTE = {
  '-1': { color: '#6b7280', label: 'Outliers', fill: 'rgba(107,114,128,0.08)' },
    0:  { color: '#2dd4bf', label: 'Cluster 0', fill: 'rgba(45,212,191,0.08)' },
    1:  { color: '#38bdf8', label: 'Cluster 1', fill: 'rgba(56,189,248,0.08)' },
    2:  { color: '#f97316', label: 'Cluster 2', fill: 'rgba(249,115,22,0.08)' },
    3:  { color: '#a78bfa', label: 'Cluster 3', fill: 'rgba(167,139,250,0.08)' },
    4:  { color: '#22c55e', label: 'Cluster 4', fill: 'rgba(34,197,94,0.08)' },
}

function convexHull(pts) {
  if (pts.length < 3) return pts
  const sorted = [...pts].sort((a, b) => a.x - b.x || a.y - b.y)
  const cross = (O, A, B) => (A.x - O.x) * (B.y - O.y) - (A.y - O.y) * (B.x - O.x)
  const lower = []
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length-2], lower[lower.length-1], p) <= 0) lower.pop()
    lower.push(p)
  }
  const upper = []
  for (const p of [...sorted].reverse()) {
    while (upper.length >= 2 && cross(upper[upper.length-2], upper[upper.length-1], p) <= 0) upper.pop()
    upper.push(p)
  }
  return lower.slice(0, -1).concat(upper.slice(0, -1))
}

function padHull(hull, factor = 0.18) {
  if (hull.length === 0) return hull
  const cx = hull.reduce((s, p) => s + p.x, 0) / hull.length
  const cy = hull.reduce((s, p) => s + p.y, 0) / hull.length
  return hull.map(p => ({ x: p.x + (p.x - cx) * factor, y: p.y + (p.y - cy) * factor }))
}

function makeHullPlugin(clusters) {
  return {
    id: 'hullPlugin',
    afterDraw(chart) {
      const { ctx, scales: { x: sx, y: sy } } = chart
      for (const { pts, color, fill } of clusters) {
        if (pts.length === 0) continue
        const hull = padHull(pts.length >= 3 ? convexHull(pts) : pts)
        const px = hull.map(p => ({ x: sx.getPixelForValue(p.x), y: sy.getPixelForValue(p.y) }))
        ctx.save()
        ctx.beginPath()
        if (pts.length === 1) {
          ctx.arc(px[0].x, px[0].y, 22, 0, Math.PI * 2)
        } else {
          ctx.moveTo(px[0].x, px[0].y)
          for (let i = 1; i < px.length; i++) ctx.lineTo(px[i].x, px[i].y)
          ctx.closePath()
        }
        ctx.fillStyle = fill
        ctx.fill()
        ctx.strokeStyle = color
        ctx.lineWidth = 1.5
        ctx.setLineDash([5, 3])
        ctx.stroke()
        ctx.restore()
      }
    },
  }
}

export function ClusterScatterChart({ clusterData, rankings }) {
  if (!clusterData || Object.keys(clusterData).length === 0) return null

  const rankMap = {}
  if (rankings) rankings.forEach(r => { rankMap[r.filename] = r })

  const byCluster = {}
  Object.entries(clusterData).forEach(([filename, d]) => {
    const cid = String(d.cluster_id)
    if (!byCluster[cid]) byCluster[cid] = []
    byCluster[cid].push({
      x: d.umap_x, y: d.umap_y,
      filename,
      tier: rankMap[filename]?.tier,
      score: rankMap[filename]?.score,
      band: d.cluster_dominant_band,
    })
  })

  const clusterIds = Object.keys(byCluster).sort((a, b) => Number(a) - Number(b))

  const datasets = clusterIds.map(cid => {
    const palette = CLUSTER_PALETTE[Number(cid)] || CLUSTER_PALETTE[0]
    return {
      label: `${palette.label} (${byCluster[cid].length})`,
      data: byCluster[cid],
      backgroundColor: palette.color,
      borderColor: palette.color,
      borderWidth: 1.5,
      pointRadius: 7,
      pointHoverRadius: 10,
    }
  })

  const hullClusters = clusterIds.map(cid => {
    const palette = CLUSTER_PALETTE[Number(cid)] || CLUSTER_PALETTE[0]
    return { pts: byCluster[cid], color: palette.color, fill: palette.fill }
  })

  const hullPlugin = makeHullPlugin(hullClusters)

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: {
        display: true,
        labels: { color: tickColor, font: chartFont, usePointStyle: true, pointStyleWidth: 10 },
      },
      tooltip: {
        backgroundColor: '#0f1a2e',
        borderColor: 'rgba(56,189,248,0.2)',
        borderWidth: 1,
        titleFont: chartFont,
        bodyFont: chartFont,
        callbacks: {
          title: (items) => items[0]?.raw?.filename?.replace('.wav', '') || '',
          label: (item) => {
            const d = item.raw
            const parts = [`Band: ${d.band}`]
            if (d.score !== undefined) parts.push(`Score: ${d.score?.toFixed(1)} (${d.tier})`)
            return parts
          },
        },
      },
    },
    scales: {
      x: {
        grid: { color: gridColor },
        ticks: { color: tickColor, font: chartFont },
        title: { display: true, text: 'UMAP dimension 1', color: tickColor, font: chartFont },
      },
      y: {
        grid: { color: gridColor },
        ticks: { color: tickColor, font: chartFont },
        title: { display: true, text: 'UMAP dimension 2', color: tickColor, font: chartFont },
      },
    },
  }

  return (
    <div className="chart-container">
      <h3>Acoustic Embedding Clusters <span style={{ fontSize: 11, fontWeight: 400, color: tickColor }}>(NatureLM-BEATs → UMAP → HDBSCAN)</span></h3>
      <div style={{ height: 380 }}>
        <Scatter data={{ datasets }} options={options} plugins={[hullPlugin]} />
      </div>
      <div style={{ fontSize: 10, color: tickColor, marginTop: 6, textAlign: 'center', fontStyle: 'italic' }}>
        Each point is a clip. Dashed boundaries show cluster hull regions. Outliers (∅) were not assigned to any cluster.
      </div>
    </div>
  )
}
