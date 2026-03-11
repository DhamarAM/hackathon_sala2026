import { useState, useEffect } from 'react'
import SpectrogramViewer from './SpectrogramViewer'
import AnalysisPanel from './AnalysisPanel'
import { loadFileAnnotation, getFileId } from '../utils'

export default function DetailModal({ ranking, onClose }) {
  const [cascade, setCascade] = useState(null)
  const [basic, setBasic] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ranking) return
    setLoading(true)
    loadFileAnnotation(ranking.filename)
      .then(({ basic: b, cascade: c }) => {
        setCascade(c)
        setBasic(b)
      })
      .finally(() => setLoading(false))
  }, [ranking])

  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  if (!ranking) return null

  const fileId = getFileId(ranking.filename)

  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal-content">
        <div className="modal-header">
          <h2>{ranking.filename}</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {loading ? (
          <div className="loading"><div className="spinner" /> Loading annotation data...</div>
        ) : (
          <div className="stack">
            <SpectrogramViewer fileId={fileId} duration={ranking.duration_s} cascade={cascade} />
            <AnalysisPanel ranking={ranking} cascade={cascade} basic={basic} />
          </div>
        )}
      </div>
    </div>
  )
}
