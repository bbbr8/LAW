import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildCheckpoint,
  buildConnectorDeliveries,
  buildConnectorMessage,
  connectorCapabilities,
  normalizeConnectorId,
  stableStringify,
  summarizeConnectorHealth,
  transitionDelivery,
  validateConnectorMessage,
} from './connectorCommunication.js'

const base = {
  caseId: 'CASE-001',
  sourceSystem: 'drive',
  targets: ['case_api'],
  eventType: 'source.updated',
  objectType: 'evidence_source',
  objectId: 'SRC-001',
  sourceStatus: 'native_source',
  nativeLocator: 'drive:file:abc123',
  sourceHash: 'sha256:abc',
  payloadMode: 'source_pointer',
  payload: { fileId: 'abc123', title: 'Draw 1 packet' },
}

test('normalizes connector aliases', () => {
  assert.equal(normalizeConnectorId('Google Drive'), 'google_drive')
  assert.equal(normalizeConnectorId('HF'), 'hugging_face')
  assert.equal(normalizeConnectorId('FigJam'), 'figma')
})

test('stableStringify is key-order deterministic', () => {
  assert.equal(stableStringify({ b: 2, a: { d: 4, c: 3 } }), stableStringify({ a: { c: 3, d: 4 }, b: 2 }))
})

test('builds a source-bound message and deliveries', () => {
  const message = buildConnectorMessage(base)
  assert.equal(message.schemaVersion, 'connector-envelope.v1')
  assert.equal(message.sourceSystem, 'google_drive')
  assert.equal(message.source.nativeLocator, 'drive:file:abc123')
  assert.equal(message.promotion.blocked, false)
  assert.equal(message.idempotencyKey.length, 64)
  const deliveries = buildConnectorDeliveries(message, '2026-07-11T10:00:00.000Z')
  assert.equal(deliveries.length, 1)
  assert.equal(deliveries[0].targetSystem, 'case_api')
  assert.equal(deliveries[0].status, 'pending')
})

test('idempotency key is stable across key order and generated IDs', () => {
  const first = buildConnectorMessage(base)
  const second = buildConnectorMessage({ ...base, payload: { title: 'Draw 1 packet', fileId: 'abc123' } })
  assert.equal(first.idempotencyKey, second.idempotencyKey)
  assert.notEqual(first.id, second.id)
})

test('native sources require exact native locator', () => {
  const result = validateConnectorMessage({ ...base, nativeLocator: '' })
  assert.equal(result.valid, false)
  assert.match(result.errors.join(' '), /nativeLocator/)
})

test('GitHub blocks evidence text and non-control payload modes', () => {
  const result = validateConnectorMessage({
    ...base,
    targets: ['github'],
    payloadMode: 'redacted_derivative',
    sourceStatus: 'source_derived',
    payload: { documentText: 'case passage' },
  })
  assert.equal(result.valid, false)
  assert.match(result.errors.join(' '), /GitHub|forbidden/i)
})

test('Hugging Face requires private processing scope', () => {
  const invalid = validateConnectorMessage({
    ...base,
    targets: ['hugging_face'],
    payloadMode: 'redacted_derivative',
    sourceStatus: 'source_derived',
    payload: { passageId: 'PASS-1', redacted: true },
  })
  assert.equal(invalid.valid, false)
  const valid = validateConnectorMessage({
    ...base,
    targets: ['hugging_face'],
    payloadMode: 'redacted_derivative',
    sourceStatus: 'source_derived',
    processingScope: 'local',
    sensitivity: 'confidential',
    payload: { passageId: 'PASS-1', redacted: true },
  })
  assert.equal(valid.valid, true)
})

