import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const REPO_ROOT = path.resolve(__dirname, '..')
const BACKEND_DIR = path.resolve(REPO_ROOT, 'backend')
const AUDIO_DIR = path.resolve(BACKEND_DIR, 'data/raw_data')
const OUTPUTS_DIR = path.resolve(REPO_ROOT, 'outputs')

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
        } else if (url.startsWith('/api/audio/')) {
          filePath = path.join(AUDIO_DIR, url.replace('/api/audio/', ''))
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
          res.end('Not found: ' + filePath)
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

export default defineConfig({
  plugins: [react(), serveDataPlugin()],
  server: {
    port: 3000,
    open: true,
    fs: {
      allow: [__dirname, BACKEND_DIR, OUTPUTS_DIR]
    }
  }
})
