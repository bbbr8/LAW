import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildResolutionEvent,
  classifyScore,
  findResolutionCandidates,
  normalizeMoney,
  normalizeText,
  propagateResolutionEvent,
  scoreEvidenceAgainstDebt,
} from './proofDebtResolver.js'

const debt = {
  id: 'PDR-009',
  canonicalEntities: ['Lot 2', 'Loretta', 'Suited Construction'],
  aliases: ['Lot 2 Loretta', 'loan 105109326'],
  triggerTerms: ['customer ledger', 'reimbursement credit'],
  amounts: [103453.21, 63543.47],
  dateWindow: { start: '2018-04-01', end: '2018-05-31' },
  expectedDocumentTypes: ['project ledger', 'customer subledger'],
  expectedCustodians: ['Suited', 'Central Bank'],
  relatedLanes: ['Lot 2', 'owner advances', 'final accounting'],
  identityKeys: ['105109326'],
  resolutionStatus: 'Open',
}

const strongEvidence = {
  id: 'SRC-001',
  name: 'Lot 2 customer subledger 105109326',
  text: 'Suited Construction reimbursement credit for Lot 2 Loretta',
  entities: ['Lot 2', 'Suited Construction'],
  amounts: [63543.47],
  date: '2018-05-10',
  documentType: 'customer subledger',
  custodian: 'Central Bank',
  lanes: ['Lot 2', 'final accounting'],
  accountLoanKeys: ['105109326'],
  nativeLocator: 'Native XLSX / Ledger!A1:Q50',
  sourceStatus: 'source_closed',
  isNative: true,
}

test('normalization is stable for text and money', () => {
  assert.equal(normalizeText('  LOT-2 / Loretta  '), 'lot 2 loretta')
  assert.equal(normalizeMoney('$103,453.21'), 103453.21)
  assert.equal(normalizeMoney('not money'), null)
})

test('strong evidence receives a high-priority score', () => {
  const result = scoreEvidenceAgainstDebt(debt, strongEvidence)
  assert.equal(result.score, 100)
  assert.equal(result.threshold, 'high_priority_human_validation')
  assert.ok(result.reasons.some(reason => reason.criterion === 'amount'))
  assert.ok(result.reasons.some(reason => reason.criterion === 'identityKey'))
})

test('weak semantic evidence does not auto-resolve', () => {
  const weakEvidence = {
    id: 'SRC-002',
    text: 'A generic construction accounting document',
    lanes: ['construction'],
  }
  const result = scoreEvidenceAgainstDebt(debt, weakEvidence)
  assert.ok(result.score < 40)
  assert.equal(classifyScore(result.score), 'log_only')
})

test('candidate search checks every open debt', () => {
  const unrelatedDebt = {
    id: 'PDR-OTHER',
    canonicalEntities: ['Unrelated Project'],
    resolutionStatus: 'Open',
  }
  const candidates = findResolutionCandidates([unrelatedDebt, debt], strongEvidence)
  assert.equal(candidates.length, 1)
  assert.equal(candidates[0].debtId, 'PDR-009')
})

test('resolution events require human validation and propagate dependencies', () => {
  const candidate = scoreEvidenceAgainstDebt(debt, strongEvidence)
  const event = buildResolutionEvent(debt, strongEvidence, candidate, 'SR-001')
  assert.equal(event.newStatus, 'Candidate Review')
  assert.equal(event.humanValidation, 'Pending')

  const propagation = propagateResolutionEvent(event, [
    {
      id: 'DG-001',
      fromId: 'PDR-009',
      relation: 'AFFECTS',
      toId: 'CLAIM-LOT2',
      propagationRule: 'Rerun whole-case accounting',
      sourceStatus: 'bridge_missing',
    },
  ])
  assert.equal(propagation.length, 1)
  assert.equal(propagation[0].targetId, 'CLAIM-LOT2')
})
