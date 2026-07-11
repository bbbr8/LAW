import crypto from 'crypto'
import { buildAiFinding, reviewAiFinding } from './aiFinding.js'

function parseRows(rows) {
  return rows.map(row => JSON.parse(row.data))
}

function nowIso() {
  return new Date().toISOString()
}

async function upsertFinding(db, finding) {
  await db.run(
    `INSERT INTO ai_findings (id, caseId, currentStatus, data) VALUES (?, ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET currentStatus = excluded.currentStatus, data = excluded.data`,
    finding.id,
    finding.caseId,
    finding.currentStatus,
    JSON.stringify(finding),
  )
}

export function registerAiFindingRoutes(app, dbPromise) {
  app.get('/api/cases/:id/ai-findings', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM ai_findings WHERE caseId = ? ORDER BY json_extract(data,"$.createdAt") DESC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/ai-findings', async (req, res, next) => {
    try {
      const db = await dbPromise
      const atomRows = await db.all('SELECT data FROM evidence_atoms WHERE caseId = ?', req.params.id)
      const finding = buildAiFinding({
        id: req.body.id || `AIF-${crypto.randomUUID()}`,
        caseId: req.params.id,
        createdAt: nowIso(),
        ...req.body,
      }, parseRows(atomRows))
      await upsertFinding(db, finding)
      res.status(201).json(finding)
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.post('/api/cases/:id/ai-findings/:findingId/review', async (req, res, next) => {
    try {
      const db = await dbPromise
      const row = await db.get(
        'SELECT data FROM ai_findings WHERE caseId = ? AND id = ?',
        req.params.id,
        req.params.findingId,
      )
      if (!row) return res.status(404).json({ error: 'AI finding not found' })
      const updated = reviewAiFinding(JSON.parse(row.data), req.body)
      await upsertFinding(db, updated)
      res.json(updated)
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })
}
