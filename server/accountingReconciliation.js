const SOURCE_CLOSED = new Set(['source_closed'])
const SOURCE_USABLE = new Set(['source_closed', 'source_closed_partial'])

const FUNDING_ROLES = new Set([
  'draw_funding',
  'owner_funding',
  'other_project_funding',
  'reimbursement',
  'customer_credit',
  'refund',
])

const REQUIRED_CLOSURE_FIELDS = Object.freeze([
  'projectIdentityStatus',
  'invoiceStatus',
  'deliveryStatus',
  'paymentStatus',
  'customerCreditStatus',
  'finalTreatmentStatus',
])

function asArray(value) {
  if (Array.isArray(value)) return value.filter(item => item !== null && item !== undefined)
  if (value === null || value === undefined || value === '') return []
  return [value]
}

function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFKD')
    .toLowerCase()
    .replace(/[^a-z0-9.]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ')
}

export function normalizeMoney(value) {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.round(value * 100) / 100
  }
  const parsed = Number(String(value).replace(/[$,\s]/g, ''))
  return Number.isFinite(parsed) ? Math.round(parsed * 100) / 100 : null
}

function roundMoney(value) {
  return Math.round((Number(value) + Number.EPSILON) * 100) / 100
}

export function buildMoneyEventKey(event) {
  const amount = normalizeMoney(event?.amount)
  return [
    event?.eventDate ?? '',
    normalizeText(event?.accountOrLoan),
    normalizeText(event?.instrument),
    normalizeText(event?.sourceEntity),
    amount === null ? '' : amount.toFixed(2),
  ].join('|')
}

export function validateMoneyEvent(event) {
  const errors = []
  if (!event?.id) errors.push('id is required')
  if (!event?.eventDate) errors.push('eventDate is required')
  if (!event?.eventType) errors.push('eventType is required')
  if (normalizeMoney(event?.amount) === null) errors.push('amount must be numeric')
  if (!event?.sourceStatus) errors.push('sourceStatus is required')
  if (!event?.accountingRole) errors.push('accountingRole is required')
  if (!event?.identityScope && !event?.project) {
    errors.push('identityScope or project is required')
  }

  return { valid: errors.length === 0, errors }
}

export function evaluateClosureGate(obligation) {
  const missing = REQUIRED_CLOSURE_FIELDS.filter(field => obligation?.[field] !== 'source_closed')
  const duplicateRisk = normalizeText(obligation?.duplicateRisk)
  if (duplicateRisk && duplicateRisk !== 'none' && duplicateRisk !== 'resolved') {
    missing.push('duplicateRisk')
  }

  return {
    pass: missing.length === 0,
    missing,
    requiredFields: [...REQUIRED_CLOSURE_FIELDS],
  }
}

function eventMatchesObligation(event, obligation) {
  const linked = asArray(event?.linkedObligationIds)
  if (linked.includes(obligation?.id)) return true

  if (event?.obligationId && event.obligationId === obligation?.id) return true

  const projectMatches =
    !obligation?.project ||
    !event?.project ||
    normalizeText(obligation.project) === normalizeText(event.project)
  const categoryMatches =
    !obligation?.category ||
    !event?.category ||
    normalizeText(obligation.category) === normalizeText(event.category)

  return projectMatches && categoryMatches && Boolean(event?.allowSemanticObligationMatch)
}

function summarizeFunding(events) {
  const confirmed = {}
  const unresolved = {}

  for (const role of FUNDING_ROLES) {
    confirmed[role] = 0
    unresolved[role] = 0
  }

  for (const event of events) {
    const role = normalizeText(event.accountingRole).replace(/ /g, '_')
    if (!FUNDING_ROLES.has(role)) continue
    const amount = normalizeMoney(event.amount)
    if (amount === null) continue

    if (SOURCE_CLOSED.has(event.sourceStatus) && event.customerCreditStatus !== 'Unresolved') {
      confirmed[role] = roundMoney(confirmed[role] + amount)
    } else {
      unresolved[role] = roundMoney(unresolved[role] + amount)
    }
  }

  return { confirmed, unresolved }
}

export function reconcileObligation(obligation, moneyEvents) {
  if (!obligation?.id) throw new TypeError('obligation.id is required')
  const finalClaim = normalizeMoney(obligation.finalClaim)
  const matchedEvents = asArray(moneyEvents).filter(event => eventMatchesObligation(event, obligation))
  const funding = summarizeFunding(matchedEvents)

  const confirmedFunding = roundMoney(
    Object.values(funding.confirmed).reduce((total, value) => total + value, 0),
  )
  const unresolvedFunding = roundMoney(
    Object.values(funding.unresolved).reduce((total, value) => total + value, 0),
  )

  const unresolvedGross =
    finalClaim === null ? null : roundMoney(Math.max(0, finalClaim - confirmedFunding))

  const closure = evaluateClosureGate(obligation)
  const netConfirmedLoss = closure.pass && unresolvedGross !== null ? unresolvedGross : null

  let reconciliationStatus = 'Open'
  if (matchedEvents.length > 0) reconciliationStatus = 'In Review'
  if (closure.pass && unresolvedGross === 0) reconciliationStatus = 'Reconciled'
  else if (closure.pass) reconciliationStatus = 'Partially Reconciled'

  return {
    obligationId: obligation.id,
    category: obligation.category ?? null,
    project: obligation.project ?? null,
    finalClaim,
    matchedEventIds: matchedEvents.map(event => event.id),
    confirmedFunding,
    unresolvedFunding,
    unresolvedGross,
    netConfirmedLoss,
    funding,
    closure,
    reconciliationStatus,
    guardrail:
      netConfirmedLoss === null
        ? 'No confirmed loss is produced until every closure field is source-closed and duplicate risk is resolved.'
        : 'Confirmed loss is limited to the source-closed, nonduplicative remainder.',
  }
}

