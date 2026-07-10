import crypto from 'crypto'
import {
  buildFinalBalanceControl,
  findPotentialDuplicateFunding,
  rankAcquisitionRequests,
  reconcileObligation,
  validateMoneyEvent,
} from './accountingReconciliation.js'

function parseRows(rows) {
  return rows.map(row => JSON.parse(row.data))
}

function nowIso() {
  return new Date().toISOString()
}

function recordId(prefix, suppliedId) {
  return suppliedId || `${prefix}-${crypto.randomUUID()}`
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

export function registerAccountingRoutes(app, dbPromise) {
  app.get('/api/cases/:id/money-events', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM money_events WHERE caseId = ? ORDER BY json_extract(data,"$.eventDate") ASC, id ASC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/money-events', async (req, res, next) => {
    try {
      const event = {
        id: recordId('ME', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        ...req.body,
      }
      const validation = validateMoneyEvent(event)
      if (!validation.valid) return res.status(400).json({ error: validation.errors })

      const db = await dbPromise
      await insertJson(db, 'money_events', event, {
        caseId: req.params.id,
        obligationId: event.obligationId ?? null,
      })
      res.status(201).json(event)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/accounting-obligations', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM accounting_obligations WHERE caseId = ? ORDER BY id ASC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/accounting-obligations', async (req, res, next) => {
    try {
      if (!req.body.category || !req.body.project) {
        return res.status(400).json({ error: 'category and project are required' })
      }
      const createdAt = nowIso()
      const obligation = {
        id: recordId('OB', req.body.id),
        caseId: req.params.id,
        createdAt,
        updatedAt: createdAt,
        reconciliationStatus: 'Open',
        ...req.body,
      }
      const db = await dbPromise
      await insertJson(db, 'accounting_obligations', obligation, {
        caseId: req.params.id,
        reconciliationStatus: obligation.reconciliationStatus,
      })
      res.status(201).json(obligation)
    } catch (error) {
      next(error)
    }
  })

  app.patch('/api/cases/:id/accounting-obligations/:obligationId', async (req, res, next) => {
    try {
      const db = await dbPromise
      const row = await db.get(
        'SELECT data FROM accounting_obligations WHERE caseId = ? AND id = ?',
        req.params.id,
        req.params.obligationId,
      )
      if (!row) return res.status(404).json({ error: 'Accounting obligation not found' })
      const existing = JSON.parse(row.data)
      const updated = {
        ...existing,
        ...req.body,
        id: existing.id,
        caseId: existing.caseId,
        updatedAt: nowIso(),
      }
      await upsertJson(db, 'accounting_obligations', updated, {
        caseId: req.params.id,
        reconciliationStatus: updated.reconciliationStatus ?? 'Open',
      })
      res.json(updated)
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/reconcile-accounting', async (req, res, next) => {
    try {
      const db = await dbPromise
      const [obligationRows, eventRows] = await Promise.all([
        db.all('SELECT data FROM accounting_obligations WHERE caseId = ?', req.params.id),
        db.all('SELECT data FROM money_events WHERE caseId = ?', req.params.id),
      ])
      const obligations = parseRows(obligationRows)
      const events = parseRows(eventRows)
      const obligationFilter = new Set(req.body.obligationIds ?? [])
      const selected = obligationFilter.size
        ? obligations.filter(obligation => obligationFilter.has(obligation.id))
        : obligations
      const results = selected.map(obligation => reconcileObligation(obligation, events))
      const duplicates = findPotentialDuplicateFunding(events)
      const run = {
        id: recordId('ARUN', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        contextVersion: req.body.contextVersion ?? null,
        searchRunId: req.body.searchRunId ?? null,
        obligationCount: results.length,
        duplicateCandidateCount: duplicates.length,
        results,
        duplicateCandidates: duplicates,
        completenessLabel:
          results.every(result => result.closure.pass) && duplicates.length === 0
            ? 'SOURCE-CLOSED RECONCILIATION'
            : 'PARTIAL — ACCOUNTING PROOF DEBT REMAINS',
      }

      await db.exec('BEGIN')
      try {
        await insertJson(db, 'accounting_reconciliation_runs', run, {
          caseId: req.params.id,
        })
        for (const result of results) {
          const obligation = obligations.find(item => item.id === result.obligationId)
          if (!obligation) continue
          const updated = {
            ...obligation,
            reconciliationStatus: result.reconciliationStatus,
            latestReconciliationRunId: run.id,
            latestReconciliation: result,
            updatedAt: nowIso(),
          }
          await upsertJson(db, 'accounting_obligations', updated, {
            caseId: req.params.id,
            reconciliationStatus: updated.reconciliationStatus,
          })
        }
        await db.exec('COMMIT')
      } catch (error) {
        await db.exec('ROLLBACK')
        throw error
      }

      res.status(201).json(run)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/accounting-reconciliation-runs', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM accounting_reconciliation_runs WHERE caseId = ? ORDER BY json_extract(data,"$.createdAt") DESC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/final-balance-controls', async (req, res, next) => {
    try {
      const control = {
        id: recordId('FBC', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        contextVersion: req.body.contextVersion ?? null,
        sourceIds: req.body.sourceIds ?? [],
        ...buildFinalBalanceControl(req.body),
      }
      const db = await dbPromise
      await insertJson(db, 'final_balance_controls', control, { caseId: req.params.id })
      res.status(201).json(control)
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.get('/api/cases/:id/final-balance-controls', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM final_balance_controls WHERE caseId = ? ORDER BY json_extract(data,"$.createdAt") DESC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/source-requests', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM source_requests WHERE caseId = ? ORDER BY json_extract(data,"$.priorityScore") DESC, id ASC',
        req.params.id,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/source-requests', async (req, res, next) => {
    try {
      if (!req.body.targetCustodian || !req.body.requestedRecord) {
        return res.status(400).json({ error: 'targetCustodian and requestedRecord are required' })
      }
      const request = {
        id: recordId('RP', req.body.id),
        caseId: req.params.id,
        createdAt: nowIso(),
        status: 'Queued',
        ...req.body,
      }
      const [ranked] = rankAcquisitionRequests([request])
      const db = await dbPromise
      await insertJson(db, 'source_requests', ranked, {
        caseId: req.params.id,
        status: ranked.status,
      })
      res.status(201).json(ranked)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/acquisition-priorities', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all('SELECT data FROM source_requests WHERE caseId = ?', req.params.id)
      res.json(rankAcquisitionRequests(parseRows(rows)))
    } catch (error) {
      next(error)
    }
  })
}
