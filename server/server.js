import express from 'express'
import cors from 'cors'
import multer from 'multer'
import crypto from 'crypto'
import fs from 'fs'
import { initDb } from './db.js'
import { hybridSearch } from './ai-search/hybrid-search.js'
import { registerAdvancedRoutes } from './advancedRoutes.js'
import { registerProofDebtRoutes } from './proofDebtRoutes.js'
import { registerAiFindingRoutes } from './aiFindingRoutes.js'
import { registerConnectorRoutes } from './connectorRoutes.js'

const upload = multer({ dest: 'server/upload-dir' })
const app = express()
app.use(cors())
app.use(express.json({ limit: '10mb' }))

const PORT = 3001
const dbPromise = initDb()
registerProofDebtRoutes(app, dbPromise)
registerAdvancedRoutes(app, dbPromise)
registerAiFindingRoutes(app, dbPromise)
registerConnectorRoutes(app, dbPromise)

app.get('/api/cases', async (req, res, next) => {
  try {
    const db = await dbPromise
    const rows = await db.all(`SELECT data FROM cases ORDER BY json_extract(data,'$.createdAt') DESC`)
    res.json(rows.map(row => JSON.parse(row.data)))
  } catch (error) {
    next(error)
  }
})

app.post('/api/cases', async (req, res, next) => {
  try {
    const db = await dbPromise
    const id = crypto.randomUUID()
    const createdAt = new Date().toISOString()
    const caseObj = { id, createdAt, ...req.body }
    await db.run('INSERT INTO cases (id, data) VALUES (?, ?)', id, JSON.stringify(caseObj))
    res.json(caseObj)
  } catch (error) {
    next(error)
  }
})

app.get('/api/cases/:id/messages', async (req, res, next) => {
  try {
    const db = await dbPromise
    const rows = await db.all(
      'SELECT data FROM messages WHERE caseId = ? ORDER BY json_extract(data,"$.at") ASC',
      req.params.id,
    )
    res.json(rows.map(row => JSON.parse(row.data)))
  } catch (error) {
    next(error)
  }
})

app.post('/api/cases/:id/messages', async (req, res, next) => {
  try {
    const db = await dbPromise
    const id = crypto.randomUUID()
    const at = new Date().toISOString()
    const message = { id, caseId: req.params.id, at, ...req.body }
    await db.run(
      'INSERT INTO messages (id, caseId, data) VALUES (?, ?, ?)',
      id,
      req.params.id,
      JSON.stringify(message),
    )
    res.json(message)
  } catch (error) {
    next(error)
  }
})

app.get('/api/cases/:id/tasks', async (req, res, next) => {
  try {
    const db = await dbPromise
    const rows = await db.all(
      'SELECT data FROM tasks WHERE caseId = ? ORDER BY json_extract(data,"$.dueAt") ASC',
      req.params.id,
    )
    res.json(rows.map(row => JSON.parse(row.data)))
  } catch (error) {
    next(error)
  }
})

app.post('/api/cases/:id/tasks', async (req, res, next) => {
  try {
    const db = await dbPromise
    const id = crypto.randomUUID()
    const task = { id, caseId: req.params.id, ...req.body }
    await db.run(
      'INSERT INTO tasks (id, caseId, data) VALUES (?, ?, ?)',
      id,
      req.params.id,
      JSON.stringify(task),
    )
    res.json(task)
  } catch (error) {
    next(error)
  }
})

app.post('/api/scan-upload', upload.single('file'), async (req, res, next) => {
  const file = req.file
  if (!file) return res.status(400).json({ error: 'file is required' })

  try {
    const buffer = await fs.promises.readFile(file.path)
    const sha256 = crypto.createHash('sha256').update(buffer).digest('hex')
    res.json({ safe: true, name: file.originalname, size: file.size, mime: file.mimetype, sha256 })
  } catch (error) {
    next(error)
  } finally {
    await fs.promises.unlink(file.path).catch(() => {})
  }
})

app.post('/api/ai-search', async (req, res, next) => {
  try {
    const result = await hybridSearch(req.body || {})
    res.json(result)
  } catch (error) {
    if (error instanceof TypeError || error instanceof RangeError) {
      return res.status(400).json({ error: error.message || 'Invalid AI search request' })
    }
    next(error)
  }
})

app.use((error, req, res, next) => {
  console.error(error)
  if (res.headersSent) return next(error)
  res.status(500).json({ error: 'Internal server error' })
})

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`))
