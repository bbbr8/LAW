import crypto from 'crypto'

const MAX_PAYLOAD_BYTES = 256 * 1024

const CONNECTOR_ALIASES = Object.freeze({
  app: 'case_api',
  case_api: 'case_api',
  drive: 'google_drive',
  google_drive: 'google_drive',
  gmail: 'gmail',
  github: 'github',
  hf: 'hugging_face',
  huggingface: 'hugging_face',
  hugging_face: 'hugging_face',
  figma: 'figma',
  figjam: 'figma',
  dropbox: 'dropbox',
})

export const CONNECTOR_PROFILES = Object.freeze({
  case_api: Object.freeze({
    id: 'case_api',
    label: 'Case API',
    role: 'Orchestration, durable routing, proof-debt and review control',
    trustBoundary: 'private_control_plane',
    writePolicy: 'internal_controlled',
    allowedPayloadModes: ['source_pointer', 'metadata', 'redacted_derivative', 'control_record', 'visual_projection', 'model_candidate', 'acknowledgement'],
    canReceivePrivileged: true,
    acknowledgementRequired: false,
  }),
  google_drive: Object.freeze({
    id: 'google_drive',
    label: 'Google Drive',
    role: 'Native evidence vault and controlling source registry',
    trustBoundary: 'private_evidence_plane',
    writePolicy: 'explicit_authorization_only',
    allowedPayloadModes: ['source_pointer', 'metadata', 'redacted_derivative', 'control_record', 'visual_projection', 'model_candidate', 'acknowledgement'],
    canReceivePrivileged: true,
    acknowledgementRequired: true,
  }),
  gmail: Object.freeze({
    id: 'gmail',
    label: 'Gmail',
    role: 'Native communication source and EML/attachment provenance lane',
    trustBoundary: 'private_evidence_plane',
    writePolicy: 'explicit_authorization_only',
    allowedPayloadModes: ['source_pointer', 'metadata', 'control_record', 'acknowledgement'],
    canReceivePrivileged: true,
    acknowledgementRequired: true,
  }),
  github: Object.freeze({
    id: 'github',
    label: 'GitHub',
    role: 'Versioned code, schemas, tests, synthetic fixtures, and reproducibility history',
    trustBoundary: 'public_control_plane',
    writePolicy: 'explicit_authorization_only',
    allowedPayloadModes: ['source_pointer', 'metadata', 'control_record', 'acknowledgement'],
    canReceivePrivileged: false,
    acknowledgementRequired: true,
  }),
  hugging_face: Object.freeze({
    id: 'hugging_face',
    label: 'Hugging Face',
    role: 'Private/local semantic retrieval, reranking, classification, and candidate generation',
    trustBoundary: 'private_derivative_compute_only',
    writePolicy: 'explicit_authorization_only',
    allowedPayloadModes: ['source_pointer', 'metadata', 'redacted_derivative', 'control_record', 'model_candidate', 'acknowledgement'],
    canReceivePrivileged: false,
    acknowledgementRequired: true,
  }),
  figma: Object.freeze({
    id: 'figma',
    label: 'Figma / FigJam',
    role: 'Editable visual projection of source-routed nodes, edges, proof gaps, and review state',
    trustBoundary: 'derivative_visual_plane',
    writePolicy: 'explicit_authorization_only',
    allowedPayloadModes: ['source_pointer', 'metadata', 'control_record', 'visual_projection', 'acknowledgement'],
    canReceivePrivileged: false,
    acknowledgementRequired: true,
  }),
  dropbox: Object.freeze({
    id: 'dropbox',
    label: 'Dropbox',
    role: 'Legacy source/cache pointer and access-history lane',
    trustBoundary: 'private_legacy_plane',
    writePolicy: 'explicit_authorization_only',
    allowedPayloadModes: ['source_pointer', 'metadata', 'control_record', 'acknowledgement'],
    canReceivePrivileged: true,
    acknowledgementRequired: true,
  }),
})

