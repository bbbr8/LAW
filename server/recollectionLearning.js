import crypto from 'crypto'
import { extractExactKeys } from './exactIndexRouter.js'

const SOURCE_CLASSES = new Set([
  'first_person_recollection',
  'first_person_self_fact',
  'user_correction',
  'sworn_first_person',
  'user_authored_source',
  'user_authored_source_with_embedded_quote',
  'interpretation',
])

const DIMENSIONS = new Set([
  'self_action',
  'self_knowledge',
  'self_authorization',
  'self_receipt_timing',
  'self_understanding',
  'accounting_correction',
  'recollection_of_other_statement',
  'recollection_of_event',
  'interpretation',
])

const PROMOTION_BLOCKED_CLASSES = new Set([
  'first_person_recollection',
  'user_correction',
  'user_authored_source_with_embedded_quote',
  'interpretation',
])

function preserveExactLanguage(value = '') {
  return String(value).replace(/\r\n/g, '\n').trim()
}

function normalizeText(value = '') {
  return String(value)
    .normalize('NFKC')
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201C\u201D]/g, '"')
    .replace(/\s+/g, ' ')
    .trim()
}

function normalizeToken(value = '') {
  return normalizeText(value).toLowerCase().replace(/[\s-]+/g, '_')
}

function unique(values = []) {
  return [...new Set(values.filter(Boolean))]
}

function nowIso() {
  return new Date().toISOString()
}

function sha256(value) {
  return crypto.createHash('sha256').update(String(value)).digest('hex')
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(Object.keys(value).sort().map(key => [key, stableValue(value[key])]))
}

function stableStringify(value) {
  return JSON.stringify(stableValue(value))
}

function normalizeStringArray(value) {
  if (value === undefined || value === null) return []
  const values = Array.isArray(value) ? value : [value]
  return unique(values.map(normalizeText).filter(Boolean))
}

function canonicalKey(statement) {
  const subject = normalizeToken(statement.subject || 'borrower')
  const dimension = normalizeToken(statement.dimension)
  const topics = [...statement.topicIds].sort().join('|')
  const eventPeriod = normalizeText(statement.eventPeriod || 'unknown')
  const objectIds = [...statement.objectIds].sort().join('|')
  return sha256(`${subject}\n${dimension}\n${topics}\n${eventPeriod}\n${objectIds}`)
}

function extractNormalizedKeys(text) {
  return extractExactKeys(text).map(key => `${key.type}:${key.normalized}`).sort()
}

function tokenSet(text) {
  return new Set(normalizeText(text).toLowerCase().split(/[^a-z0-9$.-]+/).filter(token => token.length > 1))
}

function jaccard(leftText, rightText) {
  const left = tokenSet(leftText)
  const right = tokenSet(rightText)
  if (left.size === 0 && right.size === 0) return 1
  const intersection = [...left].filter(token => right.has(token)).length
  const union = new Set([...left, ...right]).size
  return union ? intersection / union : 0
}

function defaultStatus(sourceClass, dimension) {
  if (sourceClass === 'sworn_first_person' && ['self_action', 'self_knowledge', 'self_authorization', 'self_receipt_timing', 'self_understanding'].includes(dimension)) {
    return 'Sworn First-Person Fact — Scope Limited to Speaker Knowledge'
  }
  if (sourceClass === 'first_person_self_fact') return 'First-Person Source Fact — Scope Limited to Speaker Knowledge'
  if (sourceClass === 'user_correction') return 'User Correction — Native Reconciliation Required'
  if (sourceClass === 'interpretation') return 'Investigative Interpretation — Not Proof'
  return 'First-Person Recollection — Needs Source Closure'
}

function promotionBlockers(sourceClass, dimension) {
  const blockers = []
  if (PROMOTION_BLOCKED_CLASSES.has(sourceClass)) blockers.push(`source_class:${sourceClass}`)
  if (['recollection_of_other_statement', 'recollection_of_event', 'interpretation', 'accounting_correction'].includes(dimension)) blockers.push(`dimension:${dimension}`)
  return unique(blockers)
}

