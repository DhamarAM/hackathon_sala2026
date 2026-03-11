import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { execSync } from 'child_process'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const REPO_ROOT = path.resolve(__dirname, '..')
const BACKEND_DIR = path.resolve(REPO_ROOT, 'backend')
const OUTPUTS_DIR = path.resolve(REPO_ROOT, 'outputs')
const SALA_ROOT = path.resolve(REPO_ROOT, '..', '..')           // SALA/
const AUDIO_DIR = path.resolve(SALA_ROOT, 'data', 'audio')      // SALA/data/audio/
const DOWNLOAD_SCRIPT = path.resolve(BACKEND_DIR, 'download_audio.py')
const GENERATE_SPEC_SCRIPT = path.resolve(BACKEND_DIR, 'utils', 'generate_spectrogram.py')

// Audio subdirectories (WAVs are organized by hydrophone unit)
const AUDIO_SUBDIRS = ['Music_Soundtrap_Pilot', '6478', '5783']

function findAudioFile(filename) {
  // Search all unit subdirectories for the WAV file
  for (const sub of AUDIO_SUBDIRS) {
    const p = path.join(AUDIO_DIR, sub, filename)
    if (fs.existsSync(p)) return p
  }
  // Fallback: check AUDIO_DIR root
  const root = path.join(AUDIO_DIR, filename)
  if (fs.existsSync(root)) return root
  return null
}

// Track in-progress downloads to avoid duplicate spawns
const downloading = new Set()

function serveDataPlugin() {
  return {
    name: 'serve-data-files',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = decodeURIComponent(req.url.split('?')[0])

        let filePath = null
        let contentType = 'application/octet-stream'

        if (url.startsWith('/api/pipeline/')) {
          filePath = path.join(OUTPUTS_DIR, url.replace('/api/pipeline/', ''))
        } else if (url.startsWith('/api/audio/download/')) {
          const filename = url.replace('/api/audio/download/', '')
          handleAudioDownload(filename, res)
          return
        } else if (url.startsWith('/api/audio/status/')) {
          const filename = url.replace('/api/audio/status/', '')
          const found = findAudioFile(filename)
          const isDownloading = downloading.has(filename)
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.end(JSON.stringify({ exists: !!found, downloading: isDownloading }))
          return
        } else if (url.startsWith('/api/audio/')) {
          const filename = url.replace('/api/audio/', '')
          filePath = findAudioFile(filename)
          if (!filePath) {
            res.statusCode = 404
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify({ error: 'not_found', path: url }))
            return
          }
        } else if (url.startsWith('/api/clean-spectrogram/')) {
          // On-the-fly clean spectrogram generation
          const filename = url.replace('/api/clean-spectrogram/', '')
          handleCleanSpectrogram(filename, res)
          return
        } else if (url.startsWith('/api/spectrogram/generate/')) {
          // On-the-fly full spectrogram generation
          const filename = url.replace('/api/spectrogram/generate/', '')
          handleGenerateSpectrogram(filename, 'full', res)
          return
        } else if (url.startsWith('/api/spectrogram/bands/')) {
          // On-the-fly band spectrogram generation
          const filename = url.replace('/api/spectrogram/bands/', '')
          handleGenerateSpectrogram(filename, 'bands', res)
          return
        } else {
          return next()
        }

        if (filePath.endsWith('.json')) contentType = 'application/json'
        else if (filePath.endsWith('.png')) contentType = 'image/png'
        else if (filePath.endsWith('.jpg') || filePath.endsWith('.jpeg')) contentType = 'image/jpeg'
        else if (filePath.endsWith('.wav')) contentType = 'audio/wav'
        else if (filePath.endsWith('.csv')) contentType = 'text/csv'

        if (!fs.existsSync(filePath)) {
          res.statusCode = 404
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'not_found', path: url }))
          return
        }

        const stat = fs.statSync(filePath)
        res.setHeader('Content-Type', contentType)
        res.setHeader('Access-Control-Allow-Origin', '*')
        res.setHeader('Accept-Ranges', 'bytes')

        // Handle range requests (required for audio seeking in browsers)
        const range = req.headers.range
        if (range) {
          const parts = range.replace(/bytes=/, '').split('-')
          const start = parseInt(parts[0], 10)
          const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1
          const chunkSize = end - start + 1
          res.statusCode = 206
          res.setHeader('Content-Range', `bytes ${start}-${end}/${stat.size}`)
          res.setHeader('Content-Length', chunkSize)
          fs.createReadStream(filePath, { start, end }).pipe(res)
          return
        }

        res.setHeader('Content-Length', stat.size)
        fs.createReadStream(filePath).pipe(res)
      })
    }
  }
}