const SOURCE_STATUSES = new Set([
  'native_source', 'first_person_source_fact', 'sworn_source_fact', 'source_derived',
  'investigative_inference', 'proof_gap', 'candidate', 'human_confirmed',
  'non_proof', 'context_only', 'superseded', 'rejected', 'quarantined', 'do_not_count',
])
const PAYLOAD_MODES = new Set([
  'source_pointer', 'metadata', 'redacted_derivative', 'control_record',
  'visual_projection', 'model_candidate', 'acknowledgement',
])
const INTENTS = new Set(['observe', 'route', 'analyze', 'visualize', 'mutate', 'acknowledge'])
const PRIVILEGE_LEVELS = new Set(['none', 'confidential', 'privileged'])
const SENSITIVITY_LEVELS = new Set(['public_control', 'internal', 'confidential', 'restricted_case'])
const PRIVATE_HF_SCOPES = new Set(['local', 'private_endpoint', 'private_space'])
const PROMOTION_BLOCKED_STATUSES = new Set(['candidate', 'investigative_inference', 'proof_gap', 'non_proof', 'context_only', 'superseded', 'rejected', 'quarantined', 'do_not_count'])
const MUTATING_OPERATIONS = new Set(['create', 'update', 'write', 'move', 'rename', 'delete', 'send', 'archive', 'label', 'publish', 'push', 'merge'])
const FORBIDDEN_KEYS = new Set(['accesstoken', 'refreshtoken', 'oauthtoken', 'password', 'secret', 'rawbytes', 'filebytes', 'attachmentbytes', 'nativecontent', 'base64'])
const PUBLIC_TEXT_KEYS = new Set(['body', 'text', 'documenttext', 'messagebody', 'ocrtext', 'transcript', 'attachmentcontent', 'nativebody'])

function nowIso() {
  return new Date().toISOString()
}

function normalizeToken(value) {
  return String(value ?? '').trim().toLowerCase().replace(/[\s-]+/g, '_')
}

export function normalizeConnectorId(value) {
  const normalized = normalizeToken(value)
  return CONNECTOR_ALIASES[normalized] || normalized
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(Object.keys(value).sort().map(key => [key, stableValue(value[key])]))
}

export function stableStringify(value) {
  return JSON.stringify(stableValue(value))
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex')
}

function objectSize(value) {
  return Buffer.byteLength(stableStringify(value), 'utf8')
}

function walkObject(value, visitor, path = []) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => walkObject(item, visitor, [...path, index]))
    return
  }
  if (!value || typeof value !== 'object') return
  for (const [key, item] of Object.entries(value)) {
    visitor(key, item, [...path, key])
    walkObject(item, visitor, [...path, key])
  }
}

function validateAuthorization(input, intent, operation) {
  const mutating = intent === 'mutate' || MUTATING_OPERATIONS.has(normalizeToken(operation))
  if (!mutating) return []
  const errors = []
  const authorization = input.authorization
  if (!authorization || authorization.explicit !== true) {
    errors.push('Mutating connector messages require authorization.explicit=true.')
    return errors
  }
  if (!String(authorization.authorizedBy || '').trim()) errors.push('Mutating connector messages require authorization.authorizedBy.')
  if (!String(authorization.authorizedAt || '').trim()) errors.push('Mutating connector messages require authorization.authorizedAt.')
  if (!String(authorization.scope || '').trim()) errors.push('Mutating connector messages require authorization.scope.')
  return errors
}

function findForbiddenPayloadKeys(payload, targets) {
  const findings = []
  const publicTargets = targets.some(target => ['github', 'figma'].includes(target))
  walkObject(payload, (key, _value, path) => {
    const normalized = normalizeToken(key).replace(/_/g, '')
    if (FORBIDDEN_KEYS.has(normalized)) findings.push(path.join('.'))
    if (publicTargets && PUBLIC_TEXT_KEYS.has(normalized)) findings.push(path.join('.'))
  })
  return [...new Set(findings)]
}

function promotionBlock(sourceStatus, payloadMode) {
  const reasons = []
  if (PROMOTION_BLOCKED_STATUSES.has(sourceStatus)) reasons.push(`source_status:${sourceStatus}`)
  if (['model_candidate', 'visual_projection'].includes(payloadMode)) reasons.push(`payload_mode:${payloadMode}`)
  return { blocked: reasons.length > 0, reasons }
}

