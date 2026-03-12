import { useState, useMemo } from 'react'
import TierBadge from './TierBadge'
import { formatScore, exportTableToCSV } from '../utils'

const MODEL_KEYS = [
  { key: 'perch',        short: 'P',   label: 'Perch 2.0',         color: '#ef4444' },
  { key: 'multispecies', short: 'MS',  label: 'Multispecies',      color: '#f97316' },
  { key: 'humpback',     short: 'HB',  label: 'Humpback',          color: '#eab308' },
  { key: 'naturelm',     short: 'NL',  label: 'NatureLM',          color: '#22c55e' },
  { key: 'biolingual',   short: 'BL',  label: 'BioLingual',        color: '#38bdf8' },
  { key: 'dasheng',      short: 'DS',  label: 'Dasheng',           color: '#a78bfa' },
]

function MiniBar({ value, color }) {
  const pct = Math.round((value || 0) * 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 54 }}>
      <div style={{
        flex: 1, height: 5, borderRadius: 3,
        background: 'var(--border)',
        overflow: 'hidden',
      }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', minWidth: 24, textAlign: 'right' }}>
        {pct}%
      </span>
    </div>
  )
}

const CLUSTER_COLORS = { '-1': '#6b7280', 0: '#2dd4bf', 1: '#38bdf8', 2: '#f97316', 3: '#a78bfa', 4: '#22c55e' }

