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
const AUDIO_DIR = path.resolve(BACKEND_DIR, 'data/raw_data')
const CLEAN_SPEC_DIR = path.resolve(BACKEND_DIR, 'output', 'spectrograms_clean')
const DOWNLOAD_SCRIPT = path.resolve(BACKEND_DIR, 'download_audio.py')

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
          // On-demand download trigger — returns status JSON
          const filename = url.replace('/api/audio/download/', '')
          handleAudioDownload(filename, res)
          return
        } else if (url.startsWith('/api/audio/status/')) {
          // Check if audio file exists locally
          const filename = url.replace('/api/audio/status/', '')
          const audioPath = path.join(AUDIO_DIR, filename)
          const exists = fs.existsSync(audioPath)
          const isDownloading = downloading.has(filename)
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.end(JSON.stringify({ exists, downloading: isDownloading }))
          return
        } else if (url.startsWith('/api/audio/')) {
          filePath = path.join(AUDIO_DIR, url.replace('/api/audio/', ''))
        } else if (url.startsWith('/api/clean-spectrogram/')) {
          filePath = path.join(CLEAN_SPEC_DIR, url.replace('/api/clean-spectrogram/', ''))
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

  const audioPath = path.join(AUDIO_DIR, filename)

  // Already downloaded
  if (fs.existsSync(audioPath)) {
    res.end(JSON.stringify({ status: 'ready', filename }))
    return
  }

  // Already being downloaded
  if (downloading.has(filename)) {
    res.end(JSON.stringify({ status: 'downloading', filename }))
    return
  }

  // Start download
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

export default defineConfig({
  plugins: [react(), serveDataPlugin()],
  server: {
    port: 3000,
    open: true,
    fs: {
      allow: [__dirname, BACKEND_DIR, OUTPUTS_DIR, AUDIO_DIR, CLEAN_SPEC_DIR]
    }
  }
})
