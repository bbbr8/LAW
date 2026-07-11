import {
  buildCheckpoint,
  buildConnectorDeliveries,
  buildConnectorMessage,
  connectorCapabilities,
  normalizeConnectorId,
  summarizeConnectorHealth,
  transitionDelivery,
} from './connectorCommunication.js'

function parseRows(rows) {
  return rows.map(row => JSON.parse(row.data))
}

async function insertMessage(db, message) {
  await db.run(
    `INSERT INTO connector_messages
      (id, caseId, sourceSystem, idempotencyKey, createdAt, data)
     VALUES (?, ?, ?, ?, ?, ?)`,
    message.id,
    message.caseId,
    message.sourceSystem,
    message.idempotencyKey,
    message.createdAt,
    JSON.stringify(message),
  )
}

async function insertDelivery(db, delivery) {
  await db.run(
    `INSERT INTO connector_deliveries
      (id, caseId, messageId, targetSystem, status, updatedAt, data)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    delivery.id,
    delivery.caseId,
    delivery.messageId,
    delivery.targetSystem,
    delivery.status,
    delivery.updatedAt,
    JSON.stringify(delivery),
  )
}

async function upsertDelivery(db, delivery) {
  await db.run(
    `INSERT INTO connector_deliveries
      (id, caseId, messageId, targetSystem, status, updatedAt, data)
     VALUES (?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET
       status = excluded.status,
       updatedAt = excluded.updatedAt,
       data = excluded.data`,
    delivery.id,
    delivery.caseId,
    delivery.messageId,
    delivery.targetSystem,
    delivery.status,
    delivery.updatedAt,
    JSON.stringify(delivery),
  )
}

async function upsertCheckpoint(db, checkpoint) {
  await db.run(
    `INSERT INTO connector_checkpoints
      (id, caseId, connectorId, stream, updatedAt, data)
     VALUES (?, ?, ?, ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET
       connectorId = excluded.connectorId,
       stream = excluded.stream,
       updatedAt = excluded.updatedAt,
       data = excluded.data`,
    checkpoint.id,
    checkpoint.caseId,
    checkpoint.connectorId,
    checkpoint.stream,
    checkpoint.updatedAt,
    JSON.stringify(checkpoint),
  )
}

async function readMessageBundle(db, caseId, messageId) {
  const messageRow = await db.get(
    'SELECT data FROM connector_messages WHERE caseId = ? AND id = ?',
    caseId,
    messageId,
  )
  if (!messageRow) return null
  const deliveryRows = await db.all(
    'SELECT data FROM connector_deliveries WHERE caseId = ? AND messageId = ? ORDER BY targetSystem, id',
    caseId,
    messageId,
  )
  return { message: JSON.parse(messageRow.data), deliveries: parseRows(deliveryRows) }
}

export function registerConnectorRoutes(app, dbPromise) {
  app.get('/api/connectors', (_req, res) => {
    res.json({
      schemaVersion: 'connector-capabilities.v1',
      connectors: connectorCapabilities(),
      guardrails: [
        'Native evidence remains in its controlling source system.',
        'Connector messages carry pointers, metadata, redacted derivatives, control records, visual projections, model candidates, or acknowledgements—not native file bytes.',
        'Mutations require explicit scoped authorization.',
        'Model candidates, visual projections, proof gaps, context-only items, and superseded records remain promotion blocked.',
      ],
    })
  })

  app.post('/api/cases/:id/connector-messages', async (req, res, next) => {
    try {
      const message = buildConnectorMessage({ ...req.body, caseId: req.params.id })
      const db = await dbPromise
      const duplicateRow = await db.get(
        'SELECT data FROM connector_messages WHERE caseId = ? AND idempotencyKey = ?',
        req.params.id,
        message.idempotencyKey,
      )
      if (duplicateRow) {
        const existing = JSON.parse(duplicateRow.data)
        const bundle = await readMessageBundle(db, req.params.id, existing.id)
        return res.status(200).json({ duplicate: true, ...bundle })
      }

      const deliveries = buildConnectorDeliveries(message)
      await db.exec('BEGIN')
      try {
        await insertMessage(db, message)
        for (const delivery of deliveries) await insertDelivery(db, delivery)
        await db.exec('COMMIT')
      } catch (error) {
        await db.exec('ROLLBACK')
        throw error
      }

      res.status(201).json({
        duplicate: false,
        message,
        deliveries,
        guardrail: 'Creation of a connector message does not prove delivery, acknowledgement, source validity, or promotion eligibility.',
      })
    } catch (error) {
      if (error instanceof TypeError || error instanceof RangeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.get('/api/cases/:id/connector-messages', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM connector_messages WHERE caseId = ? ORDER BY createdAt DESC, id DESC',
        req.params.id,
      )
      let messages = parseRows(rows)
      if (req.query.source) {
        const source = normalizeConnectorId(req.query.source)
        messages = messages.filter(message => message.sourceSystem === source)
      }
      if (req.query.target) {
        const target = normalizeConnectorId(req.query.target)
        messages = messages.filter(message => message.targets.includes(target))
      }
      if (req.query.eventType) messages = messages.filter(message => message.eventType === req.query.eventType)
      if (req.query.objectId) messages = messages.filter(message => message.objectId === req.query.objectId)
      res.json(messages)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/connector-messages/:messageId', async (req, res, next) => {
    try {
      const db = await dbPromise
      const bundle = await readMessageBundle(db, req.params.id, req.params.messageId)
      if (!bundle) return res.status(404).json({ error: 'Connector message not found' })
      res.json(bundle)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/connector-deliveries', async (req, res, next) => {
    try {
      const db = await dbPromise
      const clauses = ['caseId = ?']
      const params = [req.params.id]
      if (req.query.target) {
        clauses.push('targetSystem = ?')
        params.push(normalizeConnectorId(req.query.target))
      }
      if (req.query.status) {
        clauses.push('status = ?')
        params.push(String(req.query.status))
      }
      if (req.query.messageId) {
        clauses.push('messageId = ?')
        params.push(String(req.query.messageId))
      }
      const rows = await db.all(
        `SELECT data FROM connector_deliveries
         WHERE ${clauses.join(' AND ')}
         ORDER BY updatedAt ASC, id ASC`,
        ...params,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/connector-deliveries/claim', async (req, res, next) => {
    try {
      const targetSystem = normalizeConnectorId(req.body.targetSystem)
      if (!targetSystem) return res.status(400).json({ error: 'targetSystem is required' })
      const limit = Math.min(Math.max(Number(req.body.limit) || 10, 1), 50)
      const db = await dbPromise
      const claimed = []

      await db.exec('BEGIN IMMEDIATE')
      try {
        const rows = await db.all(
          `SELECT data FROM connector_deliveries
           WHERE caseId = ? AND targetSystem = ? AND status IN ('pending', 'failed', 'dead_letter')
           ORDER BY updatedAt ASC, id ASC
           LIMIT ?`,
          req.params.id,
          targetSystem,
          limit,
        )
        for (const delivery of parseRows(rows)) {
          const active = transitionDelivery(delivery, 'in_progress', {}, new Date().toISOString())
          await upsertDelivery(db, active)
          claimed.push(active)
        }
        await db.exec('COMMIT')
      } catch (error) {
        await db.exec('ROLLBACK')
        throw error
      }

      res.json({ targetSystem, claimed, count: claimed.length })
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.post('/api/cases/:id/connector-deliveries/:deliveryId/transition', async (req, res, next) => {
    try {
      const db = await dbPromise
      const row = await db.get(
        'SELECT data FROM connector_deliveries WHERE caseId = ? AND id = ?',
        req.params.id,
        req.params.deliveryId,
      )
      if (!row) return res.status(404).json({ error: 'Connector delivery not found' })
      const delivery = JSON.parse(row.data)
      const updated = transitionDelivery(delivery, req.body.status, {
        receipt: req.body.receipt,
        error: req.body.error,
      })
      await upsertDelivery(db, updated)
      res.json(updated)
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.post('/api/cases/:id/connector-checkpoints', async (req, res, next) => {
    try {
      const checkpoint = buildCheckpoint({ ...req.body, caseId: req.params.id })
      const db = await dbPromise
      await upsertCheckpoint(db, checkpoint)
      res.status(201).json(checkpoint)
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.get('/api/cases/:id/connector-checkpoints', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM connector_checkpoints WHERE caseId = ? ORDER BY updatedAt DESC, id ASC',
        req.params.id,
      )
      let checkpoints = parseRows(rows)
      if (req.query.connector) {
        const connectorId = normalizeConnectorId(req.query.connector)
        checkpoints = checkpoints.filter(checkpoint => checkpoint.connectorId === connectorId)
      }
      res.json(checkpoints)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/connector-health', async (req, res, next) => {
    try {
      const db = await dbPromise
      const [messageRows, deliveryRows, checkpointRows] = await Promise.all([
        db.all('SELECT data FROM connector_messages WHERE caseId = ?', req.params.id),
        db.all('SELECT data FROM connector_deliveries WHERE caseId = ?', req.params.id),
        db.all('SELECT data FROM connector_checkpoints WHERE caseId = ?', req.params.id),
      ])
      res.json(summarizeConnectorHealth(parseRows(messageRows), parseRows(deliveryRows), parseRows(checkpointRows)))
    } catch (error) {
      next(error)
    }
  })
}
