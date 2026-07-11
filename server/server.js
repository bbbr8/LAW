import express from 'express'
import cors from 'cors'
import multer from 'multer'
import crypto from 'crypto'
import fs from 'fs'
import { initDb } from './db.js'
import { hybridSearch } from './ai-search/hybrid-search.js'

const upload = multer({ dest: 'server/upload-dir' })
const app = express()
app.use(cors())
app.use(express.json({ limit: '5mb' }))

const PORT = 3001
const dbPromise = initDb()

app.get('/api/cases', async (req, res) => {
  const db = await dbPromise
  const rows = await db.all(`SELECT data FROM cases ORDER BY json_extract(data,'$.createdAt') DESC`)
  res.json(rows.map(r => JSON.parse(r.data)))
})

app.post('/api/cases', async (req, res) => {
  const db = await dbPromise
  const id = crypto.randomUUID()
  const createdAt = new Date().toISOString()
  const caseObj = { id, createdAt, ...req.body }
  await db.run('INSERT INTO cases (id, data) VALUES (?, ?)', id, JSON.stringify(caseObj))
  res.json(caseObj)
})

app.get('/api/cases/:id/messages', async (req, res) => {
  const db = await dbPromise
  const rows = await db.all('SELECT data FROM messages WHERE caseId = ? ORDER BY json_extract(data,"$.at") ASC', req.params.id)
  res.json(rows.map(r => JSON.parse(r.data)))
})

app.post('/api/cases/:id/messages', async (req, res) => {
  const db = await dbPromise
  const id = crypto.randomUUID()
  const at = new Date().toISOString()
  const message = { id, caseId: req.params.id, at, ...req.body }
  await db.run('INSERT INTO messages (id, caseId, data) VALUES (?, ?, ?)', id, req.params.id, JSON.stringify(message))
  res.json(message)
})

app.get('/api/cases/:id/tasks', async (req, res) => {
  const db = await dbPromise
  const rows = await db.all('SELECT data FROM tasks WHERE caseId = ? ORDER BY json_extract(data,"$.dueAt") ASC', req.params.id)
  res.json(rows.map(r => JSON.parse(r.data)))
})

app.post('/api/cases/:id/tasks', async (req, res) => {
  const db = await dbPromise
  const id = crypto.randomUUID()
  const task = { id, caseId: req.params.id, ...req.body }
  await db.run('INSERT INTO tasks (id, caseId, data) VALUES (?, ?, ?)', id, req.params.id, JSON.stringify(task))
  res.json(task)
})

app.post('/api/scan-upload', upload.single('file'), async (req, res) => {
  const file = req.file
  if (!file) return res.status(400).json({ error: 'file is required' })

  try {
    const buffer = await fs.promises.readFile(file.path)
    const sha256 = crypto.createHash('sha256').update(buffer).digest('hex')
    return res.json({ safe: true, name: file.originalname, size: file.size, mime: file.mimetype, sha256 })
  } finally {
    await fs.promises.unlink(file.path).catch(() => {})
  }
})

app.post('/api/ai-search', async (req, res) => {
  try {
    const result = await hybridSearch(req.body || {})
    res.json(result)
  } catch (error) {
    const status = error instanceof TypeError || error instanceof RangeError ? 400 : 500
    res.status(status).json({ error: error.message || 'AI search failed' })
  }
})

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`))