export default function ReportTable({ rankings, onRowClick }) {
  const [sortKey, setSortKey] = useState('rank')
  const [sortDir, setSortDir] = useState('asc')
  const [tierFilter, setTierFilter] = useState(null)
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState(false)

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir(key === 'rank' ? 'asc' : 'desc') }
  }

  const filtered = useMemo(() => {
    let data = rankings || []
    if (tierFilter) data = data.filter(r => r.tier === tierFilter)
    if (search) {
      const q = search.toLowerCase()
      data = data.filter(r =>
        r.filename.toLowerCase().includes(q) ||
        (r.top_species && r.top_species.toLowerCase().includes(q))
      )
    }
    return [...data].sort((a, b) => {
      let va = sortKey.startsWith('components.')
        ? (a.components?.[sortKey.slice(11)] ?? 0)
        : a[sortKey]
      let vb = sortKey.startsWith('components.')
        ? (b.components?.[sortKey.slice(11)] ?? 0)
        : b[sortKey]
      if (typeof va === 'string') va = va.toLowerCase()
      if (typeof vb === 'string') vb = vb.toLowerCase()
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [rankings, sortKey, sortDir, tierFilter, search])

  const handleExport = () => {
    const headers = ['Rank', 'Filename', 'Score', 'Tier', 'Duration', 'Top Species',
      'Perch', 'Multispecies', 'Humpback', 'NatureLM', 'BioLingual', 'Dasheng',
      'NDSI', 'Boat', 'Cluster', 'Flags']
    const rows = filtered.map(r => [
      r.rank, r.filename, r.score?.toFixed(2), r.tier,
      r.duration_s?.toFixed(1) + 's',
      r.top_species || '—',
      ...(MODEL_KEYS.map(m => ((r.components?.[m.key] || 0) * 100).toFixed(1) + '%')),
      r.ndsi?.toFixed(3) ?? '—',
      r.boat_score?.toFixed(3) ?? '—',
      r.cluster_id ?? '—',
      (r.cascade_flags || []).join('; '),
    ])
    exportTableToCSV(headers, rows, 'dragon_ocean_report.csv')
  }

  const tiers = ['CRITICAL', 'HIGH', 'MODERATE', 'LOW', 'MINIMAL']
  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <span className="sort-icon">↕</span>
    return <span className="sort-icon">{sortDir === 'asc' ? '▲' : '▼'}</span>
  }

  const tierColor = (score) => {
    if (score >= 65) return 'var(--tier-critical)'
    if (score >= 45) return 'var(--tier-high)'
    if (score >= 25) return 'var(--tier-moderate)'
    if (score >= 10) return 'var(--tier-low)'
    return 'var(--tier-minimal)'
  }

  return (
    <div className="stack">
      <div className="filter-bar">
        <input
          className="input"
          placeholder="Search filename or species..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: 240 }}
        />
        <div style={{ display: 'flex', gap: 6 }}>
          <button className={`filter-chip ${!tierFilter ? 'active' : ''}`} onClick={() => setTierFilter(null)}>All</button>
          {tiers.map(t => (
            <button
              key={t}
              className={`filter-chip ${tierFilter === t ? 'active' : ''}`}
              style={tierFilter === t ? { borderColor: `var(--tier-${t.toLowerCase()})`, color: `var(--tier-${t.toLowerCase()})` } : {}}
              onClick={() => setTierFilter(tierFilter === t ? null : t)}
            >{t}</button>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        <button
          className={`btn ${expanded ? 'active' : ''}`}
          onClick={() => setExpanded(e => !e)}
          style={{ fontSize: 12 }}
        >
          {expanded ? '◀ Compact' : '▶ Full detail'}
        </button>
        <button className="btn" onClick={handleExport}>Export CSV</button>
      </div>

      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 4 }}>
        Showing {filtered.length} of {rankings?.length || 0} recordings
      </div>

      <div className="report-table-wrap" style={{ maxHeight: 600, overflowY: 'auto', overflowX: 'auto' }}>
        <table className="report-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('rank')}># <SortIcon col="rank" /></th>
              <th onClick={() => handleSort('filename')}>Filename <SortIcon col="filename" /></th>
              <th onClick={() => handleSort('score')}>Score <SortIcon col="score" /></th>
              <th onClick={() => handleSort('tier')}>Tier <SortIcon col="tier" /></th>
              <th onClick={() => handleSort('duration_s')}>Dur <SortIcon col="duration_s" /></th>
              <th onClick={() => handleSort('top_species')}>Species <SortIcon col="top_species" /></th>
              {expanded && MODEL_KEYS.map(m => (
                <th key={m.key} onClick={() => handleSort(`components.${m.key}`)} style={{ minWidth: 80 }}>
                  <span style={{ color: m.color }}>{m.short}</span> <SortIcon col={`components.${m.key}`} />
                </th>
              ))}
              {expanded && <th onClick={() => handleSort('ndsi')} style={{ minWidth: 64 }}>NDSI <SortIcon col="ndsi" /></th>}
              {expanded && <th onClick={() => handleSort('boat_score')} style={{ minWidth: 64 }}>Boat <SortIcon col="boat_score" /></th>}
              {expanded && <th onClick={() => handleSort('cluster_id')} style={{ minWidth: 54 }}>Cluster <SortIcon col="cluster_id" /></th>}
              <th>Flags</th>
            </tr>
            {/* Full-name legend row when expanded */}
            {expanded && (
              <tr style={{ background: 'transparent' }}>
                <td colSpan={6} />
                {MODEL_KEYS.map(m => (
                  <td key={m.key} style={{ fontSize: 9, color: 'var(--text-dim)', fontStyle: 'italic', paddingTop: 0 }}>
                    {m.label}
                  </td>
                ))}
                <td colSpan={3} />
                <td />
              </tr>
            )}
          </thead>
          <tbody>
            {filtered.map(r => (
              <tr key={r.filename} onClick={() => onRowClick?.(r)}>
                <td style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>{r.rank}</td>
                <td className="filename-cell">{r.filename}</td>
                <td className="score-cell" style={{ color: tierColor(r.score) }}>{formatScore(r.score)}</td>
                <td><TierBadge tier={r.tier} /></td>
                <td>{r.duration_s ? `${r.duration_s.toFixed(0)}s` : '—'}</td>
                <td style={{ color: 'var(--teal)', fontSize: 11 }}>{r.top_species || '—'}</td>
                {expanded && MODEL_KEYS.map(m => (
                  <td key={m.key}>
                    <MiniBar value={r.components?.[m.key]} color={m.color} />
                  </td>
                ))}
                {expanded && (
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11,
                    color: r.ndsi > 0 ? 'var(--teal)' : 'var(--tier-high)' }}>
                    {r.ndsi?.toFixed(2) ?? '—'}
                  </td>
                )}
                {expanded && (
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11,
                    color: r.boat_score > 0.3 ? 'var(--tier-moderate)' : 'var(--text-tertiary)' }}>
                    {r.boat_score?.toFixed(2) ?? '—'}
                  </td>
                )}
                {expanded && (
                  <td>
                    {r.cluster_id !== undefined ? (
                      <span style={{
                        display: 'inline-block', padding: '1px 6px', borderRadius: 10, fontSize: 11,
                        fontFamily: 'var(--font-mono)',
                        background: `${CLUSTER_COLORS[r.cluster_id] || '#6b7280'}22`,
                        color: CLUSTER_COLORS[r.cluster_id] || '#6b7280',
                        border: `1px solid ${CLUSTER_COLORS[r.cluster_id] || '#6b7280'}55`,
                      }}>
                        {r.cluster_id === -1 ? '∅' : `C${r.cluster_id}`}
                      </span>
                    ) : '—'}
                  </td>
                )}
                <td>
                  <div className="flag-list">
                    {(r.cascade_flags || []).slice(0, 3).map(f => (
                      <span key={f} className="flag-tag">{f.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