export function validateStatementInput(input = {}) {
  const errors = []
  const exactLanguage = preserveExactLanguage(input.exactLanguage)
  const sourceClass = normalizeToken(input.sourceClass)
  const dimension = normalizeToken(input.dimension)
  const topicIds = normalizeStringArray(input.topicIds).map(normalizeToken)

  if (!normalizeText(input.caseId)) errors.push('caseId is required.')
  if (!exactLanguage) errors.push('exactLanguage is required.')
  if (!SOURCE_CLASSES.has(sourceClass)) errors.push(`Unsupported sourceClass: ${sourceClass || '(empty)'}.`)
  if (!DIMENSIONS.has(dimension)) errors.push(`Unsupported dimension: ${dimension || '(empty)'}.`)
  if (topicIds.length === 0) errors.push('At least one topicId is required.')
  if (input.sourcePointers !== undefined && !Array.isArray(input.sourcePointers)) errors.push('sourcePointers must be an array.')
  if (input.nativeRecordNeeds !== undefined && !Array.isArray(input.nativeRecordNeeds)) errors.push('nativeRecordNeeds must be an array.')
  if (input.competingExplanations !== undefined && !Array.isArray(input.competingExplanations)) errors.push('competingExplanations must be an array.')
  if (input.falsifiers !== undefined && !Array.isArray(input.falsifiers)) errors.push('falsifiers must be an array.')

  return { valid: errors.length === 0, errors, normalized: { exactLanguage, sourceClass, dimension, topicIds } }
}

export function buildStatement(input = {}) {
  const validation = validateStatementInput(input)
  if (!validation.valid) throw new TypeError(validation.errors.join(' '))
  const createdAt = input.createdAt || nowIso()
  const normalized = validation.normalized
  const sourcePointers = (input.sourcePointers || []).map(pointer => ({
    sourceSystem: normalizeToken(pointer.sourceSystem || 'unknown'),
    locator: normalizeText(pointer.locator),
    sourceId: normalizeText(pointer.sourceId),
    sourceHash: normalizeText(pointer.sourceHash),
    sourceStatus: normalizeToken(pointer.sourceStatus || 'source_routed'),
  })).filter(pointer => pointer.locator || pointer.sourceId)

  const statement = {
    schemaVersion: 'user-statement.v1',
    id: input.id || `USR-STMT-${crypto.randomUUID()}`,
    canonicalId: input.canonicalId || null,
    caseId: normalizeText(input.caseId),
    version: Number(input.version) || 1,
    supersedesId: input.supersedesId || null,
    createdAt,
    recordedAt: input.recordedAt || createdAt,
    eventPeriod: normalizeText(input.eventPeriod),
    subject: normalizeText(input.subject || 'Borrower'),
    exactLanguage: normalized.exactLanguage,
    normalizedStatement: normalizeText(input.normalizedStatement || normalized.exactLanguage),
    sourceClass: normalized.sourceClass,
    dimension: normalized.dimension,
    topicIds: normalized.topicIds,
    objectIds: normalizeStringArray(input.objectIds),
    actors: normalizeStringArray(input.actors),
    amountsOrObjects: normalizeStringArray(input.amountsOrObjects),
    sourcePointers,
    nativeRecordNeeds: normalizeStringArray(input.nativeRecordNeeds),
    competingExplanations: normalizeStringArray(input.competingExplanations),
    falsifiers: normalizeStringArray(input.falsifiers),
    correctionReason: normalizeText(input.correctionReason),
    currentStatus: normalizeText(input.currentStatus || defaultStatus(normalized.sourceClass, normalized.dimension)),
    exactKeys: extractNormalizedKeys(`${normalized.exactLanguage} ${input.normalizedStatement || ''}`),
    languageDigest: sha256(normalized.exactLanguage),
    promotion: {
      blocked: promotionBlockers(normalized.sourceClass, normalized.dimension).length > 0,
      blockers: promotionBlockers(normalized.sourceClass, normalized.dimension),
      humanReviewRequired: true,
    },
  }

  statement.canonicalId = statement.canonicalId || `UST-CAN-${canonicalKey(statement).slice(0, 24)}`
  statement.recordDigest = sha256(stableStringify({
    canonicalId: statement.canonicalId,
    version: statement.version,
    exactLanguage: statement.exactLanguage,
    sourceClass: statement.sourceClass,
    dimension: statement.dimension,
    topicIds: statement.topicIds,
    eventPeriod: statement.eventPeriod,
    exactKeys: statement.exactKeys,
  }))
  return statement
}

