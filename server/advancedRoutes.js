import crypto from 'crypto'
import { buildExactRoutePlan, normalizeExactKey } from './exactIndexRouter.js'
import {
  applyHumanReview,
  createAuditChainEvent,
  findConclusionInvalidations,
  traceConclusion,
  validateEvidenceAtom,
} from './sourceLineage.js'

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

export function registerAdvancedRoutes(app, dbPromise) {
  app.post('/api/cases/:id/route-query', async (req, res, next) => {
    try {
      if (!req.body.query) return res.status(400).json({ error: 'query is required' })
      const db = await dbPromise
      const debtRows = await db.all(
        `SELECT data FROM proof_debts
         WHERE caseId = ? AND lower(json_extract(data, '$.resolutionStatus')) != 'resolved'`,
        req.params.id,
      )
      const contextRow = await db.get(
        `SELECT data FROM context_versions
         WHERE caseId = ? AND lower(COALESCE(status, 'active')) = 'active'
         ORDER BY json_extract(data, '$.effectiveDate') DESC LIMIT 1`,
        req.params.id,
      )
      const debts = parseRows(debtRows)
      const plan = buildExactRoutePlan(req.body.query, {
        aliasTerms: req.body.aliasTerms,
        identityFirewalls: req.body.identityFirewalls,
        openDebtTerms: debts.flatMap(debt => [
          debt.id,
          ...(Array.isArray(debt.aliases) ? debt.aliases : []),
          ...(Array.isArray(debt.triggerTerms) ? debt.triggerTerms : []),
        ]),
      })

      res.json({
        contextVersion: contextRow ? JSON.parse(contextRow.data) : null,
        openDebtCount: debts.length,
        ...plan,
      })
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/exact-index-entries', async (req, res, next) => {
    try {
      if (!req.body.indexType || req.body.rawKey === undefined) {
        return res.status(400).json({ error: 'indexType and rawKey are required' })
      }
      const normalizedKey = normalizeExactKey(req.body.indexType, req.body.rawKey)
      if (!normalizedKey) return res.status(400).json({ error: 'rawKey could not be normalized' })

      const db = await dbPromise
      const entry = {
        id: recordId('IDX', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        ...req.body,
        normalizedKey,
      }
      await insertJson(db, 'exact_index_entries', entry, {
        caseId: req.params.id,
        indexType: entry.indexType,
        normalizedKey,
      })
      res.status(201).json(entry)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/exact-index-entries', async (req, res, next) => {
    try {
      const db = await dbPromise
      const clauses = ['caseId = ?']
      const params = [req.params.id]
      if (req.query.type) {
        clauses.push('indexType = ?')
        params.push(String(req.query.type))
      }
      if (req.query.key !== undefined) {
        const type = String(req.query.type || 'identifier')
        clauses.push('normalizedKey = ?')
        params.push(normalizeExactKey(type, req.query.key))
      }
      const rows = await db.all(
        `SELECT data FROM exact_index_entries WHERE ${clauses.join(' AND ')} ORDER BY id ASC`,
        ...params,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/evidence-atoms', async (req, res, next) => {
    try {
      const atom = {
        id: recordId('ATOM', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        atomStatus: 'Active',
        ...req.body,
      }
      const validation = validateEvidenceAtom(atom)
      if (!validation.valid) return res.status(400).json({ error: validation.errors })

      const db = await dbPromise
      await insertJson(db, 'evidence_atoms', atom, {
        caseId: req.params.id,
        sourceId: atom.sourceId,
      })
      res.status(201).json(atom)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/evidence-atoms', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM evidence_atoms WHERE caseId = ? ORDER BY id ASC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/conclusions', async (req, res, next) => {
    try {
      if (!req.body.conclusionText) {
        return res.status(400).json({ error: 'conclusionText is required' })
      }
      const db = await dbPromise
      const atomRows = await db.all(
        'SELECT data FROM evidence_atoms WHERE caseId = ?',
        req.params.id,
      )
      const atoms = parseRows(atomRows)
      const conclusion = {
        id: recordId('CONC', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        currentStatus: 'Active',
        ...req.body,
      }
      const lineage = traceConclusion(conclusion, atoms)
      if (!lineage.sourceComplete) conclusion.currentStatus = 'Review Required'
      conclusion.lineage = {
        sourceComplete: lineage.sourceComplete,
        missingAtomIds: lineage.missingAtomIds,
        lineageBreaks: lineage.lineageBreaks,
      }

      await insertJson(db, 'conclusions', conclusion, {
        caseId: req.params.id,
        currentStatus: conclusion.currentStatus,
      })
      res.status(201).json({ conclusion, lineage })
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/conclusions', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM conclusions WHERE caseId = ? ORDER BY json_extract(data,"$.createdAt") DESC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/reconcile-invalidations', async (req, res, next) => {
    try {
      const db = await dbPromise
      const eventRows = await db.all(
        'SELECT data FROM resolution_events WHERE caseId = ?',
        req.params.id,
      )
      const conclusionRows = await db.all(
        'SELECT data FROM conclusions WHERE caseId = ?',
        req.params.id,
      )
      const existingRows = await db.all(
        'SELECT data FROM invalidations WHERE caseId = ?',
        req.params.id,
      )
      const events = parseRows(eventRows)
      const conclusions = parseRows(conclusionRows)
      const existingKeys = new Set(
        parseRows(existingRows).map(row => `${row.triggerId}:${row.impactedConclusionId}`),
      )
      const created = []

      for (const event of events) {
        const invalidations = findConclusionInvalidations(event, conclusions)
        for (const invalidation of invalidations) {
          const key = `${invalidation.triggerId}:${invalidation.impactedConclusionId}`
          if (existingKeys.has(key)) continue
          await insertJson(db, 'invalidations', invalidation, {
            caseId: req.params.id,
            impactedConclusionId: invalidation.impactedConclusionId,
            triggerId: invalidation.triggerId,
          })
          existingKeys.add(key)
          created.push(invalidation)

          const conclusion = conclusions.find(item => item.id === invalidation.impactedConclusionId)
          if (conclusion && conclusion.currentStatus !== 'Superseded') {
            const updated = {
              ...conclusion,
              currentStatus: 'Review Required',
              staleOrReviewReason: invalidation.reason,
              updatedAt: nowIso(),
            }
            await upsertJson(db, 'conclusions', updated, {
              caseId: req.params.id,
              currentStatus: updated.currentStatus,
            })
          }
        }
      }

      res.json({ created, count: created.length })
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/invalidations', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM invalidations WHERE caseId = ? ORDER BY json_extract(data,"$.createdAt") DESC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/review-decisions', async (req, res, next) => {
    try {
      if (!req.body.eventId || !req.body.decision) {
        return res.status(400).json({ error: 'eventId and decision are required' })
      }
      const db = await dbPromise
      const eventRow = await db.get(
        'SELECT data FROM resolution_events WHERE caseId = ? AND id = ?',
        req.params.id,
        req.body.eventId,
      )
      if (!eventRow) return res.status(404).json({ error: 'Resolution event not found' })
      const event = JSON.parse(eventRow.data)
      const debtRow = await db.get(
        'SELECT data FROM proof_debts WHERE caseId = ? AND id = ?',
        req.params.id,
        event.debtId,
      )
      if (!debtRow) return res.status(404).json({ error: 'Proof debt not found' })
      const debt = JSON.parse(debtRow.data)
      const reviewed = applyHumanReview({
        debt,
        event,
        decision: req.body.decision,
        reviewer: req.body.reviewer,
        rationale: req.body.rationale,
        checks: req.body.checks,
      })

      const lastReviewRow = await db.get(
        `SELECT data FROM review_decisions
         WHERE caseId = ? ORDER BY json_extract(data, '$.reviewedAt') DESC LIMIT 1`,
        req.params.id,
      )
      const previousHash = lastReviewRow ? JSON.parse(lastReviewRow.data).eventHash : ''
      const chainedDecision = createAuditChainEvent(reviewed.reviewDecision, previousHash)

      await db.exec('BEGIN')
      try {
        await insertJson(db, 'review_decisions', chainedDecision, {
          caseId: req.params.id,
          debtId: chainedDecision.debtId,
          eventId: chainedDecision.eventId,
        })
        await upsertJson(db, 'proof_debts', reviewed.updatedDebt, { caseId: req.params.id })
        await db.exec('COMMIT')
      } catch (error) {
        await db.exec('ROLLBACK')
        throw error
      }

      res.status(201).json({
        reviewDecision: chainedDecision,
        updatedDebt: reviewed.updatedDebt,
        guardrail: 'Only an accepted review with all required checks can resolve a proof debt.',
      })
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })
}
