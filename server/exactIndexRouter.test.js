import test from 'node:test'
import assert from 'node:assert/strict'
import { buildExactRoutePlan, extractExactKeys, normalizeExactKey } from './exactIndexRouter.js'

test('extracts exact money, loan, account, check, draw, date, Bates, and file keys', () => {
  const query = 'Find $103,453.21 on 2018-04-25 in loan 105109326, account 1563, check 266733, Draw 3, FORTIS JONES 001066, and BD1-Aug_2018_cost_breakdown.xlsx.'
  const keys = extractExactKeys(query)
  const signatures = new Set(keys.map(key => `${key.type}:${key.normalized}`))

  assert.ok(signatures.has('amount:103453.21'))
  assert.ok(signatures.has('date:2018-04-25'))
  assert.ok(signatures.has('loan:105109326'))
  assert.ok(signatures.has('account:1563'))
  assert.ok(signatures.has('check:266733'))
  assert.ok(signatures.has('draw:3'))
  assert.ok(signatures.has('file:bd1-aug_2018_cost_breakdown.xlsx'))
  assert.ok([...signatures].some(value => value.startsWith('bates:FORTIS JONES')))
})

test('routes exact indexes before semantic retrieval', () => {
  const plan = buildExactRoutePlan('Review $63,543.47 and loan 105109326', {
    aliasTerms: ['Lot 2', 'Loretta'],
    identityFirewalls: ['Lot 2 is not Lot 5'],
    openDebtTerms: ['PDR-009', 'PDR-010'],
  })

  const semanticIndex = plan.routeOrder.findIndex(route => route.engine === 'semantic_retrieval')
  const amountIndex = plan.routeOrder.findIndex(route => route.engine === 'amount_index')
  const loanIndex = plan.routeOrder.findIndex(route => route.engine === 'loan_index')

  assert.ok(amountIndex >= 0 && amountIndex < semanticIndex)
  assert.ok(loanIndex >= 0 && loanIndex < semanticIndex)
  assert.deepEqual(plan.identityFirewalls, ['Lot 2 is not Lot 5'])
})

test('normalization preserves exact distinctions', () => {
  assert.equal(normalizeExactKey('amount', '$103,453.21'), '103453.21')
  assert.notEqual(normalizeExactKey('amount', '$103,453.21'), normalizeExactKey('amount', '$103,458.21'))
  assert.equal(normalizeExactKey('file', 'BD1.XLSX'), 'bd1.xlsx')
})
