import test from 'node:test'
import assert from 'node:assert/strict'
import { buildAiFinding, reviewAiFinding } from './aiFinding.js'

const atom = {
  id: 'ATOM-1',
  nativeLocator: 'Native XLSX / Ledger!A1:Q50',
}

test('source-linked high-confidence result becomes an AI New Finding worth pursuing', () => {
  const finding = buildAiFinding({
    id: 'AIF-1',
    findingText: 'The Lot 2 transfer may be a reimbursement rather than a project cost.',
    confidenceScore: 0.82,
    supportingAtomIds: ['ATOM-1'],
    alternativeExplanations: ['Ordinary inter-project reimbursement'],
  }, [atom])

  assert.equal(finding.displayLabel, 'AI New Finding')
  assert.equal(finding.currentStatus, 'AI New Finding — Worth Pursuing')
  assert.equal(finding.reviewState, 'Questioned')
  assert.equal(finding.sourceComplete, true)
  assert.ok(finding.reviewQuestions.length >= 3)
})

test('an attractive conclusion without source anchors stays visibly unresolved', () => {
  const finding = buildAiFinding({
    id: 'AIF-2',
    findingText: 'A repeated amount may connect two transactions.',
    confidenceScore: 0.91,
  }, [])

  assert.equal(finding.currentStatus, 'AI New Finding — Needs Source Anchors')
  assert.equal(finding.autoConfirmed, false)
})

test('human confirmation requires source lineage and all adversarial checks', () => {
  const finding = buildAiFinding({
    id: 'AIF-3',
    findingText: 'The source-backed sequence supports a reimbursement finding.',
    confidenceScore: 0.88,
    supportingAtomIds: ['ATOM-1'],
  }, [atom])

  assert.throws(() => reviewAiFinding(finding, {
    reviewer: 'Reviewer',
    decision: 'confirm',
    checks: { nativeSourceChecked: true },
  }))

  const confirmed = reviewAiFinding(finding, {
    reviewer: 'Reviewer',
    decision: 'confirm',
    rationale: 'Native source and alternatives reviewed.',
    checks: {
      nativeSourceChecked: true,
      identityFirewallChecked: true,
      contraryEvidenceChecked: true,
      questionsResolved: true,
    },
  })

  assert.equal(confirmed.currentStatus, 'Human-Confirmed Finding')
  assert.equal(confirmed.originType, 'AI_ASSISTED')
  assert.equal(confirmed.autoConfirmed, false)
})