export function compareStatementVersions(previous, nextInput = {}) {
  if (!previous?.id) throw new TypeError('previous statement is required.')
  const next = buildStatement({
    ...previous,
    ...nextInput,
    id: nextInput.id,
    canonicalId: previous.canonicalId,
    version: Number(previous.version || 1) + 1,
    supersedesId: previous.id,
    createdAt: nextInput.createdAt,
    recordedAt: nextInput.recordedAt,
    currentStatus: nextInput.currentStatus,
  })

  const previousKeys = new Set(previous.exactKeys || extractNormalizedKeys(previous.exactLanguage || ''))
  const nextKeys = new Set(next.exactKeys)
  const removedKeys = [...previousKeys].filter(key => !nextKeys.has(key))
  const addedKeys = [...nextKeys].filter(key => !previousKeys.has(key))
  const languageSimilarity = jaccard(previous.exactLanguage || '', next.exactLanguage)
  const materialFieldsChanged = [
    previous.sourceClass !== next.sourceClass ? 'sourceClass' : null,
    previous.dimension !== next.dimension ? 'dimension' : null,
    previous.eventPeriod !== next.eventPeriod ? 'eventPeriod' : null,
    JSON.stringify([...(previous.topicIds || [])].sort()) !== JSON.stringify([...next.topicIds].sort()) ? 'topicIds' : null,
  ].filter(Boolean)
  const material = Boolean(
    removedKeys.length ||
    addedKeys.length ||
    materialFieldsChanged.length ||
    languageSimilarity < 0.78 ||
    next.sourceClass === 'user_correction'
  )

  return {
    next,
    material,
    differences: {
      languageSimilarity: Number(languageSimilarity.toFixed(4)),
      removedKeys,
      addedKeys,
      materialFieldsChanged,
      correctionReason: next.correctionReason || null,
    },
    conflict: material ? {
      schemaVersion: 'statement-conflict.v1',
      id: `UST-CONFLICT-${crypto.randomUUID()}`,
      caseId: previous.caseId,
      canonicalId: previous.canonicalId,
      previousStatementId: previous.id,
      nextStatementId: next.id,
      createdAt: nowIso(),
      status: 'Open — Preserve Both Versions',
      differences: {
        languageSimilarity: Number(languageSimilarity.toFixed(4)),
        removedKeys,
        addedKeys,
        materialFieldsChanged,
      },
      controllingRecordNeeded: unique([
        ...(previous.nativeRecordNeeds || []),
        ...(next.nativeRecordNeeds || []),
      ]),
      guardrail: 'A correction or changed recollection does not erase the earlier statement.',
    } : null,
  }
}

export function buildTopicLearningExample(statement, options = {}) {
  if (!statement?.id) throw new TypeError('statement is required.')
  const includeExactLanguage = options.includeExactLanguage === true
  const hardNegatives = normalizeStringArray(options.hardNegatives)
  const requiredFeatures = normalizeStringArray(options.requiredFeatures)
  return {
    schemaVersion: 'topic-learning-example.v1',
    id: options.id || `TLE-${crypto.randomUUID()}`,
    caseId: statement.caseId,
    statementId: statement.id,
    canonicalStatementId: statement.canonicalId,
    topicIds: [...statement.topicIds],
    exampleType: normalizeToken(options.exampleType || 'positive'),
    sourceClass: statement.sourceClass,
    dimension: statement.dimension,
    eventPeriod: statement.eventPeriod,
    exactKeys: [...statement.exactKeys],
    languageDigest: statement.languageDigest,
    exactLanguage: includeExactLanguage ? statement.exactLanguage : null,
    normalizedStatement: includeExactLanguage ? statement.normalizedStatement : null,
    sourcePointers: statement.sourcePointers.map(pointer => ({
      sourceSystem: pointer.sourceSystem,
      locator: pointer.locator,
      sourceId: pointer.sourceId,
      sourceStatus: pointer.sourceStatus,
    })),
    hardNegatives,
    requiredFeatures,
    expectedRoute: normalizeText(options.expectedRoute || statement.nativeRecordNeeds.join('; ')),
    expectedLabel: normalizeToken(options.expectedLabel || 'statement_source_route'),
    promotionBlocked: true,
    privacy: {
      exactLanguageIncluded: includeExactLanguage,
      recommendedHfScope: includeExactLanguage ? 'local_or_private_approved_only' : 'private_metadata_projection',
    },
  }
}

export function buildHfLearningProjection(statement, options = {}) {
  const example = buildTopicLearningExample(statement, {
    ...options,
    includeExactLanguage: options.includeExactLanguage === true,
  })
  return {
    schemaVersion: 'hf-topic-learning-projection.v1',
    projectionId: `HFPROJ-${crypto.randomUUID()}`,
    caseId: example.caseId,
    statementId: example.statementId,
    topicIds: example.topicIds,
    input: {
      exactKeys: example.exactKeys,
      sourceClass: example.sourceClass,
      dimension: example.dimension,
      eventPeriod: example.eventPeriod,
      languageDigest: example.languageDigest,
      exactLanguage: example.exactLanguage,
      normalizedStatement: example.normalizedStatement,
    },
    supervision: {
      exampleType: example.exampleType,
      hardNegatives: example.hardNegatives,
      requiredFeatures: example.requiredFeatures,
      expectedRoute: example.expectedRoute,
      expectedLabel: example.expectedLabel,
    },
    privacy: example.privacy,
    promotionBlocked: true,
  }
}

