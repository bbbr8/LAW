import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildHfLearningProjection,
  buildStatement,
  buildTopicLearningExample,
  compareStatementVersions,
  evaluateStatementPromotion,
  scoreEvidenceForStatement,
  statementLearningConfig,
  validateStatementInput,
} from './recollectionLearning.js'

const base = {
  caseId: 'CASE-001',
  exactLanguage: 'I signed only Draw 1 and did not authorize the later draw forms.',
  sourceClass: 'first_person_recollection',
  dimension: 'self_authorization',
  topicIds: ['draw-auth'],
  eventPeriod: '2018',
  actors: ['Borrower', 'Builder', 'Lender'],
  amountsOrObjects: ['Draw 1', 'Draws 2-4'],
  sourcePointers: [{ sourceSystem: 'gmail', locator: 'gmail:sent:message-1', sourceStatus: 'user_authored_source' }],
  nativeRecordNeeds: ['Native Draw/LIT PDFs', 'DocuSign certificates', 'Lender audit logs'],
  competingExplanations: ['A stored signature may have been used with separate authorization.'],
  falsifiers: ['Authenticated records show approval of each later instrument.'],
}

test('validates required statement fields and controlled classes', () => {
  assert.equal(validateStatementInput(base).valid, true)
  const invalid = validateStatementInput({ ...base, sourceClass: 'verified_truth' })
  assert.equal(invalid.valid, false)
  assert.match(invalid.errors.join(' '), /Unsupported sourceClass/)
})

test('preserves exact user language and applies conservative status', () => {
  const statement = buildStatement(base)
  assert.equal(statement.exactLanguage, base.exactLanguage)
  assert.equal(statement.currentStatus, 'First-Person Recollection — Needs Source Closure')
  assert.equal(statement.promotion.blocked, true)
  assert.match(statement.canonicalId, /^UST-CAN-/)
  assert.match(statement.recordDigest, /^[a-f0-9]{64}$/)
})

test('sworn self facts are limited to speaker knowledge', () => {
  const statement = buildStatement({
    ...base,
    exactLanguage: 'I did not receive the later draw emails in 2018.',
    sourceClass: 'sworn_first_person',
    dimension: 'self_receipt_timing',
  })
  assert.equal(statement.currentStatus, 'Sworn First-Person Fact — Scope Limited to Speaker Knowledge')
})

test('extracts exact accounting keys for collision control', () => {
  const statement = buildStatement({
    ...base,
    exactLanguage: 'The $16,519.43 item was returned on 2018-04-10.',
    sourceClass: 'user_correction',
    dimension: 'accounting_correction',
    topicIds: ['owner-funding'],
  })
  assert.ok(statement.exactKeys.includes('amount:16519.43'))
  assert.ok(statement.exactKeys.includes('date:2018-04-10'))
})

test('material corrections create a conflict and preserve both versions', () => {
  const previous = buildStatement({
    ...base,
    exactLanguage: 'I advanced $16,519.43 and counted it as owner funding.',
    sourceClass: 'first_person_recollection',
    dimension: 'self_action',
    topicIds: ['owner-funding'],
  })
  const comparison = compareStatementVersions(previous, {
    exactLanguage: 'The $16,519.43 item was returned and should not be counted as net owner funding.',
    sourceClass: 'user_correction',
    dimension: 'accounting_correction',
    correctionReason: 'Later source-of-funds review.',
  })
  assert.equal(comparison.material, true)
  assert.equal(comparison.next.version, 2)
  assert.equal(comparison.next.supersedesId, previous.id)
  assert.equal(comparison.conflict.status, 'Open — Preserve Both Versions')
  assert.equal(comparison.conflict.previousStatementId, previous.id)
})

test('minor wording cleanup does not automatically create a conflict', () => {
  const previous = buildStatement(base)
  const comparison = compareStatementVersions(previous, {
    exactLanguage: 'I signed only Draw 1, and I did not authorize the later draw forms.',
  })
  assert.equal(comparison.material, false)
  assert.equal(comparison.conflict, null)
})

test('topic learning examples exclude exact language by default', () => {
  const statement = buildStatement(base)
  const example = buildTopicLearningExample(statement, {
    hardNegatives: ['A PDF contains a signature image.'],
    requiredFeatures: ['native PDF', 'audit log'],
    expectedLabel: 'authorization_disputed',
  })
  assert.equal(example.exactLanguage, null)
  assert.equal(example.normalizedStatement, null)
  assert.equal(example.privacy.exactLanguageIncluded, false)
  assert.equal(example.promotionBlocked, true)
})

test('Hugging Face projection remains metadata-only unless explicitly approved', () => {
  const statement = buildStatement(base)
  const redacted = buildHfLearningProjection(statement)
  assert.equal(redacted.input.exactLanguage, null)
  assert.equal(redacted.privacy.recommendedHfScope, 'private_metadata_projection')
  const privateProjection = buildHfLearningProjection(statement, { includeExactLanguage: true })
  assert.equal(privateProjection.input.exactLanguage, base.exactLanguage)
  assert.equal(privateProjection.privacy.recommendedHfScope, 'local_or_private_approved_only')
})

test('scores native evidence candidates without promoting them', () => {
  const statement = buildStatement({
    ...base,
    exactLanguage: 'I was told the $15,000 excavator advance would come back in the draw and was not extra money.',
    dimension: 'recollection_of_other_statement',
    topicIds: ['bridge-funding'],
  })
  const result = scoreEvidenceForStatement(statement, {
    id: 'SRC-1',
    sourceStatus: 'native_source',
    topicIds: ['bridge-funding'],
    text: 'Text message: $15,000 for the excavator will come back in the draw and is not extra money.',
    nativeLocator: 'MBJ_072057',
  })
  assert.ok(result.score >= 70)
  assert.equal(result.candidateType, 'strong_source_candidate')
  assert.equal(result.promotionBlocked, true)
  assert.ok(result.matchingKeys.includes('amount:15000.00'))
})

test('promotion of self facts requires human and scope checks', () => {
  const statement = buildStatement({
    ...base,
    sourceClass: 'sworn_first_person',
    dimension: 'self_authorization',
  })
  const incomplete = evaluateStatementPromotion(statement, [{
    sourceStatus: 'native_source',
    nativeSourceChecked: true,
  }], {
    humanReviewed: false,
    contraryEvidenceChecked: true,
    identityFirewallChecked: true,
    observerTimeChecked: true,
  })
  assert.equal(incomplete.promoted, false)

  const promoted = evaluateStatementPromotion(statement, [{
    sourceStatus: 'native_source',
    nativeSourceChecked: true,
  }], {
    humanReviewed: true,
    reviewer: 'Counsel Reviewer',
    contraryEvidenceChecked: true,
    identityFirewallChecked: true,
    observerTimeChecked: true,
  })
  assert.equal(promoted.promoted, true)
  assert.equal(promoted.nextStatus, 'Human-Confirmed First-Person Fact — Limited to Speaker Knowledge')
})

test('configuration exposes controlled statement classes and dimensions', () => {
  assert.ok(statementLearningConfig.sourceClasses.includes('user_correction'))
  assert.ok(statementLearningConfig.dimensions.includes('self_understanding'))
})
