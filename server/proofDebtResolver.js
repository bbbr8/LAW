const DEFAULT_WEIGHTS = Object.freeze({
  entityOrAlias: 25,
  amount: 25,
  dateWindow: 15,
  documentOrCustodian: 10,
  lane: 10,
  identityKey: 10,
  nativeProvenance: 5,
})

const DEFAULT_THRESHOLDS = Object.freeze({
  logOnly: 0,
  lowConfidence: 40,
  resolutionEvent: 60,
  highPriorityReview: 80,
})

export function normalizeText(value) {
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

  const cleaned = String(value).replace(/[$,\s]/g, '')
  const parsed = Number(cleaned)
  return Number.isFinite(parsed) ? Math.round(parsed * 100) / 100 : null
}

function asArray(value) {
  if (Array.isArray(value)) return value.filter(v => v !== null && v !== undefined && v !== '')
  if (value === null || value === undefined || value === '') return []
  return [value]
}

function normalizedSet(values) {
  return new Set(asArray(values).map(normalizeText).filter(Boolean))
}

function evidenceText(evidence) {
  return normalizeText([
    evidence?.name,
    evidence?.title,
    evidence?.text,
    evidence?.snippet,
    evidence?.documentType,
    evidence?.custodian,
    evidence?.nativeLocator,
    ...asArray(evidence?.entities),
    ...asArray(evidence?.aliases),
    ...asArray(evidence?.lanes),
    ...asArray(evidence?.accountLoanKeys),
  ].join(' '))
}

function anyTermMatch(terms, haystack) {
  const normalizedTerms = normalizedSet(terms)
  for (const term of normalizedTerms) {
    if (term.length >= 3 && haystack.includes(term)) return true
  }
  return false
}

function intersection(left, right) {
  const rightSet = normalizedSet(right)
  return asArray(left)
    .map(normalizeText)
    .filter(value => value && rightSet.has(value))
}

function amountMatch(debtAmounts, evidenceAmounts, tolerance = 0.01) {
  const debt = asArray(debtAmounts).map(normalizeMoney).filter(v => v !== null)
  const evidence = asArray(evidenceAmounts).map(normalizeMoney).filter(v => v !== null)
  const matches = []

  for (const expected of debt) {
    for (const actual of evidence) {
      if (Math.abs(expected - actual) <= tolerance) {
        matches.push({ expected, actual, type: 'exact' })
      }
    }
  }

  if (matches.length > 0) return matches

  // Split/aggregate support: a later source may contain a component or a total.
  for (const expected of debt) {
    if (evidence.length > 1) {
      const sum = Math.round(evidence.reduce((total, value) => total + value, 0) * 100) / 100
      if (Math.abs(expected - sum) <= tolerance) {
        matches.push({ expected, actual: sum, type: 'aggregate' })
      }
    }
  }

  return matches
}

function parseDate(value) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function dateWindowMatch(window, evidenceDate) {
  if (!window || !evidenceDate) return false
  const date = parseDate(evidenceDate)
  if (!date) return false

  const start = parseDate(window.start)
  const end = parseDate(window.end)
  if (start && date < start) return false
  if (end && date > end) return false
  return Boolean(start || end)
}

function hasNativeProvenance(evidence) {
  const nativeStatuses = new Set(['source_closed', 'native', 'tier_a', 'official'])
  return Boolean(
    evidence?.nativeLocator &&
    (nativeStatuses.has(normalizeText(evidence?.sourceStatus)) || evidence?.isNative === true)
  )
}

