import crypto from 'crypto'
import {
  buildResolutionEvent,
  findResolutionCandidates,
  propagateResolutionEvent,
} from './proofDebtResolver.js'

function parseRows(rows) {
  return rows.map(row => JSON.parse(row.data))
}

function recordId(prefix, suppliedId) {
  return suppliedId || `${prefix}-${crypto.randomUUID()}`
}

function nowIso() {
  return new Date().toISOString()
}

async function insertJson(db, table, record, extraColumns = {}) {
  const columns = ['id', ...Object.keys(extraColumns), 'data']
  const placeholders = columns.map(() => '?').join(', ')
  const values = [record.id, ...Object.values(extraColumns), JSON.stringify(record)]
  await db.run(
    `INSERT INTO ${table} (${columns.join(', ')}) VALUES (${placeholders})`,
    ...values,
  )
}

async function upsertJson(db, table, record, extraColumns = {}) {
  const columns = ['id', ...Object.keys(extraColumns), 'data']
  const placeholders = columns.map(() => '?').join(', ')
  const updates = [...Object.keys(extraColumns), 'data']
    .map(column => `${column} = excluded.${column}`)
    .join(', ')
  const values = [record.id, ...Object.values(extraColumns), JSON.stringify(record)]
  await db.run(
    `INSERT INTO ${table} (${columns.join(', ')}) VALUES (${placeholders})
     ON CONFLICT(id) DO UPDATE SET ${updates}`,
    ...values,
  )
}

export function registerProofDebtRoutes(app, dbPromise) {
  app.get('/api/cases/:id/proof-debts', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM proof_debts WHERE caseId = ? ORDER BY json_extract(data,"$.priority") ASC, id ASC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/proof-debts', async (req, res, next) => {
    try {
      if (!req.body.canonicalRecordNeed) {
        return res.status(400).json({ error: 'canonicalRecordNeed is required' })
      }

      const db = await dbPromise
      const createdAt = nowIso()
      const debt = {
        id: recordId('PDR', req.body.id),
        caseId: req.params.id,
        createdAt,
        updatedAt: createdAt,
        priority: 3,
        sourceStatus: 'bridge_missing',
        resolutionStatus: 'Open',
        candidateHits: 0,
        ...req.body,
      }
      await insertJson(db, 'proof_debts', debt, { caseId: req.params.id })
      res.status(201).json(debt)
    } catch (error) {
      next(error)
    }
  })

  app.patch('/api/cases/:id/proof-debts/:debtId', async (req, res, next) => {
    try {
      const db = await dbPromise
      const row = await db.get(
        'SELECT data FROM proof_debts WHERE caseId = ? AND id = ?',
        req.params.id,
        req.params.debtId,
      )
      if (!row) return res.status(404).json({ error: 'Proof debt not found' })

      const existing = JSON.parse(row.data)
      const updated = {
        ...existing,
        ...req.body,
        id: existing.id,
        caseId: existing.caseId,
        updatedAt: nowIso(),
      }
      await upsertJson(db, 'proof_debts', updated, { caseId: req.params.id })
      res.json(updated)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/search-runs', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM search_runs WHERE caseId = ? ORDER BY json_extract(data,"$.createdAt") DESC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/search-runs', async (req, res, next) => {
    try {
      if (!req.body.preSearchContextVersion) {
        return res.status(400).json({ error: 'preSearchContextVersion is required' })
      }
      if (!Array.isArray(req.body.lanesLoaded) || req.body.lanesLoaded.length === 0) {
        return res.status(400).json({ error: 'lanesLoaded must contain at least one lane' })
      }

      const db = await dbPromise
      const searchRun = {
        id: recordId('SR', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        completenessLabel: 'PARTIAL — NOT WHOLE-CASE',
        ...req.body,
      }
      await insertJson(db, 'search_runs', searchRun, { caseId: req.params.id })
      res.status(201).json(searchRun)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/dependencies', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM dependency_edges WHERE caseId = ? ORDER BY id ASC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/dependencies', async (req, res, next) => {
    try {
      if (!req.body.fromId || !req.body.toId || !req.body.relation) {
        return res.status(400).json({ error: 'fromId, toId, and relation are required' })
      }

      const db = await dbPromise
      const edge = {
        id: recordId('DG', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        ...req.body,
      }
      await insertJson(db, 'dependency_edges', edge, {
        caseId: req.params.id,
        fromId: edge.fromId,
        toId: edge.toId,
      })
      res.status(201).json(edge)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/resolution-events', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM resolution_events WHERE caseId = ? ORDER BY json_extract(data,"$.createdAt") DESC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/evidence-sources', async (req, res, next) => {
    try {
      const db = await dbPromise
      const evidence = {
        id: recordId('SRC', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        ...req.body,
      }

      await insertJson(db, 'evidence_sources', evidence, { caseId: req.params.id })

      const debtRows = await db.all(
        'SELECT data FROM proof_debts WHERE caseId = ?',
        req.params.id,
      )
      const dependencyRows = await db.all(
        'SELECT data FROM dependency_edges WHERE caseId = ?',
        req.params.id,
      )
      const debts = parseRows(debtRows)
      const dependencies = parseRows(dependencyRows)
      const candidates = findResolutionCandidates(debts, evidence, { minimumScore: 40 })
      const debtById = new Map(debts.map(debt => [debt.id, debt]))
      const events = []
      const propagations = []

      await db.exec('BEGIN')
      try {
        for (const candidate of candidates) {
          const debt = debtById.get(candidate.debtId)
          if (!debt) continue

          const event = {
            ...buildResolutionEvent(debt, evidence, candidate, evidence.searchRunId),
            caseId: req.params.id,
          }
          await insertJson(db, 'resolution_events', event, {
            caseId: req.params.id,
            debtId: debt.id,
            evidenceId: evidence.id,
          })
          events.push(event)

          const updatedDebt = {
            ...debt,
            candidateHits: Number(debt.candidateHits || 0) + 1,
            resolutionStatus:
              candidate.score >= 60 && debt.resolutionStatus !== 'Resolved'
                ? 'Candidate Review'
                : debt.resolutionStatus,
            lastChecked: nowIso(),
            latestCandidate: {
              evidenceId: evidence.id,
              score: candidate.score,
              threshold: candidate.threshold,
              nativeLocator: evidence.nativeLocator ?? null,
            },
            updatedAt: nowIso(),
          }
          await upsertJson(db, 'proof_debts', updatedDebt, { caseId: req.params.id })

          propagations.push(...propagateResolutionEvent(event, dependencies))
        }
        await db.exec('COMMIT')
      } catch (error) {
        await db.exec('ROLLBACK')
        throw error
      }

      res.status(201).json({
        evidence,
        candidates,
        resolutionEvents: events,
        propagations,
        autoResolved: false,
        guardrail: 'Native/source validation and human review are required before closure.',
      })
    } catch (error) {
      next(error)
    }
  })
}
