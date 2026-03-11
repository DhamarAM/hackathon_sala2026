import { useRef, useState, useEffect, useCallback } from 'react'
import { API } from '../config'
import { IconVolumeHigh, IconVolumeMute } from './Icons'

export default function SpectrogramViewer({ fileId, duration, audioSrc, cascade, sampleRate = 48000 }) {
  const [spectroType, setSpectroType] = useState('cascade')
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [audioDuration, setAudioDuration] = useState(duration || 0)
  const [volume, setVolume] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [panX, setPanX] = useState(0)
  const [hoverInfo, setHoverInfo] = useState(null)
  const [audioError, setAudioError] = useState(false)
  const audioRef = useRef(null)
  const viewportRef = useRef(null)
  const imgRef = useRef(null)
  const animRef = useRef(null)
  const dragRef = useRef({ dragging: false, startX: 0, startPan: 0 })

  const spectroSrc = spectroType === 'cascade'
    ? API.cascadeSpectrogram(`${fileId}_cascade.png`)
    : API.spectrogram(`${fileId}_spectrogram.png`)

  const actualAudioSrc = audioSrc || API.audio(`${fileId}.wav`)

  useEffect(() => {
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current) }
  }, [])

  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = volume
  }, [volume])

  // Reset zoom on spectrogram type change
  useEffect(() => { setZoom(1); setPanX(0) }, [spectroType])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      switch (e.key) {
        case ' ':
          e.preventDefault()
          togglePlay()
          break
        case 'ArrowLeft':
          e.preventDefault()
          if (audioRef.current && audioDuration > 0) {
            audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 5)
            setCurrentTime(audioRef.current.currentTime)
          }
          break
        case 'ArrowRight':
          e.preventDefault()
          if (audioRef.current && audioDuration > 0) {
            audioRef.current.currentTime = Math.min(audioDuration, audioRef.current.currentTime + 5)
            setCurrentTime(audioRef.current.currentTime)
          }
          break
        case '+': case '=':
          setZoom(z => Math.min(5, z + 0.5))
          break
        case '-':
          setZoom(z => { const next = Math.max(1, z - 0.5); if (next === 1) setPanX(0); return next })
          break
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [audioDuration, audioError, isPlaying])

  const updateTime = useCallback(() => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime)
      if (!audioRef.current.paused) {
        animRef.current = requestAnimationFrame(updateTime)
      }
    }
  }, [])

  const togglePlay = () => {
    if (!audioRef.current || audioError) return
    if (audioRef.current.paused) {
      audioRef.current.play().catch(() => setAudioError(true))
      setIsPlaying(true)
      animRef.current = requestAnimationFrame(updateTime)
    } else {
      audioRef.current.pause()
      setIsPlaying(false)
      if (animRef.current) cancelAnimationFrame(animRef.current)
    }
  }

  const seekTo = (ratio) => {
    if (!audioRef.current || !audioDuration) return
    audioRef.current.currentTime = Math.max(0, Math.min(1, ratio)) * audioDuration
    setCurrentTime(audioRef.current.currentTime)
  }

  const handleTimelineClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    seekTo((e.clientX - rect.left) / rect.width)
  }

  const handleViewportClick = (e) => {
    if (dragRef.current.didDrag) return
    if (!viewportRef.current || !audioDuration) return
    const rect = viewportRef.current.getBoundingClientRect()
    const xInViewport = e.clientX - rect.left
    const imgDisplayWidth = rect.width * zoom
    const xInImage = (xInViewport + (-panX)) / imgDisplayWidth
    seekTo(xInImage)
  }

  // Zoom with wheel
  const handleWheel = (e) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.2 : 0.2
    setZoom(z => {
      const next = Math.max(1, Math.min(5, z + delta))
      if (next === 1) setPanX(0)
      return next
    })
  }

  // Pan with drag
  const handleMouseDown = (e) => {
    if (zoom <= 1) return
    dragRef.current = { dragging: true, startX: e.clientX, startPan: panX, didDrag: false }
  }
  const handleMouseMove = (e) => {
    if (!dragRef.current.dragging) return
    const dx = e.clientX - dragRef.current.startX
    if (Math.abs(dx) > 3) dragRef.current.didDrag = true
    if (!viewportRef.current) return
    const vw = viewportRef.current.offsetWidth
    const maxPan = vw * (zoom - 1)
    setPanX(Math.max(-maxPan, Math.min(0, dragRef.current.startPan + dx)))
  }
  const handleMouseUp = () => { dragRef.current.dragging = false }

  // Hover info
  const handleImgHover = (e) => {
    if (!viewportRef.current || !audioDuration) return
    const rect = viewportRef.current.getBoundingClientRect()
    const xInViewport = e.clientX - rect.left
    const imgDisplayWidth = rect.width * zoom
    const xRatio = (xInViewport + (-panX)) / imgDisplayWidth
    const time = xRatio * audioDuration
    const yRatio = (e.clientY - rect.top) / rect.height
    const nyquist = sampleRate / 2
    const freqHz = Math.round((1 - yRatio) * nyquist)
    setHoverInfo({
      time: `${Math.floor(time / 60)}:${Math.floor(time % 60).toString().padStart(2, '0')}`,
      freq: freqHz >= 1000 ? `${(freqHz / 1000).toFixed(1)} kHz` : `${freqHz} Hz`,
    })
  }

  const progress = audioDuration > 0 ? (currentTime / audioDuration) * 100 : 0

  // Compute playhead position accounting for zoom and pan
  const playheadLeft = (() => {
    if (!viewportRef.current || audioDuration <= 0) return -10
    const vw = viewportRef.current?.offsetWidth || 0
    return (progress / 100) * vw * zoom + panX
  })()

  const formatTime = (s) => {
    if (!s || isNaN(s)) return '0:00'
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  // Build event markers from cascade data
  const eventMarkers = []
  if (cascade && audioDuration > 0) {
    // Multispecies time series → markers where score > 0.02
    const ts2 = cascade.stage2_multispecies?.top_time_series
    if (ts2) {
      ts2.forEach((score, i) => {
        if (score > 0.02) {
          eventMarkers.push({
            position: ((i + 0.5) / ts2.length) * 100,
            color: 'var(--teal)',
            label: `${cascade.stage2_multispecies.top_species || 'Whale'}: ${(score * 100).toFixed(1)}%`,
          })
        }
      })
    }
    // Humpback time series → markers where score > 0.03
    const ts3 = cascade.stage3_humpback?.time_series
    if (ts3) {
      ts3.forEach((score, i) => {
        if (score > 0.03) {
          eventMarkers.push({
            position: ((i + 0.5) / ts3.length) * 100,
            color: 'var(--accent)',
            label: `Humpback: ${(score * 100).toFixed(1)}%`,
          })
        }
      })
    }
    // YAMNet bio detections
    if (cascade.stage1_yamnet?.has_bio_signal) {
      cascade.stage1_yamnet.bio_detections?.forEach(d => {
        if (d.score > 0.1) {
          eventMarkers.push({
            position: 50,
            color: 'var(--green)',
            label: `YAMNet: ${d.class} (${(d.score * 100).toFixed(0)}%)`,
          })
        }
      })
    }
  }

  return (
    <div className="stack">
      {/* Spectrogram Type Tabs */}
      <div className="tabs" style={{ maxWidth: 300 }}>
        <button className={`tab ${spectroType === 'cascade' ? 'active' : ''}`} onClick={() => setSpectroType('cascade')}>
          Cascade (4-panel)
        </button>
        <button className={`tab ${spectroType === 'basic' ? 'active' : ''}`} onClick={() => setSpectroType('basic')}>
          Basic (2-panel)
        </button>
      </div>

      {/* Spectrogram Image with Zoom/Pan/Playhead */}
      <div className="spectrogram-container">
        {hoverInfo && (
          <div className="spectrogram-hover-info">
            {hoverInfo.time} &middot; {hoverInfo.freq}
          </div>
        )}
        <div
          ref={viewportRef}
          className="spectrogram-viewport"
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={(e) => { handleMouseMove(e); handleImgHover(e) }}
          onMouseUp={handleMouseUp}
          onMouseLeave={() => { handleMouseUp(); setHoverInfo(null) }}
          onClick={handleViewportClick}
        >
          <img
            ref={imgRef}
            src={spectroSrc}
            alt={`${spectroType} spectrogram for ${fileId}`}
            style={{ width: `${zoom * 100}%`, transform: `translateX(${panX}px)` }}
            onError={(e) => { e.target.style.opacity = 0.3 }}
            draggable={false}
          />
          {audioDuration > 0 && playheadLeft >= 0 && (
            <div className="spectrogram-playhead" style={{ left: `${playheadLeft}px` }} />
          )}
        </div>
        <div className="spectrogram-zoom-controls">
          <button onClick={() => { setZoom(1); setPanX(0) }} title="Reset zoom">1x</button>
          <button onClick={() => setZoom(z => Math.max(1, z - 0.5))} title="Zoom out">&minus;</button>
          <button onClick={() => setZoom(z => Math.min(5, z + 0.5))} title="Zoom in">+</button>
        </div>
      </div>

      {/* Audio Element */}
      <audio
        ref={audioRef}
        src={actualAudioSrc}
        preload="auto"
        onLoadedMetadata={() => {
          if (audioRef.current) {
            setAudioDuration(audioRef.current.duration)
            setAudioError(false)
          }
        }}
        onError={() => setAudioError(true)}
        onEnded={() => {
          setIsPlaying(false)
          if (animRef.current) cancelAnimationFrame(animRef.current)
        }}
      />

      {/* Audio Controls */}
      <div className="audio-player">
        <button className="play-btn" onClick={togglePlay} title={audioError ? 'Audio not available' : isPlaying ? 'Pause' : 'Play'}>
          {audioError ? '!' : isPlaying ? '\u275A\u275A' : '\u25B6'}
        </button>
        <div className="timeline" onClick={handleTimelineClick}>
          <div className="timeline-progress" style={{ width: `${progress}%` }} />
        </div>
        <div className="time-display">
          {formatTime(currentTime)} / {formatTime(audioDuration)}
        </div>
        <div className="volume-control">
          <span style={{ color: 'var(--text-tertiary)' }}>{volume > 0 ? <IconVolumeHigh size={16} /> : <IconVolumeMute size={16} />}</span>
          <input
            type="range"
            className="volume-slider"
            min="0"
            max="1"
            step="0.05"
            value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
          />
        </div>
      </div>

      {/* Event Timeline with markers */}
      <div className="event-timeline" onClick={handleTimelineClick}>
        <span className="event-timeline-label">Events</span>
        {eventMarkers.map((m, i) => (
          <div
            key={i}
            className="event-marker"
            style={{ left: `${m.position}%`, background: m.color }}
            onClick={(e) => {
              e.stopPropagation()
              seekTo(m.position / 100)
            }}
          >
            <div className="event-marker-tooltip">{m.label}</div>
          </div>
        ))}
        {audioDuration > 0 && (
          <div style={{
            position: 'absolute', top: 0, bottom: 0, width: 2,
            background: 'var(--tier-critical)',
            left: `${progress}%`,
            pointerEvents: 'none',
            zIndex: 3,
          }} />
        )}
      </div>
      {audioError && (
        <div style={{ fontSize: 12, color: 'var(--tier-moderate)', textAlign: 'center' }}>
          Audio file not available for this recording. Only one sample file (190806_3754.wav) is in the dataset.
        </div>
      )}
    </div>
  )
}
