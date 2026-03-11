import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import PipelineDiagram from '../components/PipelineDiagram'
import { loadRankedData, loadCascadeResults } from '../utils'

export default function LandingPage() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    Promise.all([loadRankedData(), loadCascadeResults()])
      .then(([ranked, cascade]) => setStats({
        total: ranked.total_ranked,
        tiers: ranked.tier_distribution,
        yamnetBio: cascade?.yamnet_bio_signals || 0,
        whaleSpecies: cascade?.whale_species_detected || 0,
        humpback: cascade?.humpback_detected || 0,
      }))
      .catch(() => setStats(null))
  }, [])

  return (
    <div className="landing-page">
      {/* Hero Section */}
      <div className="landing-hero">
        <div className="hero-badge">Galapagos Marine Reserve &middot; Acoustic Monitoring</div>
        <h1>Dragon Ocean<br />Analyzer</h1>
        <p className="subtitle">
          AI-powered marine bioacoustics platform that detects and classifies
          underwater species from hydrophone recordings using a 3-stage
          cascade classifier pipeline.
        </p>
        <p className="meta">YAMNet &middot; Multispecies Whale Detector &middot; Humpback Whale Detector</p>

        <div className="hero-cta">
          <Link to="/single" className="btn btn-primary">
            Analyze Recording
          </Link>
          <Link to="/multiple" className="btn">
            View Batch Report
          </Link>
        </div>

        {stats && (
          <div className="landing-stats">
            <div className="stat-card">
              <div className="stat-value" style={{ color: 'var(--text-primary)' }}>{stats.total}</div>
              <div className="stat-label">Recordings Analyzed</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: 'var(--tier-critical)' }}>
                {stats.tiers?.CRITICAL || 0}
              </div>
              <div className="stat-label">Critical Priority</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: 'var(--tier-high)' }}>
                {stats.whaleSpecies}
              </div>
              <div className="stat-label">Whale Detections</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: 'var(--teal)' }}>
                {stats.humpback}
              </div>
              <div className="stat-label">Humpback Signals</div>
            </div>
          </div>
        )}
      </div>

      {/* Pipeline Section */}
      <div className="pipeline-section">
        <h2>Analysis Pipeline</h2>
        <p className="section-sub">
          Three-stage cascade classifier with ensemble voting for marine species detection
        </p>
        <PipelineDiagram />
      </div>

      {/* Features Section */}
      <div className="features-section">
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-card-icon">{'\uD83C\uDF0A'}</div>
            <h3>Acoustic Analysis</h3>
            <p>
              Process hydrophone recordings through spectral analysis,
              4-band frequency decomposition, and transient event detection.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon">{'\uD83D\uDC0B'}</div>
            <h3>Species Detection</h3>
            <p>
              Identify 7 whale species including Orca, Humpback, Blue, and Fin whales
              using Google's multispecies whale classifier.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon">{'\uD83D\uDCCA'}</div>
            <h3>Biological Ranking</h3>
            <p>
              Prioritize recordings using a 7-dimension weighted scoring system
              with 5-tier classification from Critical to Minimal.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon">{'\uD83C\uDFA7'}</div>
            <h3>Synchronized Playback</h3>
            <p>
              Play audio recordings with synchronized spectrogram cursor,
              event markers, and real-time position tracking.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon">{'\uD83E\uDDE0'}</div>
            <h3>Cascade Classifiers</h3>
            <p>
              YAMNet bio-signal detection, multispecies whale identification,
              and dedicated humpback detection in sequence.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon">{'\uD83D\uDCE5'}</div>
            <h3>Export & Report</h3>
            <p>
              Export ranked results to CSV, view per-file radar charts
              of scoring dimensions, and batch-analyze datasets.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
