const STATUSES = Object.freeze({
  NEEDS_SOURCE: 'AI New Finding — Needs Source Anchors',
  QUESTIONED: 'AI New Finding — Questioned',
  WORTH_PURSUING: 'AI New Finding — Worth Pursuing',
  SUPPORTED: 'AI New Finding — Supported, Not Confirmed',
  CONFIRMED: 'Human-Confirmed Finding',
  REJECTED: 'Rejected / Superseded',
})

function unique(values = []) {
  return [...new Set(values.filter(value => value !== undefined && value !== null && String(value).trim() !== ''))]
}

function normalizedScore(value) {
  const score = Number(value ?? 0)
  if (!Number.isFinite(score)) return 0
  return Math.min(1, Math.max(0, score))
}

function defaultQuestions({ sourceComplete, missingAtomIds, alternatives }) {
  const questions = [
    'What exact native record, page, row, or transaction supports this finding?',
    'What evidence would disprove or materially limit this finding?',
    'Does the finding survive the person, property, loan, account, amount-stage, and date firewalls?',
  ]
  if (!sourceComplete) questions.push('Which missing bridge record is required before this can be treated as supported?')
  if (missingAtomIds.length) questions.push(`Why are these evidence atoms missing or unresolved: ${missingAtomIds.join(', ')}?`)
  if (!alternatives.length) questions.push('What innocent or competing explanation should be tested?')
  return questions
}

export function buildAiFinding(input = {}, atoms = []) {
  if (!String(input.findingText || '').trim()) throw new TypeError('findingText is required')

  const confidenceScore = normalizedScore(input.confidenceScore)
  const supportingAtomIds = unique(input.supportingAtomIds)
  const atomMap = new Map(atoms.map(atom => [atom.id, atom]))
  const linkedAtoms = supportingAtomIds.map(id => atomMap.get(id)).filter(Boolean)
  const missingAtomIds = supportingAtomIds.filter(id => !atomMap.has(id))
  const sourceAnchors = unique([
    ...(Array.isArray(input.sourceAnchors) ? input.sourceAnchors : []),
    ...linkedAtoms.map(atom => atom.nativeLocator),
  ])
  const alternativeExplanations = unique(input.alternativeExplanations)
  const missingBridgeRecords = unique(input.missingBridgeRecords)
  const sourceComplete = supportingAtomIds.length > 0 && missingAtomIds.length === 0 && sourceAnchors.length > 0
  const worthPursuing = input.worthPursuing === true || (
    confidenceScore >= 0.65 && (supportingAtomIds.length > 0 || sourceAnchors.length > 0)
  )
  const reviewQuestions = unique(
    Array.isArray(input.reviewQuestions) && input.reviewQuestions.length
      ? input.reviewQuestions
      : defaultQuestions({ sourceComplete, missingAtomIds, alternatives: alternativeExplanations }),
  )

  let currentStatus = STATUSES.QUESTIONED
  if (!sourceComplete) currentStatus = STATUSES.NEEDS_SOURCE
  else if (worthPursuing) currentStatus = STATUSES.WORTH_PURSUING

  return {
    ...input,
    originType: 'AI_ASSISTED',
    displayLabel: 'AI New Finding',
    currentStatus,
    reviewState: 'Questioned',
    confidenceScore,
    worthPursuing,
    supportingAtomIds,
    sourceAnchors,
    sourceComplete,
    missingAtomIds,
    alternativeExplanations,
    missingBridgeRecords,
    reviewQuestions,
    autoConfirmed: false,
    promotionRule: 'Human confirmation requires source-complete lineage and all required review checks.',
  }
}

export function reviewAiFinding(finding, review = {}) {
  if (!finding?.id) throw new TypeError('finding is required')
  if (!String(review.reviewer || '').trim()) throw new TypeError('reviewer is required')

  const decision = String(review.decision || '').toLowerCase()
  const allowed = new Set(['pursue', 'support', 'confirm', 'reject'])
  if (!allowed.has(decision)) throw new TypeError('decision must be pursue, support, confirm, or reject')

  const checks = review.checks || {}
  let currentStatus
  if (decision === 'pursue') currentStatus = STATUSES.WORTH_PURSUING
  if (decision === 'reject') currentStatus = STATUSES.REJECTED
  if (decision === 'support') {
    if (!finding.sourceComplete || checks.nativeSourceChecked !== true) {
      throw new TypeError('support requires source-complete lineage and nativeSourceChecked=true')
    }
    currentStatus = STATUSES.SUPPORTED
  }
  if (decision === 'confirm') {
    const requiredChecks = [
      'nativeSourceChecked',
      'identityFirewallChecked',
      'contraryEvidenceChecked',
      'questionsResolved',
    ]
    const missingChecks = requiredChecks.filter(key => checks[key] !== true)
    if (!finding.sourceComplete || missingChecks.length) {
      throw new TypeError(`confirmation requires source-complete lineage and checks: ${requiredChecks.join(', ')}`)
    }
    currentStatus = STATUSES.CONFIRMED
  }

  const reviewEvent = {
    reviewedAt: new Date().toISOString(),
    reviewer: review.reviewer,
    decision,
    rationale: review.rationale || '',
    checks,
    priorStatus: finding.currentStatus,
    newStatus: currentStatus,
  }

  return {
    ...finding,
    originType: 'AI_ASSISTED',
    displayLabel: finding.displayLabel || 'AI New Finding',
    currentStatus,
    reviewState: decision === 'confirm' ? 'Human Confirmed' : 'Questioned',
    autoConfirmed: false,
    updatedAt: reviewEvent.reviewedAt,
    reviewHistory: [...(Array.isArray(finding.reviewHistory) ? finding.reviewHistory : []), reviewEvent],
  }
}

export { STATUSES as AI_FINDING_STATUSES }
