import test from 'node:test'
import assert from 'node:assert/strict'
import { registerRecollectionRoutes } from './recollectionRoutes.js'

test('registers recollection, conflict, source-link, topic-learning, and HF projection routes', () => {
  const registered = []
  const app = {
    get(path, handler) {
      registered.push({ method: 'GET', path, handler })
    },
    post(path, handler) {
      registered.push({ method: 'POST', path, handler })
    },
  }

  registerRecollectionRoutes(app, Promise.resolve({}))

  assert.deepEqual(registered.map(route => `${route.method} ${route.path}`), [
    'GET /api/recollection-learning/config',
    'POST /api/cases/:id/user-statements',
    'GET /api/cases/:id/user-statements',
    'GET /api/cases/:id/user-statements/:statementId',
    'POST /api/cases/:id/user-statements/:statementId/revise',
    'GET /api/cases/:id/statement-conflicts',
    'POST /api/cases/:id/user-statements/:statementId/source-links',
    'POST /api/cases/:id/user-statements/:statementId/evaluate-source',
    'POST /api/cases/:id/user-statements/:statementId/topic-example',
    'GET /api/cases/:id/topic-learning-examples',
    'GET /api/cases/:id/user-statements/:statementId/hf-projection',
  ])
})
