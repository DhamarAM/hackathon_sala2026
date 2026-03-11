import { useState, useEffect, useRef } from 'react'
import SpectrogramViewer from '../components/SpectrogramViewer'
import AnalysisPanel from '../components/AnalysisPanel'
import { loadRankedData, loadCascadeResults, loadFileAnnotation, getFileId } from '../utils'

export default function SingleObservation() {
  const [mode, setMode] = useState('select') // 'select' | 'upload' | 'viewing'
  const [fileList, setFileList] = useState([])
  const [rankedMap, setRankedMap] = useState({})
  const [selectedFile, setSelectedFile] = useState(null)
  const [cascade, setCascade] = useState(null)
  const [basic, setBasic] = useState(null)
  const [ranking, setRanking] = useState(null)
  const [loading, setLoading] = useState(false)
  const [uploadedAudio, setUploadedAudio] = useState(null)
  const fileInputRef = useRef(null)

  // Load file list from ranked data
  useEffect(() => {
    Promise.all([loadRankedData(), loadCascadeResults()])
      .then(([ranked]) => {
        if (ranked?.rankings) {
          setFileList(ranked.rankings.map(r => r.filename))
          const map = {}
          ranked.rankings.forEach(r => { map[r.filename] = r })
          setRankedMap(map)
        }
      })
      .catch(() => {})
  }, [])

  const handleSelectFile = async (filename) => {
    setSelectedFile(filename)
    setLoading(true)
    setUploadedAudio(null)
    try {
      const { basic: b, cascade: c } = await loadFileAnnotation(filename)
      setCascade(c)
      setBasic(b)
      setRanking(rankedMap[filename] || null)
      setMode('viewing')
    } catch (err) {
      console.error('Failed to load file data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadedAudio(URL.createObjectURL(file))
    setSelectedFile(file.name)
    setCascade(null)
    setBasic(null)
    setRanking(null)
    setMode('viewing')
  }

  const handleBack = () => {
    setMode('select')
    setSelectedFile(null)
    setCascade(null)
    setBasic(null)
    setRanking(null)
    if (uploadedAudio) {
      URL.revokeObjectURL(uploadedAudio)
      setUploadedAudio(null)
    }
  }

  if (mode === 'viewing') {
    const fileId = selectedFile ? getFileId(selectedFile) : null
    return (
      <div className="stack">
        <div className="section-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn" onClick={handleBack}>&larr; Back</button>
            <h1 style={{ fontFamily: 'var(--font-mono)', fontSize: 18 }}>{selectedFile}</h1>
          </div>
        </div>

        {loading ? (
          <div className="loading"><div className="spinner" /> Loading analysis data...</div>
        ) : (
          <div className="grid-2" style={{ gridTemplateColumns: '1.5fr 1fr', alignItems: 'start' }}>
            <div className="stack">
              <SpectrogramViewer
                fileId={fileId}
                duration={ranking?.duration_s || cascade?.duration_s || basic?.duration_s}
                audioSrc={uploadedAudio}
                cascade={cascade}
              />
            </div>
            <div className="stack">
              <AnalysisPanel ranking={ranking} cascade={cascade} basic={basic} />
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="stack">
      <div className="section-header">
        <h1>Single Observation</h1>
      </div>

      {/* Upload Area */}
      <div
        className="upload-area"
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('active') }}
        onDragLeave={(e) => e.currentTarget.classList.remove('active')}
        onDrop={(e) => {
          e.preventDefault()
          e.currentTarget.classList.remove('active')
          const file = e.dataTransfer.files?.[0]
          if (file) {
            setUploadedAudio(URL.createObjectURL(file))
            setSelectedFile(file.name)
            setMode('viewing')
          }
        }}
      >
        <div className="upload-icon">{'\uD83C\uDF0A'}</div>
        <div className="upload-text">Drop an audio file here or click to upload</div>
        <div className="upload-hint">Supports WAV files from SoundTrap hydrophones</div>
        <input ref={fileInputRef} type="file" accept=".wav,audio/*" hidden onChange={handleUpload} />
      </div>

      {/* Or Select from Available Files */}
      {fileList.length > 0 && (
        <div className="card">
          <div className="card-title">Or Select from Analyzed Recordings</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, maxHeight: 300, overflowY: 'auto' }}>
            {fileList.map(f => {
              const r = rankedMap[f]
              return (
                <button
                  key={f}
                  className="btn"
                  style={{
                    fontSize: 12,
                    fontFamily: 'var(--font-mono)',
                    borderColor: r?.tier === 'CRITICAL' ? 'var(--tier-critical)' :
                                 r?.tier === 'HIGH' ? 'var(--tier-high)' : undefined,
                  }}
                  onClick={() => handleSelectFile(f)}
                >
                  {f.replace('.wav', '')}
                  {r && <span style={{
                    marginLeft: 6,
                    fontSize: 10,
                    color: `var(--tier-${r.tier.toLowerCase()})`,
                  }}>{r.score.toFixed(0)}</span>}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
