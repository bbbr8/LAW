import express from 'express'
import cors from 'cors'
import { initDb } from './db.js'
import { ensureAccountingSchema } from './accountingSchema.js'
import { registerAccountingRoutes } from './accountingRoutes.js'

const app = express()
app.use(cors())
app.use(express.json({ limit: '10mb' }))

const PORT = Number(process.env.ACCOUNTING_PORT || 3002)
const dbPromise = initDb().then(async db => {
  await ensureAccountingSchema(db)
  return db
})

registerAccountingRoutes(app, dbPromise)

app.get('/api/accounting-health', async (req, res, next) => {
  try {
    const db = await dbPromise
    const tables = await db.all(
      `SELECT name FROM sqlite_master
       WHERE type = 'table' AND name IN (
         'money_events',
         'accounting_obligations',
         'accounting_reconciliation_runs',
         'final_balance_controls',
         'source_requests'
       )
       ORDER BY name`,
    )
    res.json({
      ok: tables.length === 5,
      service: 'native-accounting-reconciliation',
      port: PORT,
      tables: tables.map(row => row.name),
      guardrail: 'The service never nets unresolved adjustments or creates confirmed loss without closure-gate proof.',
    })
  } catch (error) {
    next(error)
  }
})

app.use((error, req, res, next) => {
  console.error(error)
  if (res.headersSent) return next(error)
  res.status(500).json({ error: 'Accounting service error' })
})

app.listen(PORT, () => {
  console.log(`Accounting reconciliation service running on http://localhost:${PORT}`)
})
