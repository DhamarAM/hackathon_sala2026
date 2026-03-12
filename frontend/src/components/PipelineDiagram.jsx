import { IconWave, IconSpectrum, IconSearch, IconWhale, IconRanking } from './Icons'

export default function PipelineDiagram() {
  const stages = [
    {
      icon: <IconWave size={24} />,
      title: 'SoundTrap ST300',
      desc: 'Hydrophone capture from the Galapagos Marine Reserve (48 kHz)',
    },
    {
      icon: <IconSpectrum size={24} />,
      title: 'Audio Segmentation',
      desc: 'Silence removal and active-segment extraction (Stage 0)',
    },
    {
      icon: <IconSearch size={24} />,
      title: 'AI Ensemble Classifier',
      desc: 'Perch 2.0 · Multispecies · Humpback · NatureLM · BioLingual · Dasheng — 6 models in parallel',
    },
    {
      icon: <IconWhale size={24} />,
      title: 'Soundscape & Clustering',
      desc: 'NDSI acoustic indices + UMAP/HDBSCAN embedding clusters (Stages 5–6)',
    },
    {
      icon: <IconRanking size={24} />,
      title: 'Ranking & Report',
      desc: '6-model equal-weight scoring (mean bio_signal_score × 100) with 5-tier classification',
    },
  ]

  const ArrowSvg = () => (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 14h16m0 0l-6-6m6 6l-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )

  return (
    <div className="pipeline">
      {stages.map((stage, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
          <div className="pipeline-stage">
            <div className="pipeline-stage-num">{i + 1}</div>
            <div className="pipeline-stage-icon">{stage.icon}</div>
            <div className="pipeline-stage-title">{stage.title}</div>
            <div className="pipeline-stage-desc">{stage.desc}</div>
          </div>
          {i < stages.length - 1 && (
            <div className="pipeline-arrow"><ArrowSvg /></div>
          )}
        </div>
      ))}
    </div>
  )
}
