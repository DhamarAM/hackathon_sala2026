import TierBadge from './TierBadge'
import { ModelFamilyRadars, YamnetBarChart, TimeSeriesChart, BandEnergyChart, BioLingualChart } from './Charts'
import { formatScore, formatDuration } from '../utils'
import { SPECIES_MAP, VOCALIZATION_CODES } from '../config'

export default function AnalysisPanel({ ranking, cascade, basic, section = 'all' }) {
  if (!ranking) return null

  const detections = cascade?.stage2_multispecies?.detections || []
  const speciesDetections = detections.filter(d => !VOCALIZATION_CODES.includes(d.class_code))
  const vocalizationDetections = detections.filter(d => VOCALIZATION_CODES.includes(d.class_code))

  const showSummary = section === 'all' || section === 'summary'
  const showDetail  = section === 'all' || section === 'detail'

  return (
    <div className="stack">
      {/* Summary Header */}
      {showSummary && (
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
                <div style={{ color: 'var(--teal)', fontWeight: 600 }}>{ranking.top_species}</div>
              </div>
            )}
          </div>
          {ranking.cascade_flags && (
            <div className="flag-list" style={{ marginTop: 12 }}>
              {ranking.cascade_flags.map(f => <span key={f} className="flag-tag">{f.replace(/_/g, ' ')}</span>)}
            </div>
          )}
        </div>
      )}

      {/* 1. BioLingual Zero-Shot Classification */}
      {showDetail && cascade?.stage5_biolingual?.label_scores && (
        <BioLingualChart labelScores={cascade.stage5_biolingual.label_scores} />
      )}

      {/* 2. Time series — Multispecies + Humpback */}
      {showDetail && (cascade?.stage2_multispecies?.top_time_series || cascade?.stage3_humpback?.time_series) && (
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
              threshold={0.3}
              color="rgb(56,189,248)"
            />
          )}
        </div>
      )}

      {/* 3. CNN vs Transformer family radars */}
      {showDetail && ranking.components && (
        <ModelFamilyRadars components={ranking.components} />
      )}

      {/* 4. Perch 2.0 top classes bar chart */}
      {showDetail && cascade?.stage1_perch?.top_classes?.length > 0 && (
        <YamnetBarChart topClasses={cascade.stage1_perch.top_classes} />
      )}

      {/* 5. All 6 model classifier cards */}
      {showDetail && cascade && (
        <div className="classifier-grid">
          {/* Stage 1: Perch 2.0 */}
          <div className="classifier-card">
            <div className="classifier-card-header">
              <span className="classifier-name">Stage 1: Perch 2.0</span>
              <span className={`classifier-status ${cascade.stage1_perch?.has_bio_signal ? 'detected' : 'not-detected'}`}>
                {cascade.stage1_perch?.has_bio_signal ? 'Bio Signal' : 'No Bio Signal'}
              </span>
            </div>
            {cascade.stage1_perch?.bio_detections?.length > 0 && (
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
                Bio: {cascade.stage1_perch.bio_detections.map(d => `${d.class} (${(d.score * 100).toFixed(0)}%)`).join(', ')}
              </div>
            )}
            {cascade.stage1_perch?.marine_detections?.length > 0 && (
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Marine: {cascade.stage1_perch.marine_detections.map(d => `${d.class} (${(d.score * 100).toFixed(0)}%)`).join(', ')}
              </div>
            )}
          </div>

          {/* Stage 2: Multispecies */}
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
                Note: Model may over-detect due to boat noise overlap (100&ndash;500 Hz)
              </div>
            )}
          </div>

          {/* Stage 4: NatureLM-BEATs */}
          {cascade.stage4_naturelm && (
            <div className="classifier-card">
              <div className="classifier-card-header">
                <span className="classifier-name">Stage 4: NatureLM-BEATs</span>
                <span className={`classifier-status ${cascade.stage4_naturelm.bio_signal_score > 0.3 ? 'detected' : 'not-detected'}`}>
                  {cascade.stage4_naturelm.bio_signal_score > 0.3 ? 'Bio Signal' : 'Low Signal'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                Magnitude: {formatScore(cascade.stage4_naturelm.magnitude_score)} &middot;
                Entropy: {formatScore(cascade.stage4_naturelm.entropy_score)} &middot;
                Bio: {formatScore(cascade.stage4_naturelm.bio_signal_score)}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                Embedding: {cascade.stage4_naturelm.embedding_dim}D, {cascade.stage4_naturelm.n_frames} frames
              </div>
            </div>
          )}

          {/* Stage 5: BioLingual */}
          {cascade.stage5_biolingual && (
            <div className="classifier-card">
              <div className="classifier-card-header">
                <span className="classifier-name">Stage 5: BioLingual</span>
                <span className={`classifier-status ${cascade.stage5_biolingual.top_is_bio ? 'detected' : 'not-detected'}`}>
                  {cascade.stage5_biolingual.top_is_bio ? 'Bio Top Label' : cascade.stage5_biolingual.top_label}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
                Top: <span style={{ fontWeight: 600 }}>{cascade.stage5_biolingual.top_label}</span> ({(cascade.stage5_biolingual.top_score * 100).toFixed(1)}%)
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                Bio sum: {formatScore(cascade.stage5_biolingual.bio_score_sum)} &middot;
                Bio signal: {formatScore(cascade.stage5_biolingual.bio_signal_score)}
              </div>
            </div>
          )}

          {/* Stage 6: Dasheng */}
          {cascade.stage6_dasheng && (
            <div className="classifier-card">
              <div className="classifier-card-header">
                <span className="classifier-name">Stage 6: Dasheng</span>
                <span className={`classifier-status ${cascade.stage6_dasheng.bio_signal_score > 0.3 ? 'detected' : 'not-detected'}`}>
                  {cascade.stage6_dasheng.bio_signal_score > 0.3 ? 'Complex' : 'Simple'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                Temporal variance: {cascade.stage6_dasheng.temporal_variance?.toFixed(2)} &middot;
                Cosine sim: {cascade.stage6_dasheng.half_cosine_similarity?.toFixed(3)}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                Diversity: {formatScore(cascade.stage6_dasheng.temporal_diversity_score)} &middot;
                Bio signal: {formatScore(cascade.stage6_dasheng.bio_signal_score)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Band Energy */}
      {showDetail && basic?.band_analysis && (
        <BandEnergyChart bandAnalysis={basic.band_analysis} />
      )}

      {/* Annotations */}
      {showDetail && cascade?.annotations?.length > 0 && (
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
      {showDetail && (
        <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textAlign: 'center', padding: '8px 0', fontStyle: 'italic' }}>
          Automated analysis via pretrained models (Perch 2.0, Google Whale, NatureLM, BioLingual, Dasheng). Scores reflect acoustic pattern confidence, not confirmed presence.
        </div>
      )}
    </div>
  )
}
