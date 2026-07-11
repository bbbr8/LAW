import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildFinalBalanceControl,
  buildMoneyEventKey,
  evaluateClosureGate,
  findPotentialDuplicateFunding,
  normalizeMoney,
  rankAcquisitionRequests,
  reconcileObligation,
  validateMoneyEvent,
} from './accountingReconciliation.js'

test('money normalization and event keys preserve exact identity', () => {
  assert.equal(normalizeMoney('$103,453.21'), 103453.21)
  assert.equal(normalizeMoney('not money'), null)

  const key = buildMoneyEventKey({
    eventDate: '2018-04-25',
    accountOrLoan: 'CB1563',
    instrument: 'Wire',
    sourceEntity: 'Suited Construction',
    amount: '$103,453.21',
  })
  assert.equal(key, '2018-04-25|cb1563|wire|suited construction|103453.21')
})

test('money events require source and accounting identity', () => {
  const invalid = validateMoneyEvent({ id: 'ME-1', amount: 100 })
  assert.equal(invalid.valid, false)
  assert.ok(invalid.errors.includes('eventDate is required'))
  assert.ok(invalid.errors.includes('accountingRole is required'))

  const valid = validateMoneyEvent({
    id: 'ME-2',
    eventDate: '2018-04-25',
    eventType: 'title wire',
    amount: 103453.21,
    sourceStatus: 'source_closed',
    accountingRole: 'other_project_funding',
    project: 'Lot 2',
  })
  assert.equal(valid.valid, true)
})

test('closure gate blocks loss when any required proof field is unresolved', () => {
  const gate = evaluateClosureGate({
    projectIdentityStatus: 'source_closed',
    invoiceStatus: 'source_closed',
    deliveryStatus: 'source_closed',
    paymentStatus: 'source_closed',
    customerCreditStatus: 'Unresolved',
    finalTreatmentStatus: 'source_closed',
    duplicateRisk: 'none',
  })
  assert.equal(gate.pass, false)
  assert.ok(gate.missing.includes('customerCreditStatus'))
})

test('obligation reconciliation never converts unresolved funding into confirmed loss', () => {
  const obligation = {
    id: 'OB-1',
    category: 'Windows',
    project: 'Bryce/Lot 5',
    finalClaim: 48462.49,
    projectIdentityStatus: 'source_closed',
    invoiceStatus: 'source_closed',
    deliveryStatus: 'source_closed',
    paymentStatus: 'source_closed',
    customerCreditStatus: 'Unresolved',
    finalTreatmentStatus: 'source_closed',
    duplicateRisk: 'none',
  }
  const events = [
    {
      id: 'ME-1',
      obligationId: 'OB-1',
      project: 'Bryce/Lot 5',
      amount: 25000,
      accountingRole: 'draw_funding',
      sourceStatus: 'source_closed',
      customerCreditStatus: 'Resolved',
    },
    {
      id: 'ME-2',
      obligationId: 'OB-1',
      project: 'Bryce/Lot 5',
      amount: 22050.97,
      accountingRole: 'owner_funding',
      sourceStatus: 'source_routed',
      customerCreditStatus: 'Unresolved',
    },
  ]

  const result = reconcileObligation(obligation, events)
  assert.equal(result.confirmedFunding, 25000)
  assert.equal(result.unresolvedFunding, 22050.97)
  assert.equal(result.unresolvedGross, 23462.49)
  assert.equal(result.netConfirmedLoss, null)
  assert.equal(result.reconciliationStatus, 'In Review')
})

test('fully source-closed obligation can produce a limited confirmed remainder', () => {
  const obligation = {
    id: 'OB-2',
    category: 'Permit',
    project: 'Bryce/Lot 5',
    finalClaim: 16969.43,
    projectIdentityStatus: 'source_closed',
    invoiceStatus: 'source_closed',
    deliveryStatus: 'source_closed',
    paymentStatus: 'source_closed',
    customerCreditStatus: 'source_closed',
    finalTreatmentStatus: 'source_closed',
    duplicateRisk: 'resolved',
  }
  const events = [
    {
      id: 'ME-3',
      obligationId: 'OB-2',
      project: 'Bryce/Lot 5',
      amount: 16000,
      accountingRole: 'draw_funding',
      sourceStatus: 'source_closed',
      customerCreditStatus: 'Resolved',
    },
  ]

  const result = reconcileObligation(obligation, events)
  assert.equal(result.confirmedFunding, 16000)
  assert.equal(result.netConfirmedLoss, 969.43)
  assert.equal(result.reconciliationStatus, 'Partially Reconciled')
})

test('duplicate detection creates candidates without declaring duplication', () => {
  const candidates = findPotentialDuplicateFunding([
    {
      id: 'ME-10',
      project: 'Bryce/Lot 5',
      obligationId: 'OB-10',
      amount: 20000,
      accountingRole: 'owner_funding',
      sourceId: 'SRC-A',
    },
    {
      id: 'ME-11',
      project: 'Bryce/Lot 5',
      obligationId: 'OB-10',
      amount: 20000,
      accountingRole: 'customer_credit',
      sourceId: 'SRC-B',
    },
  ])
  assert.equal(candidates.length, 1)
  assert.equal(candidates[0].status, 'Candidate Review')
  assert.match(candidates[0].guardrail, /not duplicates/)
})

test('final balance excludes unresolved adjustments from confirmed net', () => {
  const control = buildFinalBalanceControl({
    totalCost: 1101159.96,
    confirmedBudget: 792256,
    confirmedOwnerFunding: 251522.43,
    unresolvedAdjustments: [55000, 20000, 50000],
  })
  assert.equal(control.confirmedNetBalance, 57381.53)
  assert.equal(control.unresolvedAdjustmentTotal, 125000)
  assert.equal(control.candidateNetBalance, null)
})

test('acquisition ranking prioritizes high collapse and damages value', () => {
  const ranked = rankAcquisitionRequests([
    {
      id: 'NBS-LOW',
      informationGain: 40,
      collapseValue: 40,
      damagesImpact: 20,
      linkedClaimCount: 1,
      availability: 'high',
      estimatedCost: 'low',
    },
    {
      id: 'NBS-HIGH',
      informationGain: 100,
      collapseValue: 100,
      damagesImpact: 100,
      linkedClaimCount: 8,
      availability: 'medium',
      estimatedCost: 'medium',
    },
  ])
  assert.equal(ranked[0].id, 'NBS-HIGH')
  assert.ok(ranked[0].priorityScore > ranked[1].priorityScore)
})
