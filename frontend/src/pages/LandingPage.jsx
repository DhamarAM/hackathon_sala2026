import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import PipelineDiagram from '../components/PipelineDiagram'
import { IconWave, IconWhale, IconBarChart, IconHeadphones, IconBrain, IconExport } from '../components/Icons'
import { loadRankedData, loadCascadeResults } from '../utils'

export default function LandingPage() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    Promise.all([loadRankedData(), loadCascadeResults()])
      .then(([ranked, cascade]) => setStats({
        total: ranked.total_ranked,
        tiers: ranked.tier_distribution,
        yamnetBio: cascade?.bio_signals || 0,
        whaleSpecies: cascade?.whale_detected || 0,
        humpback: cascade?.humpback_detected || 0,
      }))
      .catch(() => setStats(null))
  }, [])

  return (
    <div className="landing-page">
      {/* Scientific Context */}
      <div className="disclaimer-banner">
        Automated analysis using pretrained AI models. High scores indicate acoustic patterns consistent with species vocalizations, not confirmed presence.
      </div>

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
              <div className="stat-label">High Bio-Interest</div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>Score &ge; 65</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: 'var(--tier-high)' }}>
                {stats.whaleSpecies}
              </div>
              <div className="stat-label">Whale Species Detections</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: 'var(--teal)' }}>
                {stats.humpback}
              </div>
              <div className="stat-label">Humpback-Consistent Signals*</div>
            </div>
          </div>
        )}
        {stats && (
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 12, position: 'relative' }}>
            *Humpback model may over-detect due to frequency overlap with boat noise (100&ndash;1000 Hz). Threshold = 0.1.
          </div>
        )}
      </div>

      {/* Pipeline Section */}
      <div className="pipeline-section">
        <h2>Analysis Pipeline</h2>
        <p className="section-sub">
          Three-stage sequential cascade classifier with biological importance ranking
        </p>
        <PipelineDiagram />
      </div>

      {/* Features Section */}
      <div className="features-section">
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-card-icon"><IconWave size={28} /></div>
            <h3>Acoustic Analysis</h3>
            <p>
              Process hydrophone recordings through spectral analysis,
              4-band frequency decomposition, and transient event detection.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconWhale size={28} /></div>
            <h3>Species Detection</h3>
            <p>
              Detect 12 whale and dolphin sound classes across 7 species and 5 vocalization
              types using Google's multispecies classifier.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconBarChart size={28} /></div>
            <h3>Biological Ranking</h3>
            <p>
              Prioritize recordings using a 7-dimension weighted scoring system
              with 5-tier classification from Critical to Minimal.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconHeadphones size={28} /></div>
            <h3>Synchronized Playback</h3>
            <p>
              Play audio recordings with synchronized spectrogram cursor,
              event markers, and real-time position tracking.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconBrain size={28} /></div>
            <h3>Cascade Classifiers</h3>
            <p>
              YAMNet bio-signal gating, multispecies whale identification,
              and dedicated humpback detection in sequence.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconExport size={28} /></div>
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
