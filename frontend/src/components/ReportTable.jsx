import { useState, useMemo } from 'react'
import TierBadge from './TierBadge'
import { formatScore, exportTableToCSV } from '../utils'
import { SPECIES_MAP } from '../config'

export default function ReportTable({ rankings, onRowClick }) {
  const [sortKey, setSortKey] = useState('rank')
  const [sortDir, setSortDir] = useState('asc')
  const [tierFilter, setTierFilter] = useState(null)
  const [search, setSearch] = useState('')

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
        (r.top_species && SPECIES_MAP[r.top_species]?.toLowerCase().includes(q)) ||
        (r.top_species && r.top_species.toLowerCase().includes(q))
      )
    }
    return [...data].sort((a, b) => {
      let va = a[sortKey], vb = b[sortKey]
      if (typeof va === 'string') va = va.toLowerCase()
      if (typeof vb === 'string') vb = vb.toLowerCase()
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [rankings, sortKey, sortDir, tierFilter, search])

  const handleExport = () => {
    const headers = ['Rank', 'Filename', 'Score', 'Tier', 'Duration', 'Top Species', 'Flags']
    const rows = filtered.map(r => [
      r.rank, r.filename, r.score?.toFixed(2), r.tier,
      r.duration_s?.toFixed(1) + 's',
      r.top_species || '—',
      (r.cascade_flags || []).join('; '),
    ])
    exportTableToCSV(headers, rows, 'dragon_ocean_report.csv')
  }

  const tiers = ['CRITICAL', 'HIGH', 'MODERATE', 'LOW', 'MINIMAL']
  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <span className="sort-icon">{'\u2195'}</span>
    return <span className="sort-icon">{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>
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
          <button
            className={`filter-chip ${!tierFilter ? 'active' : ''}`}
            onClick={() => setTierFilter(null)}
          >All</button>
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
        <button className="btn" onClick={handleExport}>Export CSV</button>
      </div>

      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 4 }}>
        Showing {filtered.length} of {rankings?.length || 0} recordings
      </div>

      <div className="report-table-wrap" style={{ maxHeight: 600, overflowY: 'auto' }}>
        <table className="report-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('rank')}># <SortIcon col="rank" /></th>
              <th onClick={() => handleSort('filename')}>Filename <SortIcon col="filename" /></th>
              <th onClick={() => handleSort('score')}>Score <SortIcon col="score" /></th>
              <th onClick={() => handleSort('tier')}>Tier <SortIcon col="tier" /></th>
              <th onClick={() => handleSort('duration_s')}>Duration <SortIcon col="duration_s" /></th>
              <th onClick={() => handleSort('top_species')}>Species <SortIcon col="top_species" /></th>
              <th>Flags</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(r => (
              <tr key={r.filename} onClick={() => onRowClick?.(r)}>
                <td style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>{r.rank}</td>
                <td className="filename-cell">{r.filename}</td>
                <td className="score-cell" style={{ color: tierColor(r.score) }}>
                  {formatScore(r.score)}
                </td>
                <td><TierBadge tier={r.tier} /></td>
                <td>{r.duration_s ? `${r.duration_s.toFixed(0)}s` : '—'}</td>
                <td style={{ color: 'var(--teal)' }}>{r.top_species || '—'}</td>
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