export function scoreEvidenceAgainstDebt(debt, evidence, options = {}) {
  const weights = { ...DEFAULT_WEIGHTS, ...(options.weights ?? {}) }
  const haystack = evidenceText(evidence)
  const reasons = []
  let score = 0

  const entityTerms = [
    ...asArray(debt?.canonicalEntities),
    ...asArray(debt?.aliases),
    ...asArray(debt?.triggerTerms),
  ]
  const directEntityMatches = intersection(entityTerms, [
    ...asArray(evidence?.entities),
    ...asArray(evidence?.aliases),
  ])
  if (directEntityMatches.length > 0 || anyTermMatch(entityTerms, haystack)) {
    score += weights.entityOrAlias
    reasons.push({ criterion: 'entityOrAlias', weight: weights.entityOrAlias, matches: directEntityMatches })
  }

  const moneyMatches = amountMatch(debt?.amounts, evidence?.amounts, options.amountTolerance)
  if (moneyMatches.length > 0) {
    score += weights.amount
    reasons.push({ criterion: 'amount', weight: weights.amount, matches: moneyMatches })
  }

  if (dateWindowMatch(debt?.dateWindow, evidence?.date)) {
    score += weights.dateWindow
    reasons.push({ criterion: 'dateWindow', weight: weights.dateWindow, matches: [evidence.date] })
  }

  const documentOrCustodianTerms = [
    ...asArray(debt?.expectedDocumentTypes),
    ...asArray(debt?.expectedCustodians),
  ]
  if (anyTermMatch(documentOrCustodianTerms, haystack)) {
    score += weights.documentOrCustodian
    reasons.push({
      criterion: 'documentOrCustodian',
      weight: weights.documentOrCustodian,
      matches: documentOrCustodianTerms.filter(term => haystack.includes(normalizeText(term))),
    })
  }

  const laneMatches = intersection(debt?.relatedLanes, evidence?.lanes)
  if (laneMatches.length > 0 || anyTermMatch(debt?.relatedLanes, haystack)) {
    score += weights.lane
    reasons.push({ criterion: 'lane', weight: weights.lane, matches: laneMatches })
  }

  const identityMatches = intersection(debt?.identityKeys, evidence?.accountLoanKeys)
  if (identityMatches.length > 0 || anyTermMatch(debt?.identityKeys, haystack)) {
    score += weights.identityKey
    reasons.push({ criterion: 'identityKey', weight: weights.identityKey, matches: identityMatches })
  }

  if (hasNativeProvenance(evidence)) {
    score += weights.nativeProvenance
    reasons.push({
      criterion: 'nativeProvenance',
      weight: weights.nativeProvenance,
      matches: [evidence.nativeLocator],
    })
  }

  return {
    debtId: debt?.id,
    evidenceId: evidence?.id,
    score,
    reasons,
    threshold: classifyScore(score, options.thresholds),
  }
}

export function classifyScore(score, thresholds = {}) {
  const resolved = { ...DEFAULT_THRESHOLDS, ...thresholds }
  if (score >= resolved.highPriorityReview) return 'high_priority_human_validation'
  if (score >= resolved.resolutionEvent) return 'create_resolution_event'
  if (score >= resolved.lowConfidence) return 'low_confidence_candidate'
  return 'log_only'
}

export function findResolutionCandidates(openDebts, evidence, options = {}) {
  const minimumScore = options.minimumScore ?? DEFAULT_THRESHOLDS.lowConfidence
  return asArray(openDebts)
    .filter(debt => normalizeText(debt?.resolutionStatus) !== 'resolved')
    .map(debt => scoreEvidenceAgainstDebt(debt, evidence, options))
    .filter(result => result.score >= minimumScore)
    .sort((a, b) => b.score - a.score || String(a.debtId).localeCompare(String(b.debtId)))
}

export function buildResolutionEvent(debt, evidence, candidate, searchRunId) {
  if (!debt?.id) throw new TypeError('debt.id is required')
  if (!evidence?.id) throw new TypeError('evidence.id is required')

  return {
    id: cryptoSafeId('resolution'),
    debtId: debt.id,
    evidenceId: evidence.id,
    searchRunId: searchRunId ?? null,
    eventType: candidate.threshold,
    matchScore: candidate.score,
    matchReasons: candidate.reasons,
    oldStatus: debt.resolutionStatus ?? 'Open',
    newStatus: candidate.score >= DEFAULT_THRESHOLDS.resolutionEvent ? 'Candidate Review' : 'Open',
    nativeLocator: evidence.nativeLocator ?? null,
    humanValidation: 'Pending',
    createdAt: new Date().toISOString(),
  }
}

export function propagateResolutionEvent(event, dependencyEdges) {
  const affected = []
  for (const edge of asArray(dependencyEdges)) {
    if (edge?.fromId !== event.debtId && edge?.fromId !== event.evidenceId) continue
    affected.push({
      edgeId: edge.id,
      relation: edge.relation,
      targetId: edge.toId,
      propagationRule: edge.propagationRule,
      sourceStatus: edge.sourceStatus,
      eventId: event.id,
    })
  }
  return affected
}

function cryptoSafeId(prefix) {
  const random = globalThis.crypto?.randomUUID?.()
  if (random) return `${prefix}-${random}`
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export const resolverDefaults = Object.freeze({
  weights: DEFAULT_WEIGHTS,
  thresholds: DEFAULT_THRESHOLDS,
})
