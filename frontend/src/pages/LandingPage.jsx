import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import PipelineDiagram from '../components/PipelineDiagram'
import { IconWave, IconWhale, IconBarChart, IconHeadphones, IconBrain, IconExport } from '../components/Icons'
import { loadRankedData } from '../utils'

export default function LandingPage() {
  const [total, setTotal] = useState(null)

  useEffect(() => {
    loadRankedData().then(r => setTotal(r?.total_ranked ?? null)).catch(() => {})
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
          AI-powered marine bioacoustics platform that classifies underwater species
          from hydrophone recordings using a 6-model ensemble (3 CNN + 3 Transformer),
          all running independently and contributing equally to the final biological
          importance score.
        </p>
        <p className="meta">Perch 2.0 &middot; Multispecies Whale &middot; Humpback &middot; NatureLM-BEATs &middot; BioLingual &middot; Dasheng</p>

        <div className="hero-cta">
          <Link to="/single" className="btn btn-primary">Analyze Recording</Link>
          <Link to="/multiple" className="btn">View Batch Report</Link>
        </div>

        {total !== null && (
          <div style={{
            marginTop: 32, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
          }}>
            <div style={{
              fontSize: 52, fontWeight: 900, fontFamily: 'var(--font-mono)',
              color: 'var(--teal)', lineHeight: 1,
            }}>
              {total}
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', letterSpacing: 1, textTransform: 'uppercase' }}>
              recordings analyzed
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              Galapagos Marine Reserve · 2019
            </div>
          </div>
        )}
      </div>

      {/* Pipeline Section */}
      <div className="pipeline-section">
        <h2>Analysis Pipeline</h2>
        <p className="section-sub">
          6-model ensemble (3 CNN + 3 Transformer) — all models run independently in parallel,
          each contributing an equal-weight <code style={{ fontSize: 12 }}>bio_signal_score</code> to the final biological importance ranking
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
              Process hydrophone recordings through mel spectrogram analysis,
              4-band frequency decomposition, and transient event detection.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconWhale size={28} /></div>
            <h3>Species Detection</h3>
            <p>
              Identify 12 whale and dolphin sound classes across 7 species and 5 vocalization
              types using Google's Multispecies Whale detector.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconBarChart size={28} /></div>
            <h3>Biological Ranking</h3>
            <p>
              Prioritize recordings using a 6-model equal-weight scoring system
              with 5-tier classification from Critical to Minimal.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconHeadphones size={28} /></div>
            <h3>Synchronized Playback</h3>
            <p>
              Play audio recordings with synchronized spectrogram cursor,
              event markers, and real-time frequency-time position tracking.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconBrain size={28} /></div>
            <h3>Ensemble Classifiers</h3>
            <p>
              3 CNN models (Perch 2.0, Multispecies Whale, Humpback) and 3 Transformer
              models (NatureLM-BEATs, BioLingual, Dasheng) run in parallel — each capturing
              different acoustic dimensions, from species-specific patterns to structural complexity.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-card-icon"><IconExport size={28} /></div>
            <h3>Export &amp; Report</h3>
            <p>
              Export ranked results to CSV, view per-file CNN vs Transformer radar charts,
              acoustic embedding cluster maps, and full batch analysis reports.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