export function validateConnectorMessage(input = {}) {
  const errors = []
  const sourceSystem = normalizeConnectorId(input.sourceSystem)
  const targets = [...new Set((Array.isArray(input.targets) ? input.targets : [input.targetSystem]).filter(Boolean).map(normalizeConnectorId))]
  const sourceStatus = normalizeToken(input.sourceStatus)
  const payloadMode = normalizeToken(input.payloadMode)
  const intent = normalizeToken(input.intent || 'route')
  const privilege = normalizeToken(input.privilege || 'none')
  const sensitivity = normalizeToken(input.sensitivity || 'internal')
  const operation = normalizeToken(input.operation || '')

  if (!String(input.caseId || '').trim()) errors.push('caseId is required.')
  if (!CONNECTOR_PROFILES[sourceSystem]) errors.push(`Unknown sourceSystem: ${sourceSystem || '(empty)'}.`)
  if (targets.length === 0) errors.push('At least one target connector is required.')
  for (const target of targets) if (!CONNECTOR_PROFILES[target]) errors.push(`Unknown target connector: ${target}.`)
  if (!String(input.eventType || '').trim()) errors.push('eventType is required.')
  if (!String(input.objectType || '').trim()) errors.push('objectType is required.')
  if (!String(input.objectId || '').trim()) errors.push('objectId is required.')
  if (!SOURCE_STATUSES.has(sourceStatus)) errors.push(`Unsupported sourceStatus: ${sourceStatus || '(empty)'}.`)
  if (!PAYLOAD_MODES.has(payloadMode)) errors.push(`Unsupported payloadMode: ${payloadMode || '(empty)'}.`)
  if (!INTENTS.has(intent)) errors.push(`Unsupported intent: ${intent || '(empty)'}.`)
  if (!PRIVILEGE_LEVELS.has(privilege)) errors.push(`Unsupported privilege: ${privilege || '(empty)'}.`)
  if (!SENSITIVITY_LEVELS.has(sensitivity)) errors.push(`Unsupported sensitivity: ${sensitivity || '(empty)'}.`)
  if (input.payload !== undefined && (input.payload === null || typeof input.payload !== 'object' || Array.isArray(input.payload))) errors.push('payload must be an object.')
  if (objectSize(input.payload || {}) > MAX_PAYLOAD_BYTES) errors.push(`payload exceeds ${MAX_PAYLOAD_BYTES} bytes.`)
  if (sourceStatus === 'native_source' && !String(input.nativeLocator || '').trim()) errors.push('native_source messages require nativeLocator.')

  for (const target of targets) {
    const profile = CONNECTOR_PROFILES[target]
    if (profile && !profile.allowedPayloadModes.includes(payloadMode)) errors.push(`${target} does not allow payloadMode ${payloadMode}.`)
    if (privilege === 'privileged' && profile && !profile.canReceivePrivileged) errors.push(`${target} cannot receive privileged content.`)
  }

  if (targets.includes('hugging_face')) {
    const processingScope = normalizeToken(input.processingScope)
    if (!PRIVATE_HF_SCOPES.has(processingScope)) errors.push('Hugging Face routing requires processingScope local, private_endpoint, or private_space.')
    if (sensitivity === 'restricted_case' && !['source_pointer', 'metadata'].includes(payloadMode)) errors.push('Restricted case material may reach Hugging Face only as a source pointer or metadata record.')
  }

  if (targets.includes('github') && !['source_pointer', 'metadata', 'control_record', 'acknowledgement'].includes(payloadMode)) errors.push('GitHub accepts only source pointers, metadata, control records, or acknowledgements.')

  const forbiddenKeys = findForbiddenPayloadKeys(input.payload || {}, targets)
  if (forbiddenKeys.length) errors.push(`payload contains forbidden fields: ${forbiddenKeys.join(', ')}`)
  errors.push(...validateAuthorization(input, intent, operation))

  return {
    valid: errors.length === 0,
    errors,
    normalized: { sourceSystem, targets, sourceStatus, payloadMode, intent, privilege, sensitivity, operation },
  }
}