test('restricted material cannot be sent to Hugging Face as derivative text', () => {
  const result = validateConnectorMessage({
    ...base,
    targets: ['hugging_face'],
    payloadMode: 'redacted_derivative',
    processingScope: 'private_endpoint',
    sensitivity: 'restricted_case',
    sourceStatus: 'source_derived',
    payload: { passageId: 'PASS-1' },
  })
  assert.equal(result.valid, false)
  assert.match(result.errors.join(' '), /Restricted case material/)
})

test('mutations require explicit scoped authorization', () => {
  const denied = validateConnectorMessage({
    ...base,
    targets: ['google_drive'],
    intent: 'mutate',
    operation: 'update',
  })
  assert.equal(denied.valid, false)
  const allowed = validateConnectorMessage({
    ...base,
    targets: ['google_drive'],
    intent: 'mutate',
    operation: 'update',
    authorization: {
      explicit: true,
      authorizedBy: 'Bryce',
      authorizedAt: '2026-07-11T10:00:00.000Z',
      scope: 'append control row only; no native evidence changes',
    },
  })
  assert.equal(allowed.valid, true)
})

test('candidate and visual messages remain promotion blocked', () => {
  const candidate = buildConnectorMessage({
    ...base,
    sourceStatus: 'candidate',
    payloadMode: 'model_candidate',
    targets: ['case_api'],
  })
  assert.equal(candidate.promotion.blocked, true)
  assert.deepEqual(candidate.promotion.reasons, ['source_status:candidate', 'payload_mode:model_candidate'])
})

test('forbids secrets and binary evidence fields', () => {
  const result = validateConnectorMessage({ ...base, payload: { accessToken: 'secret', rawBytes: 'AAAA' } })
  assert.equal(result.valid, false)
  assert.match(result.errors.join(' '), /forbidden fields/)
})

test('delivery state machine records attempts, receipts, and acknowledgements', () => {
  const message = buildConnectorMessage(base)
  const [pending] = buildConnectorDeliveries(message, '2026-07-11T10:00:00.000Z')
  const active = transitionDelivery(pending, 'in_progress', {}, '2026-07-11T10:01:00.000Z')
  assert.equal(active.attempts, 1)
  const delivered = transitionDelivery(active, 'delivered', { receipt: { remoteId: 'abc' } }, '2026-07-11T10:02:00.000Z')
  assert.equal(delivered.receipt.remoteId, 'abc')
  const acknowledged = transitionDelivery(delivered, 'acknowledged', {}, '2026-07-11T10:03:00.000Z')
  assert.equal(acknowledged.status, 'acknowledged')
  assert.throws(() => transitionDelivery(acknowledged, 'in_progress'), /Invalid delivery transition/)
})

test('builds stable connector checkpoints', () => {
  const first = buildCheckpoint({ caseId: 'CASE-1', connectorId: 'figjam', stream: 'master-map', cursor: 'rev-22' })
  const second = buildCheckpoint({ caseId: 'CASE-1', connectorId: 'figma', stream: 'master-map', cursor: 'rev-23' })
  assert.equal(first.id, second.id)
  assert.equal(first.connectorId, 'figma')
})

test('summarizes health without treating blocked records as proof', () => {
  const message = buildConnectorMessage({
    ...base,
    sourceStatus: 'proof_gap',
    targets: ['figma'],
    payloadMode: 'visual_projection',
  })
  const [delivery] = buildConnectorDeliveries(message, '2026-07-11T10:00:00.000Z')
  const health = summarizeConnectorHealth([message], [delivery], [], Date.parse('2026-07-11T10:05:00.000Z'))
  const figma = health.connectors.find(row => row.connectorId === 'figma')
  assert.equal(figma.pending, 1)
  assert.equal(figma.promotionBlocked, 1)
  assert.equal(figma.oldestPendingAgeMs, 300000)
})

test('capabilities expose all configured planes', () => {
  const ids = connectorCapabilities().map(profile => profile.id)
  assert.deepEqual(ids, ['case_api', 'google_drive', 'gmail', 'github', 'hugging_face', 'figma', 'dropbox'])
})
