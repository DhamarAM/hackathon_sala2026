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
      title: 'Audio Analysis',
      desc: 'Band decomposition, transient detection, spectrogram generation',
    },
    {
      icon: <IconSearch size={24} />,
      title: 'YAMNet (Stage 1)',
      desc: '521-class general audio, bio signal gating',
    },
    {
      icon: <IconWhale size={24} />,
      title: 'Whale Classifiers',
      desc: 'Multispecies (12 classes) + Humpback (binary per 1s window)',
    },
    {
      icon: <IconRanking size={24} />,
      title: 'Bio Importance Ranking',
      desc: '7-dimension weighted scoring, 5 priority tiers',
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
