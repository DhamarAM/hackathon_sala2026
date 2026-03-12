import { useState, useEffect } from 'react'
import ReportTable from '../components/ReportTable'
import DetailModal from '../components/DetailModal'
import { TierDistributionChart, ScoreHistogramChart, SpeciesDetectionChart, ClusterScatterChart } from '../components/Charts'
import { loadRankedData, loadCascadeResults, fetchJSON } from '../utils'
import { API } from '../config'

export default function MultipleObservations() {
  const [rankedData, setRankedData] = useState(null)
  const [cascadeData, setCascadeData] = useState(null)
  const [clusterData, setClusterData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedRow, setSelectedRow] = useState(null)

  useEffect(() => {
    Promise.all([
      loadRankedData(),
      loadCascadeResults(),
      fetchJSON(API.clusters).catch(() => null),
    ])
      .then(([ranked, cascade, clusters]) => {
        setRankedData(ranked)
        setCascadeData(cascade)
        setClusterData(clusters)
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

  return (
    <div className="stack">
      <div className="section-header">
        <h1>Batch Report</h1>
      </div>

      {rankedData?.total_ranked != null && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, padding: '16px 0 8px' }}>
          <div style={{
            fontSize: 64, fontWeight: 900, fontFamily: 'var(--font-mono)',
            color: 'var(--teal)', lineHeight: 1,
          }}>
            {rankedData.total_ranked}
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', letterSpacing: 1, textTransform: 'uppercase' }}>
            recordings analyzed
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
            Galapagos Marine Reserve · 2019
          </div>
        </div>
      )}

      {/* Tier + Score distribution */}
      <div className="grid-2">
        <TierDistributionChart distribution={rankedData?.tier_distribution} />
        <ScoreHistogramChart rankings={rankedData?.rankings} />
      </div>

      {/* Species Detection Summary */}
      <SpeciesDetectionChart cascadeData={cascadeData} />

      {/* Acoustic Embedding Clusters */}
      {clusterData && (
        <ClusterScatterChart clusterData={clusterData} rankings={rankedData?.rankings} />
      )}

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
