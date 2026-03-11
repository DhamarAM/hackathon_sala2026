export default function PipelineDiagram() {
  const stages = [
    {
      icon: '\uD83C\uDF0A',
      title: 'SoundTrap Collection',
      desc: 'Hydrophone recordings from the Galapagos Marine Reserve',
    },
    {
      icon: '\u2702\uFE0F',
      title: 'Audio Segmentation',
      desc: 'Silence removal and active-segment extraction (Stage 0)',
    },
    {
      icon: '\uD83E\uDDE0',
      title: 'AI Cascade Classifier',
      desc: 'YAMNet \u2192 Multispecies Whale \u2192 Humpback Detector (Stages 1\u20133)',
    },
    {
      icon: '\uD83C\uDF3F',
      title: 'Soundscape & Clustering',
      desc: 'NDSI acoustic indices + UMAP/HDBSCAN embedding clusters (Stages 5\u20136)',
    },
    {
      icon: '\uD83D\uDCCA',
      title: 'Ranking & Report',
      desc: '9-dimension biological importance scoring with 5-tier classification (Stage 4)',
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