export function buildConnectorMessage(input = {}) {
  const validation = validateConnectorMessage(input)
  if (!validation.valid) throw new TypeError(validation.errors.join(' '))
  const normalized = validation.normalized
  const createdAt = input.createdAt || nowIso()
  const payload = stableValue(input.payload || {})
  const contentDigest = sha256(stableStringify(payload))
  const revisionIdentity = input.sourceHash || input.revision || input.nativeLocator || contentDigest
  const idempotencyKey = input.idempotencyKey || sha256(stableStringify({
    caseId: input.caseId,
    sourceSystem: normalized.sourceSystem,
    targets: normalized.targets,
    eventType: input.eventType,
    objectType: input.objectType,
    objectId: input.objectId,
    revisionIdentity,
    contentDigest,
  }))

  return {
    schemaVersion: 'connector-envelope.v1',
    id: input.id || `XMSG-${crypto.randomUUID()}`,
    caseId: input.caseId,
    correlationId: input.correlationId || `CORR-${crypto.randomUUID()}`,
    causationId: input.causationId || null,
    idempotencyKey,
    contentDigest,
    createdAt,
    occurredAt: input.occurredAt || null,
    observedAt: input.observedAt || createdAt,
    sourceSystem: normalized.sourceSystem,
    targets: normalized.targets,
    eventType: String(input.eventType),
    objectType: String(input.objectType),
    objectId: String(input.objectId),
    intent: normalized.intent,
    operation: normalized.operation || null,
    source: {
      status: normalized.sourceStatus,
      proofTier: input.proofTier || null,
      nativeLocator: input.nativeLocator || null,
      sourceHash: input.sourceHash || null,
      revision: input.revision || null,
      sourceFamilyId: input.sourceFamilyId || null,
      bridgeRecordNeeded: input.bridgeRecordNeeded || null,
    },
    privacy: {
      sensitivity: normalized.sensitivity,
      privilege: normalized.privilege,
      payloadMode: normalized.payloadMode,
      processingScope: input.processingScope ? normalizeToken(input.processingScope) : null,
    },
    authorization: input.authorization || null,
    promotion: promotionBlock(normalized.sourceStatus, normalized.payloadMode),
    payload,
  }
}

export function buildConnectorDeliveries(message, at = nowIso()) {
  if (!message?.id || !Array.isArray(message.targets)) throw new TypeError('A connector message with targets is required.')
  return message.targets.map(targetSystem => ({
    schemaVersion: 'connector-delivery.v1',
    id: `XDLV-${crypto.randomUUID()}`,
    caseId: message.caseId,
    messageId: message.id,
    targetSystem,
    status: 'pending',
    attempts: 0,
    acknowledgementRequired: CONNECTOR_PROFILES[targetSystem]?.acknowledgementRequired ?? true,
    createdAt: at,
    updatedAt: at,
    lastAttemptAt: null,
    deliveredAt: null,
    acknowledgedAt: null,
    receipt: null,
    error: null,
  }))
}

const DELIVERY_TRANSITIONS = Object.freeze({
  pending: new Set(['in_progress', 'skipped', 'dead_letter']),
  in_progress: new Set(['delivered', 'failed', 'dead_letter']),
  delivered: new Set(['acknowledged', 'failed']),
  failed: new Set(['in_progress', 'dead_letter', 'skipped']),
  acknowledged: new Set([]),
  dead_letter: new Set(['in_progress', 'skipped']),
  skipped: new Set([]),
})