export function findPotentialDuplicateFunding(events) {
  const groups = new Map()

  for (const event of asArray(events)) {
    const amount = normalizeMoney(event?.amount)
    if (amount === null) continue
    const project = normalizeText(event?.project || event?.identityScope)
    const obligation = normalizeText(event?.obligationId || asArray(event?.linkedObligationIds)[0])
    const key = `${project}|${obligation}|${amount.toFixed(2)}`
    const group = groups.get(key) ?? []
    group.push(event)
    groups.set(key, group)
  }

  const candidates = []
  for (const [key, group] of groups) {
    if (group.length < 2) continue
    const roles = new Set(group.map(event => normalizeText(event.accountingRole)))
    const sources = new Set(group.map(event => event.sourceId).filter(Boolean))
    if (roles.size < 2 && sources.size < 2) continue

    candidates.push({
      key,
      amount: normalizeMoney(group[0].amount),
      eventIds: group.map(event => event.id),
      accountingRoles: [...roles],
      sourceIds: [...sources],
      status: 'Candidate Review',
      guardrail: 'Equal amounts are not duplicates without obligation, instrument, project, and final-treatment review.',
    })
  }

  return candidates.sort((a, b) => b.amount - a.amount || a.key.localeCompare(b.key))
}

export function buildFinalBalanceControl(input) {
  const totalCost = normalizeMoney(input?.totalCost)
  const confirmedBudget = normalizeMoney(input?.confirmedBudget) ?? 0
  const confirmedOwnerFunding = normalizeMoney(input?.confirmedOwnerFunding) ?? 0
  const confirmedOtherFunding = normalizeMoney(input?.confirmedOtherFunding) ?? 0
  const confirmedCredits = normalizeMoney(input?.confirmedCredits) ?? 0
  const unresolvedAdjustments = asArray(input?.unresolvedAdjustments)
    .map(normalizeMoney)
    .filter(value => value !== null)

  if (totalCost === null) throw new TypeError('totalCost is required')

  const confirmedSources = roundMoney(
    confirmedBudget + confirmedOwnerFunding + confirmedOtherFunding + confirmedCredits,
  )
  const confirmedNetBalance = roundMoney(totalCost - confirmedSources)
  const unresolvedAdjustmentTotal = roundMoney(
    unresolvedAdjustments.reduce((total, value) => total + value, 0),
  )

  return {
    totalCost,
    confirmedBudget,
    confirmedOwnerFunding,
    confirmedOtherFunding,
    confirmedCredits,
    confirmedSources,
    confirmedNetBalance,
    unresolvedAdjustments,
    unresolvedAdjustmentTotal,
    candidateNetBalance: null,
    guardrail:
      'Unresolved adjustments are displayed separately and are never included in the confirmed net balance.',
  }
}

export function rankAcquisitionRequests(requests) {
  const availabilityScores = {
    high: 15,
    medium: 8,
    low: 3,
    external: 1,
  }
  const costPenalties = {
    low: 0,
    medium: 5,
    high: 12,
  }

  return asArray(requests)
    .map(request => {
      const informationGain = Number(request.informationGain ?? 0)
      const collapseValue = Number(request.collapseValue ?? 0)
      const damagesImpact = Number(request.damagesImpact ?? 0)
      const linkedClaimCount = Number(request.linkedClaimCount ?? 0)
      const availability = availabilityScores[normalizeText(request.availability)] ?? 0
      const costPenalty = costPenalties[normalizeText(request.estimatedCost)] ?? 0
      const priorityScore = roundMoney(
        informationGain * 0.3 +
          collapseValue * 0.3 +
          damagesImpact * 0.25 +
          Math.min(linkedClaimCount, 10) * 1.5 +
          availability -
          costPenalty,
      )

      return { ...request, priorityScore }
    })
    .sort((a, b) => b.priorityScore - a.priorityScore || String(a.id).localeCompare(String(b.id)))
}

export const reconciliationConstants = Object.freeze({
  requiredClosureFields: REQUIRED_CLOSURE_FIELDS,
  fundingRoles: [...FUNDING_ROLES],
  sourceUsableStatuses: [...SOURCE_USABLE],
})
