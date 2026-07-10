import crypto from 'crypto'

function asArray(value) {
  if (Array.isArray(value)) return value.filter(Boolean)
  if (value === null || value === undefined || value === '') return []
  return [value]
}

function normalized(value) {
  return String(value ?? '').trim().toLowerCase()
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map(key => [key, stableValue(value[key])]),
    )
  }
  return value
}

export function validateEvidenceAtom(atom) {
  const errors = []
  if (!atom?.id) errors.push('id is required')
  if (!atom?.neutralFact) errors.push('neutralFact is required')
  if (!atom?.sourceId) errors.push('sourceId is required')
  if (!atom?.exactLocator) errors.push('exactLocator is required')
  if (!atom?.sourceSpecies) errors.push('sourceSpecies is required')
  if (!atom?.proofTier) errors.push('proofTier is required')
  if (!atom?.sourceStatus) errors.push('sourceStatus is required')

  return {
    valid: errors.length === 0,
    errors,
  }
}

export function traceConclusion(conclusion, atoms) {
  const atomsById = new Map(asArray(atoms).map(atom => [atom.id, atom]))
  const requestedAtomIds = asArray(conclusion?.supportingAtomIds)
  const resolvedAtoms = requestedAtomIds.map(id => atomsById.get(id)).filter(Boolean)
  const missingAtomIds = requestedAtomIds.filter(id => !atomsById.has(id))
  const lineageBreaks = []

  for (const atom of resolvedAtoms) {
    const validation = validateEvidenceAtom(atom)
    if (!validation.valid) {
      lineageBreaks.push({ atomId: atom.id, errors: validation.errors })
    }
  }

  if (requestedAtomIds.length === 0) {
    lineageBreaks.push({ conclusionId: conclusion?.id, errors: ['No supporting atoms'] })
  }
  if (missingAtomIds.length > 0) {
    lineageBreaks.push({ conclusionId: conclusion?.id, errors: [`Missing atoms: ${missingAtomIds.join(', ')}`] })
  }

  return {
    conclusionId: conclusion?.id,
    requestedAtomIds,
    resolvedAtoms,
    missingAtomIds,
    openProofDebts: asArray(conclusion?.openProofDebts),
    sourceComplete: lineageBreaks.length === 0,
    lineageBreaks,
  }
}

export function findConclusionInvalidations(trigger, conclusions) {
  const triggerIds = new Set([
    trigger?.id,
    trigger?.debtId,
    trigger?.evidenceId,
    trigger?.sourceId,
    ...asArray(trigger?.affectedIds),
  ].filter(Boolean))

  const invalidations = []
  for (const conclusion of asArray(conclusions)) {
    const dependencies = new Set([
      ...asArray(conclusion?.supportingAtomIds),
      ...asArray(conclusion?.supportingSourceIds),
      ...asArray(conclusion?.openProofDebts),
      ...asArray(conclusion?.dependencyIds),
    ])

    const matches = [...triggerIds].filter(id => dependencies.has(id))
    if (matches.length === 0) continue

    invalidations.push({
      id: `INV-${crypto.randomUUID()}`,
      triggerId: trigger.id ?? null,
      triggerType: trigger.eventType ?? trigger.type ?? 'source_or_debt_change',
      impactedConclusionId: conclusion.id,
      impactType: trigger.impactType ?? 'conditional_re_review',
      oldStatus: conclusion.currentStatus ?? 'Active',
      newStatus: 'Review Required',
      reason: trigger.reason ?? `Dependency changed: ${matches.join(', ')}`,
      matchedDependencies: matches,
      requiredRerun: conclusion.requiredRerun ?? 'Rerun original question with current context and sources.',
      createdAt: new Date().toISOString(),
    })
  }
  return invalidations
}

const ALLOWED_DECISIONS = new Set(['accept', 'partial', 'reject', 'duplicate', 'supersede'])

export function applyHumanReview({ debt, event, decision, reviewer, checks = {}, rationale }) {
  const normalizedDecision = normalized(decision)
  if (!ALLOWED_DECISIONS.has(normalizedDecision)) {
    throw new TypeError(`Unsupported review decision: ${decision}`)
  }
  if (!reviewer) throw new TypeError('reviewer is required')
  if (!rationale) throw new TypeError('rationale is required')

  const requiredChecks = ['nativeChecked', 'identityFirewallChecked', 'contraryEvidenceChecked']
  const missingChecks = requiredChecks.filter(check => checks[check] !== true)
  if (normalizedDecision === 'accept' && missingChecks.length > 0) {
    throw new TypeError(`Accept requires checks: ${missingChecks.join(', ')}`)
  }

  let resolutionStatus = debt?.resolutionStatus ?? 'Open'
  if (normalizedDecision === 'accept') resolutionStatus = 'Resolved'
  if (normalizedDecision === 'partial') resolutionStatus = 'Partially Resolved'
  if (normalizedDecision === 'reject') resolutionStatus = 'Open'
  if (normalizedDecision === 'duplicate') resolutionStatus = debt?.resolutionStatus ?? 'Open'
  if (normalizedDecision === 'supersede') resolutionStatus = 'Superseded'

  const reviewedAt = new Date().toISOString()
  return {
    reviewDecision: {
      id: `HR-${crypto.randomUUID()}`,
      debtId: debt?.id ?? event?.debtId ?? null,
      eventId: event?.id ?? null,
      evidenceId: event?.evidenceId ?? null,
      decision: normalizedDecision,
      reviewer,
      rationale,
      checks,
      reviewedAt,
    },
    updatedDebt: debt
      ? {
          ...debt,
          resolutionStatus,
          lastReviewedAt: reviewedAt,
          lastReviewDecision: normalizedDecision,
          lastReviewer: reviewer,
          resolutionSource: normalizedDecision === 'accept' ? event?.evidenceId ?? debt.resolutionSource : debt.resolutionSource,
          updatedAt: reviewedAt,
        }
      : null,
  }
}

export function createAuditChainEvent(event, previousHash = '') {
  const canonical = JSON.stringify(stableValue({ previousHash, event }))
  const eventHash = crypto.createHash('sha256').update(canonical).digest('hex')
  return {
    ...event,
    previousHash: previousHash || null,
    eventHash,
  }
}
