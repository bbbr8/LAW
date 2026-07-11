import test from 'node:test'
import assert from 'node:assert/strict'
import {
  applyHumanReview,
  createAuditChainEvent,
  findConclusionInvalidations,
  traceConclusion,
  validateEvidenceAtom,
} from './sourceLineage.js'

const atom = {
  id: 'ATOM-001',
  neutralFact: 'A wire was recorded.',
  sourceId: 'SRC-001',
  exactLocator: 'Bank statement p. 4',
  sourceSpecies: 'bank_record',
  proofTier: 'F0',
  sourceStatus: 'source_closed',
}

test('validates complete evidence atoms', () => {
  assert.deepEqual(validateEvidenceAtom(atom), { valid: true, errors: [] })
  const invalid = validateEvidenceAtom({ id: 'ATOM-BAD' })
  assert.equal(invalid.valid, false)
  assert.ok(invalid.errors.includes('exactLocator is required'))
})

test('traces conclusions to atoms and reports lineage breaks', () => {
  const good = traceConclusion({ id: 'CONC-1', supportingAtomIds: ['ATOM-001'] }, [atom])
  assert.equal(good.sourceComplete, true)

  const broken = traceConclusion({ id: 'CONC-2', supportingAtomIds: ['ATOM-MISSING'] }, [atom])
  assert.equal(broken.sourceComplete, false)
  assert.deepEqual(broken.missingAtomIds, ['ATOM-MISSING'])
})

test('finds conclusions affected by a changed proof debt', () => {
  const invalidations = findConclusionInvalidations(
    { id: 'RE-1', debtId: 'PDR-009', reason: 'New project ledger candidate' },
    [
      { id: 'CONC-1', openProofDebts: ['PDR-009'], currentStatus: 'Active' },
      { id: 'CONC-2', openProofDebts: ['PDR-OTHER'], currentStatus: 'Active' },
    ],
  )
  assert.equal(invalidations.length, 1)
  assert.equal(invalidations[0].impactedConclusionId, 'CONC-1')
  assert.equal(invalidations[0].newStatus, 'Review Required')
})

test('accept decision requires native, identity, and contrary-evidence checks', () => {
  assert.throws(
    () => applyHumanReview({
      debt: { id: 'PDR-009', resolutionStatus: 'Candidate Review' },
      event: { id: 'RE-1', evidenceId: 'SRC-1' },
      decision: 'accept',
      reviewer: 'Reviewer',
      rationale: 'Looks relevant',
      checks: { nativeChecked: true },
    }),
    /Accept requires checks/,
  )

  const reviewed = applyHumanReview({
    debt: { id: 'PDR-009', resolutionStatus: 'Candidate Review' },
    event: { id: 'RE-1', evidenceId: 'SRC-1' },
    decision: 'accept',
    reviewer: 'Reviewer',
    rationale: 'Native ledger confirms the exact customer credit.',
    checks: {
      nativeChecked: true,
      identityFirewallChecked: true,
      contraryEvidenceChecked: true,
    },
  })
  assert.equal(reviewed.updatedDebt.resolutionStatus, 'Resolved')
  assert.equal(reviewed.updatedDebt.resolutionSource, 'SRC-1')
})

test('audit-chain events change hash when content changes', () => {
  const first = createAuditChainEvent({ id: 'E-1', value: 1 })
  const second = createAuditChainEvent({ id: 'E-2', value: 2 }, first.eventHash)
  const changed = createAuditChainEvent({ id: 'E-2', value: 3 }, first.eventHash)

  assert.equal(second.previousHash, first.eventHash)
  assert.notEqual(second.eventHash, changed.eventHash)
})