export function transitionDelivery(delivery, nextStatus, details = {}, at = nowIso()) {
  const currentStatus = normalizeToken(delivery?.status)
  const normalizedNext = normalizeToken(nextStatus)
  if (!DELIVERY_TRANSITIONS[currentStatus]) throw new TypeError(`Unknown delivery status: ${currentStatus || '(empty)'}.`)
  if (!DELIVERY_TRANSITIONS[currentStatus].has(normalizedNext)) throw new TypeError(`Invalid delivery transition ${currentStatus} -> ${normalizedNext}.`)
  const attempts = normalizedNext === 'in_progress' ? Number(delivery.attempts || 0) + 1 : Number(delivery.attempts || 0)
  return {
    ...delivery,
    status: normalizedNext,
    attempts,
    updatedAt: at,
    lastAttemptAt: normalizedNext === 'in_progress' ? at : delivery.lastAttemptAt,
    deliveredAt: normalizedNext === 'delivered' ? at : delivery.deliveredAt,
    acknowledgedAt: normalizedNext === 'acknowledged' ? at : delivery.acknowledgedAt,
    receipt: details.receipt ?? delivery.receipt ?? null,
    error: ['failed', 'dead_letter'].includes(normalizedNext) ? details.error || 'unspecified delivery failure' : null,
  }
}

export function buildCheckpoint(input = {}) {
  const connectorId = normalizeConnectorId(input.connectorId)
  if (!String(input.caseId || '').trim()) throw new TypeError('caseId is required.')
  if (!CONNECTOR_PROFILES[connectorId]) throw new TypeError(`Unknown connectorId: ${connectorId || '(empty)'}.`)
  if (!String(input.stream || '').trim()) throw new TypeError('stream is required.')
  if (!String(input.cursor || '').trim()) throw new TypeError('cursor is required.')
  const updatedAt = input.updatedAt || nowIso()
  return {
    schemaVersion: 'connector-checkpoint.v1',
    id: input.id || `XCP-${sha256(`${input.caseId}:${connectorId}:${input.stream}`).slice(0, 24)}`,
    caseId: input.caseId,
    connectorId,
    stream: String(input.stream),
    cursor: String(input.cursor),
    watermarkAt: input.watermarkAt || null,
    sourceRevision: input.sourceRevision || null,
    updatedAt,
  }
}

export function summarizeConnectorHealth(messages = [], deliveries = [], checkpoints = [], now = Date.now()) {
  const messageById = new Map(messages.map(message => [message.id, message]))
  const connectors = Object.keys(CONNECTOR_PROFILES).map(connectorId => {
    const relevant = deliveries.filter(delivery => delivery.targetSystem === connectorId)
    const pending = relevant.filter(delivery => ['pending', 'in_progress', 'failed'].includes(delivery.status))
    const pendingTimes = pending.map(delivery => Date.parse(delivery.createdAt || delivery.updatedAt || '')).filter(Number.isFinite)
    const latestAck = relevant.map(delivery => Date.parse(delivery.acknowledgedAt || '')).filter(Number.isFinite).sort((a, b) => b - a)[0]
    const connectorCheckpoints = checkpoints.filter(checkpoint => checkpoint.connectorId === connectorId)
    return {
      connectorId,
      label: CONNECTOR_PROFILES[connectorId].label,
      sourceMessages: messages.filter(message => message.sourceSystem === connectorId).length,
      queued: relevant.length,
      pending: pending.length,
      delivered: relevant.filter(delivery => delivery.status === 'delivered').length,
      acknowledged: relevant.filter(delivery => delivery.status === 'acknowledged').length,
      failed: relevant.filter(delivery => delivery.status === 'failed').length,
      deadLetter: relevant.filter(delivery => delivery.status === 'dead_letter').length,
      promotionBlocked: relevant.filter(delivery => messageById.get(delivery.messageId)?.promotion?.blocked).length,
      oldestPendingAgeMs: pendingTimes.length ? Math.max(0, now - Math.min(...pendingTimes)) : 0,
      lastAcknowledgedAt: latestAck ? new Date(latestAck).toISOString() : null,
      checkpoints: connectorCheckpoints.length,
      lastCheckpointAt: connectorCheckpoints.map(checkpoint => checkpoint.updatedAt).filter(Boolean).sort().at(-1) || null,
    }
  })
  return {
    generatedAt: new Date(now).toISOString(),
    messageCount: messages.length,
    deliveryCount: deliveries.length,
    checkpointCount: checkpoints.length,
    connectors,
  }
}

export function connectorCapabilities() {
  return Object.values(CONNECTOR_PROFILES).map(profile => ({ ...profile }))
}
