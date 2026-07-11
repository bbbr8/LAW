import test from 'node:test'
import assert from 'node:assert/strict'
import { registerConnectorRoutes } from './connectorRoutes.js'

test('registers connector capability, outbox, delivery, checkpoint, and health routes', () => {
  const registered = []
  const app = {
    get(path, handler) {
      registered.push({ method: 'GET', path, handler })
    },
    post(path, handler) {
      registered.push({ method: 'POST', path, handler })
    },
  }

  registerConnectorRoutes(app, Promise.resolve({}))

  const routeKeys = registered.map(route => `${route.method} ${route.path}`)
  assert.deepEqual(routeKeys, [
    'GET /api/connectors',
    'POST /api/cases/:id/connector-messages',
    'GET /api/cases/:id/connector-messages',
    'GET /api/cases/:id/connector-messages/:messageId',
    'GET /api/cases/:id/connector-deliveries',
    'POST /api/cases/:id/connector-deliveries/claim',
    'POST /api/cases/:id/connector-deliveries/:deliveryId/transition',
    'POST /api/cases/:id/connector-checkpoints',
    'GET /api/cases/:id/connector-checkpoints',
    'GET /api/cases/:id/connector-health',
  ])
})
