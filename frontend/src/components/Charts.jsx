import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, PointElement, LineElement,
  ArcElement, RadialLinearScale, Filler, Tooltip, Legend,
} from 'chart.js'
import { Bar, Doughnut, Line, Radar } from 'react-chartjs-2'
import { TIER_CONFIG, SCORING_DIMENSIONS } from '../config'

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

// Radar Chart for scoring dimensions
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
      <h3>Scoring Dimensions</h3>
      <div style={{ height: 280 }}><Radar data={data} options={options} /></div>
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
      y: { grid: { display: false }, ticks: { color: '#f1f5f9', font: chartFont } },
    },
  }
  return (
    <div className="chart-container">
      <h3>YAMNet Top Classes</h3>
      <div style={{ height: Math.max(140, sorted.length * 32) }}><Bar data={data} options={options} /></div>
    </div>
  )
}

// Time Series Line Chart (multispecies or humpback)
export function TimeSeriesChart({ title, dataSeries, threshold, color = '#38bdf8' }) {
  if (!dataSeries?.length) return null
  const labels = dataSeries.map((_, i) => `W${i + 1}`)
  const datasets = [{
    label: title,
    data: dataSeries,
    borderColor: color,
    backgroundColor: color.replace(')', ',0.1)').replace('rgb', 'rgba'),
    fill: true,
    tension: 0.3,
    pointRadius: 3,
    pointHoverRadius: 5,
    borderWidth: 2,
  }]
  if (threshold !== undefined) {
    datasets.push({
      label: 'Threshold',
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
      label: 'Mean Energy (dB)',
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
    </div>
  )
}