function handleAudioDownload(filename, res) {
  res.setHeader('Content-Type', 'application/json')
  res.setHeader('Access-Control-Allow-Origin', '*')

  const found = findAudioFile(filename)
  if (found) {
    res.end(JSON.stringify({ status: 'ready', filename }))
    return
  }

  if (downloading.has(filename)) {
    res.end(JSON.stringify({ status: 'downloading', filename }))
    return
  }

  downloading.add(filename)
  try {
    execSync(`python "${DOWNLOAD_SCRIPT}" "${filename}"`, {
      cwd: BACKEND_DIR,
      timeout: 120000,
      stdio: 'pipe',
    })
    downloading.delete(filename)
    res.end(JSON.stringify({ status: 'ready', filename }))
  } catch (e) {
    downloading.delete(filename)
    res.statusCode = 500
    res.end(JSON.stringify({ status: 'error', filename, error: e.stderr?.toString() || e.message }))
  }
}

function handleCleanSpectrogram(filename, res) {
  // First check if a pre-generated version exists in outputs
  const preGenerated = path.join(OUTPUTS_DIR, 'analysis', 'spectrograms', filename)
  if (fs.existsSync(preGenerated)) {
    res.setHeader('Content-Type', 'image/png')
    res.setHeader('Access-Control-Allow-Origin', '*')
    const stat = fs.statSync(preGenerated)
    res.setHeader('Content-Length', stat.size)
    fs.createReadStream(preGenerated).pipe(res)
    return
  }

  // Generate on-the-fly from WAV
  const wavFilename = filename
    .replace(/_cascade_clean\.png$/, '.wav')
    .replace(/_spectrogram_clean\.png$/, '.wav')
    .replace(/_clean\.png$/, '.wav')
  const wavPath = findAudioFile(wavFilename)

  if (!wavPath) {
    res.statusCode = 404
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({ error: 'audio_not_found', filename: wavFilename }))
    return
  }

  handleGenerateSpectrogram(wavPath, 'clean', res)
}

function handleGenerateSpectrogram(wavPathOrName, mode, res) {
  // Accept either a resolved path or a filename to search for
  const wavPath = fs.existsSync(wavPathOrName) ? wavPathOrName : findAudioFile(wavPathOrName)

  if (!wavPath) {
    res.statusCode = 404
    res.setHeader('Content-Type', 'application/json')
    res.setHeader('Access-Control-Allow-Origin', '*')
    res.end(JSON.stringify({ error: 'audio_not_found', filename: wavPathOrName }))
    return
  }

  try {
    const result = execSync(
      `python "${GENERATE_SPEC_SCRIPT}" "${wavPath}" --mode ${mode}`,
      { cwd: BACKEND_DIR, timeout: 60000, stdio: 'pipe', maxBuffer: 10 * 1024 * 1024 }
    )
    res.setHeader('Content-Type', 'image/png')
    res.setHeader('Access-Control-Allow-Origin', '*')
    res.setHeader('Content-Length', result.length)
    res.end(result)
  } catch (e) {
    res.statusCode = 500
    res.setHeader('Content-Type', 'application/json')
    res.setHeader('Access-Control-Allow-Origin', '*')
    res.end(JSON.stringify({
      error: 'generation_failed',
      filename: wavPath,
      detail: e.stderr?.toString() || e.message,
    }))
  }
}

export default defineConfig({
  plugins: [react(), serveDataPlugin()],
  server: {
    port: 3000,
    open: true,
    fs: {
      allow: [__dirname, BACKEND_DIR, OUTPUTS_DIR, AUDIO_DIR]
    }
  }
})