function flattenEvidenceText(evidence = {}) {
  return normalizeText([
    evidence.title,
    evidence.text,
    evidence.summary,
    evidence.nativeLocator,
    evidence.sourceId,
    ...(Array.isArray(evidence.identifiers) ? evidence.identifiers : []),
    ...(Array.isArray(evidence.topicIds) ? evidence.topicIds : []),
  ].filter(Boolean).join(' '))
}

export function scoreEvidenceForStatement(statement, evidence = {}) {
  if (!statement?.id) throw new TypeError('statement is required.')
  const evidenceText = flattenEvidenceText(evidence)
  if (!evidenceText) throw new TypeError('evidence text or identifiers are required.')
  const evidenceKeys = new Set(extractNormalizedKeys(evidenceText))
  const statementKeys = new Set(statement.exactKeys || [])
  const matchingKeys = [...statementKeys].filter(key => evidenceKeys.has(key))
  const topicMatches = (statement.topicIds || []).filter(topic => (evidence.topicIds || []).map(normalizeToken).includes(topic))
  const lexicalSimilarity = jaccard(statement.normalizedStatement || statement.exactLanguage || '', evidenceText)
  const sourceStrength = normalizeToken(evidence.sourceStatus) === 'native_source' ? 20 : normalizeToken(evidence.sourceStatus).includes('sworn') ? 14 : 5
  const score = Math.min(100, Math.round(
    matchingKeys.length * 15 +
    topicMatches.length * 12 +
    lexicalSimilarity * 40 +
    sourceStrength
  ))
  const candidateType = score >= 70 ? 'strong_source_candidate' : score >= 45 ? 'review_candidate' : 'weak_or_collision_candidate'
  return {
    statementId: statement.id,
    evidenceId: evidence.id || null,
    score,
    candidateType,
    matchingKeys,
    topicMatches,
    lexicalSimilarity: Number(lexicalSimilarity.toFixed(4)),
    sourceStatus: normalizeToken(evidence.sourceStatus || 'unknown'),
    promotionBlocked: true,
    requiredReview: [
      'native source identity',
      'speaker and observer-time scope',
      'contrary evidence',
      'collision and same-amount checks',
      'human review',
    ],
  }
}

export function evaluateStatementPromotion(statement, sourceLinks = [], review = {}) {
  if (!statement?.id) throw new TypeError('statement is required.')
  const links = sourceLinks.filter(link => link && typeof link === 'object')
  const nativeLinks = links.filter(link => normalizeToken(link.sourceStatus) === 'native_source' && link.nativeSourceChecked === true)
  const swornLinks = links.filter(link => normalizeToken(link.sourceStatus).includes('sworn'))
  const contraryChecked = review.contraryEvidenceChecked === true
  const identityChecked = review.identityFirewallChecked === true
  const observerTimeChecked = review.observerTimeChecked === true
  const humanReviewed = review.humanReviewed === true && normalizeText(review.reviewer)
  const selfLimitedDimension = ['self_action', 'self_knowledge', 'self_authorization', 'self_receipt_timing', 'self_understanding'].includes(statement.dimension)

  let status = statement.currentStatus
  const reasons = []
  if (!humanReviewed) reasons.push('human review missing')
  if (!contraryChecked) reasons.push('contrary evidence check missing')
  if (!identityChecked) reasons.push('identity firewall check missing')
  if (!observerTimeChecked) reasons.push('observer-time check missing')

  if (selfLimitedDimension && humanReviewed && contraryChecked && identityChecked && observerTimeChecked && (nativeLinks.length || swornLinks.length || statement.sourceClass === 'sworn_first_person')) {
    status = 'Human-Confirmed First-Person Fact — Limited to Speaker Knowledge'
  } else if (nativeLinks.length && contraryChecked && identityChecked) {
    status = 'Source-Supported Statement — Attribution/Intent Still Separate'
  } else if (links.length) {
    status = 'Source-Routed Statement — Not Confirmed'
  }

  return {
    statementId: statement.id,
    previousStatus: statement.currentStatus,
    nextStatus: status,
    promoted: status !== statement.currentStatus,
    nativeLinkCount: nativeLinks.length,
    swornLinkCount: swornLinks.length,
    reasons,
    guardrail: selfLimitedDimension
      ? 'Confirmation is limited to what the speaker did, knew, received, understood, or authorized.'
      : 'A source-supported recollection of another actor still requires independent attribution and intent proof.',
  }
}

export const statementLearningConfig = Object.freeze({
  sourceClasses: [...SOURCE_CLASSES],
  dimensions: [...DIMENSIONS],
  statuses: {
    defaultRecollection: 'First-Person Recollection — Needs Source Closure',
    correction: 'User Correction — Native Reconciliation Required',
    interpretation: 'Investigative Interpretation — Not Proof',
  },
})
