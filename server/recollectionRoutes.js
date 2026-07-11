import {
  buildHfLearningProjection,
  buildStatement,
  buildTopicLearningExample,
  compareStatementVersions,
  evaluateStatementPromotion,
  scoreEvidenceForStatement,
  statementLearningConfig,
} from './recollectionLearning.js'

function parseRows(rows) {
  return rows.map(row => JSON.parse(row.data))
}

async function insertStatement(db, statement, isCurrent = 1) {
  await db.run(
    `INSERT INTO user_statements
      (id, caseId, canonicalId, version, isCurrent, currentStatus, recordDigest, data)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    statement.id,
    statement.caseId,
    statement.canonicalId,
    statement.version,
    isCurrent,
    statement.currentStatus,
    statement.recordDigest,
    JSON.stringify(statement),
  )
}

async function updateStatement(db, statement, isCurrent = 1) {
  await db.run(
    `UPDATE user_statements
     SET isCurrent = ?, currentStatus = ?, data = ?
     WHERE caseId = ? AND id = ?`,
    isCurrent,
    statement.currentStatus,
    JSON.stringify(statement),
    statement.caseId,
    statement.id,
  )
}

async function insertConflict(db, conflict) {
  await db.run(
    `INSERT INTO statement_conflicts
      (id, caseId, canonicalId, status, data)
     VALUES (?, ?, ?, ?, ?)`,
    conflict.id,
    conflict.caseId,
    conflict.canonicalId,
    conflict.status,
    JSON.stringify(conflict),
  )
}

async function readStatement(db, caseId, statementId) {
  const row = await db.get(
    'SELECT data FROM user_statements WHERE caseId = ? AND id = ?',
    caseId,
    statementId,
  )
  return row ? JSON.parse(row.data) : null
}

async function readSourceLinks(db, caseId, statementId) {
  const rows = await db.all(
    'SELECT data FROM statement_source_links WHERE caseId = ? AND statementId = ? ORDER BY createdAt ASC, id ASC',
    caseId,
    statementId,
  )
  return parseRows(rows)
}

export function registerRecollectionRoutes(app, dbPromise) {
  app.get('/api/recollection-learning/config', (_req, res) => {
    res.json({
      schemaVersion: 'recollection-learning-config.v1',
      ...statementLearningConfig,
      guardrails: [
        'Exact user language is preserved as a versioned statement.',
        'A correction creates a new version and never erases the earlier statement.',
        'First-person facts are limited to what the speaker did, knew, received, understood, or authorized.',
        'Recollections of another actor require independent source closure for attribution and intent.',
        'Hugging Face projections exclude exact language unless a private approved workflow explicitly includes it.',
      ],
    })
  })

  app.post('/api/cases/:id/user-statements', async (req, res, next) => {
    try {
      const statement = buildStatement({ ...req.body, caseId: req.params.id })
      const db = await dbPromise
      const duplicate = await db.get(
        'SELECT data FROM user_statements WHERE caseId = ? AND recordDigest = ?',
        req.params.id,
        statement.recordDigest,
      )
      if (duplicate) return res.status(200).json({ duplicate: true, statement: JSON.parse(duplicate.data) })
      await insertStatement(db, statement, 1)
      res.status(201).json({
        duplicate: false,
        statement,
        guardrail: 'The statement is preserved as a source-controlled recollection, not independent proof of another actor.',
      })
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.get('/api/cases/:id/user-statements', async (req, res, next) => {
    try {
      const db = await dbPromise
      const clauses = ['caseId = ?']
      const params = [req.params.id]
      if (req.query.currentOnly !== 'false') clauses.push('isCurrent = 1')
      if (req.query.canonicalId) {
        clauses.push('canonicalId = ?')
        params.push(String(req.query.canonicalId))
      }
      if (req.query.status) {
        clauses.push('currentStatus = ?')
        params.push(String(req.query.status))
      }
      const rows = await db.all(
        `SELECT data FROM user_statements
         WHERE ${clauses.join(' AND ')}
         ORDER BY canonicalId ASC, version DESC, id ASC`,
        ...params,
      )
      let statements = parseRows(rows)
      if (req.query.topic) {
        const topic = String(req.query.topic).trim().toLowerCase().replace(/[\s-]+/g, '_')
        statements = statements.filter(statement => statement.topicIds.includes(topic))
      }
      res.json(statements)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/user-statements/:statementId', async (req, res, next) => {
    try {
      const db = await dbPromise
      const statement = await readStatement(db, req.params.id, req.params.statementId)
      if (!statement) return res.status(404).json({ error: 'Statement not found' })
      const [versions, sourceLinks] = await Promise.all([
        db.all(
          'SELECT data FROM user_statements WHERE caseId = ? AND canonicalId = ? ORDER BY version ASC',
          req.params.id,
          statement.canonicalId,
        ),
        readSourceLinks(db, req.params.id, statement.id),
      ])
      res.json({ statement, versions: parseRows(versions), sourceLinks })
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/user-statements/:statementId/revise', async (req, res, next) => {
    try {
      const db = await dbPromise
      const previous = await readStatement(db, req.params.id, req.params.statementId)
      if (!previous) return res.status(404).json({ error: 'Statement not found' })
      const comparison = compareStatementVersions(previous, {
        ...req.body,
        caseId: req.params.id,
      })
      const duplicate = await db.get(
        'SELECT data FROM user_statements WHERE caseId = ? AND recordDigest = ?',
        req.params.id,
        comparison.next.recordDigest,
      )
      if (duplicate) return res.status(200).json({ duplicate: true, statement: JSON.parse(duplicate.data), comparison })

      await db.exec('BEGIN')
      try {
        await db.run(
          'UPDATE user_statements SET isCurrent = 0 WHERE caseId = ? AND canonicalId = ?',
          req.params.id,
          previous.canonicalId,
        )
        await insertStatement(db, comparison.next, 1)
        if (comparison.conflict) await insertConflict(db, comparison.conflict)
        await db.exec('COMMIT')
      } catch (error) {
        await db.exec('ROLLBACK')
        throw error
      }

      res.status(201).json({
        duplicate: false,
        statement: comparison.next,
        materialChange: comparison.material,
        differences: comparison.differences,
        conflict: comparison.conflict,
        guardrail: 'The previous version remains in history and is not overwritten.',
      })
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.get('/api/cases/:id/statement-conflicts', async (req, res, next) => {
    try {
      const db = await dbPromise
      const clauses = ['caseId = ?']
      const params = [req.params.id]
      if (req.query.status) {
        clauses.push('status = ?')
        params.push(String(req.query.status))
      }
      const rows = await db.all(
        `SELECT data FROM statement_conflicts
         WHERE ${clauses.join(' AND ')}
         ORDER BY json_extract(data, '$.createdAt') DESC, id DESC`,
        ...params,
      )
      res.json(parseRows(rows))
    } catch (error) {
      next(error)
    }
  })

  app.post('/api/cases/:id/user-statements/:statementId/source-links', async (req, res, next) => {
    try {
      const db = await dbPromise
      const statement = await readStatement(db, req.params.id, req.params.statementId)
      if (!statement) return res.status(404).json({ error: 'Statement not found' })
      if (!req.body.sourceId && !req.body.nativeLocator) {
        return res.status(400).json({ error: 'sourceId or nativeLocator is required' })
      }
      const createdAt = new Date().toISOString()
      const link = {
        schemaVersion: 'statement-source-link.v1',
        id: req.body.id || `UST-LINK-${crypto.randomUUID()}`,
        caseId: req.params.id,
        statementId: statement.id,
        canonicalStatementId: statement.canonicalId,
        createdAt,
        sourceId: req.body.sourceId || null,
        nativeLocator: req.body.nativeLocator || null,
        sourceStatus: String(req.body.sourceStatus || 'source_routed'),
        relation: String(req.body.relation || 'candidate_support'),
        nativeSourceChecked: req.body.nativeSourceChecked === true,
        contradictionRole: req.body.contradictionRole || null,
        notes: req.body.notes || null,
      }
      await db.run(
        `INSERT INTO statement_source_links
          (id, caseId, statementId, sourceId, createdAt, data)
         VALUES (?, ?, ?, ?, ?, ?)`,
        link.id,
        link.caseId,
        link.statementId,
        link.sourceId,
        link.createdAt,
        JSON.stringify(link),
      )
      const sourceLinks = await readSourceLinks(db, req.params.id, statement.id)
      const promotion = evaluateStatementPromotion(statement, sourceLinks, req.body.review || {})
      const updated = {
        ...statement,
        currentStatus: promotion.nextStatus,
        lastPromotionEvaluation: {
          ...promotion,
          evaluatedAt: new Date().toISOString(),
        },
      }
      await updateStatement(db, updated, 1)
      res.status(201).json({ link, statement: updated, promotion })
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.post('/api/cases/:id/user-statements/:statementId/evaluate-source', async (req, res, next) => {
    try {
      const db = await dbPromise
      const statement = await readStatement(db, req.params.id, req.params.statementId)
      if (!statement) return res.status(404).json({ error: 'Statement not found' })
      const result = scoreEvidenceForStatement(statement, req.body || {})
      res.json(result)
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.post('/api/cases/:id/user-statements/:statementId/topic-example', async (req, res, next) => {
    try {
      const db = await dbPromise
      const statement = await readStatement(db, req.params.id, req.params.statementId)
      if (!statement) return res.status(404).json({ error: 'Statement not found' })
      const example = buildTopicLearningExample(statement, req.body || {})
      await db.run(
        `INSERT INTO topic_learning_examples
          (id, caseId, statementId, exampleType, data)
         VALUES (?, ?, ?, ?, ?)`,
        example.id,
        example.caseId,
        example.statementId,
        example.exampleType,
        JSON.stringify(example),
      )
      res.status(201).json(example)
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })

  app.get('/api/cases/:id/topic-learning-examples', async (req, res, next) => {
    try {
      const db = await dbPromise
      const rows = await db.all(
        'SELECT data FROM topic_learning_examples WHERE caseId = ? ORDER BY id ASC',
        req.params.id,
      )
      let examples = parseRows(rows)
      if (req.query.topic) {
        const topic = String(req.query.topic).trim().toLowerCase().replace(/[\s-]+/g, '_')
        examples = examples.filter(example => example.topicIds.includes(topic))
      }
      res.json(examples)
    } catch (error) {
      next(error)
    }
  })

  app.get('/api/cases/:id/user-statements/:statementId/hf-projection', async (req, res, next) => {
    try {
      const db = await dbPromise
      const statement = await readStatement(db, req.params.id, req.params.statementId)
      if (!statement) return res.status(404).json({ error: 'Statement not found' })
      const includeExactLanguage = req.query.includeExactLanguage === 'true'
      if (includeExactLanguage && req.query.privateApproved !== 'true') {
        return res.status(400).json({ error: 'privateApproved=true is required to include exact language' })
      }
      res.json(buildHfLearningProjection(statement, { includeExactLanguage }))
    } catch (error) {
      if (error instanceof TypeError) return res.status(400).json({ error: error.message })
      next(error)
    }
  })
}
