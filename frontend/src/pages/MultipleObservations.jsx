import { useState, useEffect } from 'react'
import ReportTable from '../components/ReportTable'
import DetailModal from '../components/DetailModal'
import { TierDistributionChart, ScoreHistogramChart, SpeciesDetectionChart } from '../components/Charts'
import { loadRankedData, loadCascadeResults } from '../utils'

export default function MultipleObservations() {
  const [rankedData, setRankedData] = useState(null)
  const [cascadeData, setCascadeData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedRow, setSelectedRow] = useState(null)

  useEffect(() => {
    Promise.all([loadRankedData(), loadCascadeResults()])
      .then(([ranked, cascade]) => {
        setRankedData(ranked)
        setCascadeData(cascade)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading"><div className="spinner" /> Loading batch analysis data...</div>
  if (error) return (
    <div className="empty-state">
      <div className="empty-state-icon">&#9888;</div>
      <div>Failed to load data</div>
      <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 8 }}>{error}</div>
    </div>
  )

  const pipelineStats = cascadeData ? [
    { label: 'Total Files', value: cascadeData.total_files },
    { label: 'YAMNet Bio Signals', value: cascadeData.yamnet_bio_signals },
    { label: 'Whale Species', value: cascadeData.whale_species_detected },
    { label: 'Humpback-Consistent*', value: cascadeData.humpback_detected },
  ] : []

  return (
    <div className="stack">
      <div className="section-header">
        <h1>Batch Report</h1>
        <div className="section-actions">
          <span style={{ fontSize: 12, color: 'var(--text-tertiary)', alignSelf: 'center' }}>
            {rankedData?.total_ranked || 0} recordings analyzed
          </span>
        </div>
      </div>

      {/* Pipeline Summary Stats */}
      <div className="grid-4">
        {pipelineStats.map(s => (
          <div key={s.label} className="card" style={{ textAlign: 'center' }}>
            <div className="card-value">{s.value}</div>
            <div className="card-subtitle">{s.label}</div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textAlign: 'center', marginTop: -8, fontStyle: 'italic' }}>
        *Humpback model may over-detect due to frequency overlap with boat noise (100&ndash;1000 Hz). Scores indicate acoustic pattern confidence.
      </div>

      {/* Charts */}
      <div className="grid-2">
        <TierDistributionChart distribution={rankedData?.tier_distribution} />
        <ScoreHistogramChart rankings={rankedData?.rankings} />
      </div>

      {/* Species Detection Summary */}
      <SpeciesDetectionChart cascadeData={cascadeData} />

      {/* Report Table */}
      <ReportTable
        rankings={rankedData?.rankings}
        onRowClick={setSelectedRow}
      />

      {/* Detail Modal */}
      {selectedRow && (
        <DetailModal ranking={selectedRow} onClose={() => setSelectedRow(null)} />
      )}
    </div>
  )
}
