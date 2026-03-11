import TierBadge from './TierBadge'
import { ScoringRadarChart, YamnetBarChart, TimeSeriesChart, BandEnergyChart } from './Charts'
import { formatScore, formatDuration } from '../utils'
import { SPECIES_MAP, VOCALIZATION_CODES } from '../config'

export default function AnalysisPanel({ ranking, cascade, basic }) {
  if (!ranking) return null

  const detections = cascade?.stage2_multispecies?.detections || []
  const speciesDetections = detections.filter(d => !VOCALIZATION_CODES.includes(d.class_code))
  const vocalizationDetections = detections.filter(d => VOCALIZATION_CODES.includes(d.class_code))

  return (
    <div className="stack">
      {/* Summary Header */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
              Biological Importance Score
            </div>
            <div style={{ fontSize: 36, fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
              {formatScore(ranking.score)}
            </div>
          </div>
          <TierBadge tier={ranking.tier} />
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Duration</div>
            <div style={{ fontFamily: 'var(--font-mono)' }}>{formatDuration(ranking.duration_s)}</div>
          </div>
          {ranking.top_species && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Top Species</div>
              <div style={{ color: 'var(--teal)', fontWeight: 600 }}>
                {ranking.top_species} {SPECIES_MAP[ranking.top_species] && <span style={{ fontWeight: 400, fontSize: 12 }}>({SPECIES_MAP[ranking.top_species]})</span>}
              </div>
            </div>
          )}
        </div>
        {ranking.cascade_flags && (
          <div className="flag-list" style={{ marginTop: 12 }}>
            {ranking.cascade_flags.map(f => <span key={f} className="flag-tag">{f.replace(/_/g, ' ')}</span>)}
          </div>
        )}
      </div>

      {/* Radar Chart */}
      {ranking.components && (
        <ScoringRadarChart components={ranking.components} />
      )}

      {/* Cascade Classifiers */}
      {cascade && (
        <div className="classifier-grid">
          {/* Stage 1: YAMNet */}
          <div className="classifier-card">
            <div className="classifier-card-header">
              <span className="classifier-name">Stage 1: YAMNet</span>
              <span className={`classifier-status ${cascade.stage1_yamnet?.has_bio_signal ? 'detected' : 'not-detected'}`}>
                {cascade.stage1_yamnet?.has_bio_signal ? 'Bio Signal' : 'No Bio Signal'}
              </span>
            </div>
            {cascade.stage1_yamnet?.bio_detections?.length > 0 && (
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
                Bio: {cascade.stage1_yamnet.bio_detections.map(d => `${d.class} (${(d.score * 100).toFixed(0)}%)`).join(', ')}
              </div>
            )}
            {cascade.stage1_yamnet?.marine_detections?.length > 0 && (
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Marine: {cascade.stage1_yamnet.marine_detections.map(d => `${d.class} (${(d.score * 100).toFixed(0)}%)`).join(', ')}
              </div>
            )}
          </div>

          {/* Stage 2: Multispecies — All Detections */}
          <div className="classifier-card">
            <div className="classifier-card-header">
              <span className="classifier-name">Stage 2: Multispecies</span>
              <span className={`classifier-status ${cascade.stage2_multispecies?.any_whale_detected ? 'detected' : 'not-detected'}`}>
                {cascade.stage2_multispecies?.any_whale_detected ? 'Whale Detected' : 'Below Threshold'}
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 8 }}>
              Windows: {cascade.stage2_multispecies?.num_windows}
            </div>
            {speciesDetections.length > 0 && (
              <div style={{ marginBottom: 6 }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>Species</div>
                {speciesDetections.map(d => (
                  <div key={d.class_code} style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 2 }}>
                    <span style={{ color: 'var(--teal)', fontWeight: 600 }}>{d.class_code}</span>
                    {' '}({SPECIES_MAP[d.class_code] || d.species}): max {(d.max_score * 100).toFixed(1)}%, mean {(d.mean_score * 100).toFixed(1)}%
                  </div>
                ))}
              </div>
            )}
            {vocalizationDetections.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>Vocalizations</div>
                {vocalizationDetections.map(d => (
                  <div key={d.class_code} style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 2 }}>
                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{d.class_code}</span>
                    {' '}({SPECIES_MAP[d.class_code] || d.species}): max {(d.max_score * 100).toFixed(1)}%, mean {(d.mean_score * 100).toFixed(1)}%
                  </div>
                ))}
              </div>
            )}
            {detections.length === 0 && (
              <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>No detections above threshold</div>
            )}
          </div>

          {/* Stage 3: Humpback */}
          <div className="classifier-card">
            <div className="classifier-card-header">
              <span className="classifier-name">Stage 3: Humpback</span>
              <span className={`classifier-status ${cascade.stage3_humpback?.humpback_detected ? 'detected' : 'not-detected'}`}>
                {cascade.stage3_humpback?.humpback_detected ? 'Humpback-Consistent' : 'Not Detected'}
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
              Max: {formatScore(cascade.stage3_humpback?.max_score)} &middot; Mean: {formatScore(cascade.stage3_humpback?.mean_score)} &middot; Windows: {cascade.stage3_humpback?.num_windows}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
              Above threshold: {((cascade.stage3_humpback?.fraction_above_threshold || 0) * 100).toFixed(0)}%
            </div>
            {cascade.stage3_humpback?.humpback_detected && (
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 6, fontStyle: 'italic' }}>
                Note: Model may over-detect due to boat noise overlap (100&ndash;1000 Hz)
              </div>
            )}
          </div>
        </div>
      )}

      {/* YAMNet bar chart */}
      {cascade?.stage1_yamnet?.top_classes && (
        <YamnetBarChart topClasses={cascade.stage1_yamnet.top_classes} />
      )}

      {/* Time series */}
      <div className="grid-2">
        {cascade?.stage2_multispecies?.top_time_series && (
          <TimeSeriesChart
            title={`Multispecies: ${cascade.stage2_multispecies.top_species || 'Top Species'}`}
            dataSeries={cascade.stage2_multispecies.top_time_series}
            threshold={0.1}
            color="rgb(45,212,191)"
          />
        )}
        {cascade?.stage3_humpback?.time_series && (
          <TimeSeriesChart
            title="Humpback Detection"
            dataSeries={cascade.stage3_humpback.time_series}
            threshold={0.1}
            color="rgb(56,189,248)"
          />
        )}
      </div>

      {/* Band Energy */}
      {basic?.band_analysis && (
        <BandEnergyChart bandAnalysis={basic.band_analysis} />
      )}

      {/* Annotations */}
      {cascade?.annotations?.length > 0 && (
        <div className="card">
          <div className="card-title">Annotations</div>
          <ul className="annotation-list">
            {cascade.annotations.map((a, i) => (
              <li key={i} className="annotation-item">{a}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Methodology note */}
      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textAlign: 'center', padding: '8px 0', fontStyle: 'italic' }}>
        Automated analysis via pretrained models (YAMNet, Google Whale). Scores reflect acoustic pattern confidence, not confirmed presence.
      </div>
    </div>
  )
}
