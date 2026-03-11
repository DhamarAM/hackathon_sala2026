import { API } from './config'

export async function fetchJSON(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`)
  return res.json()
}

export async function loadRankedData() {
  return fetchJSON(API.rankedImportance)
}

export async function loadCascadeResults() {
  return fetchJSON(API.cascadeResults)
}

export async function loadFileAnnotation(filename) {
  const id = filename.replace('.wav', '')
  const cascade = await fetchJSON(API.cascadeAnnotation(id)).catch(() => null)
  return { basic: null, cascade }
}

export function getFileId(filename) {
  return filename.replace('.wav', '')
}

export function formatScore(score) {
  return typeof score === 'number' ? score.toFixed(2) : '—'
}

export function formatDuration(seconds) {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

export function formatFrequency(hz) {
  if (hz >= 1000) return `${(hz / 1000).toFixed(0)} kHz`
  return `${hz} Hz`
}

export function exportTableToCSV(headers, rows, filename = 'export.csv') {
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
  ].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}
