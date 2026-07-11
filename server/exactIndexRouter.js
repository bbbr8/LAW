const MONEY_PATTERN = /(?:\$\s*)?\b\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\b/g
const ISO_DATE_PATTERN = /\b(?:19|20)\d{2}-\d{2}-\d{2}\b/g
const US_DATE_PATTERN = /\b(?:0?[1-9]|1[0-2])[\/-](?:0?[1-9]|[12]\d|3[01])[\/-](?:19|20)?\d{2}\b/g
const FILE_PATTERN = /\b[^\s/\\]+\.(?:pdf|xlsx?|csv|jsonl?|ya?ml|eml|msg|docx?|pptx?|txt|md|html?)\b/gi
const BATES_PATTERN = /\b[A-Z][A-Z0-9 _-]{1,24}\s*0{0,6}\d{2,8}\b/g

const LABEL_PATTERNS = Object.freeze({
  check: /\b(?:check|chk)\s*(?:#|no\.?|number)?\s*([A-Z0-9-]{2,20})\b/gi,
  invoice: /\b(?:invoice|inv)\s*(?:#|no\.?|number)?\s*([A-Z0-9-]{2,30})\b/gi,
  loan: /\b(?:loan|loan no\.?|loan number)\s*#?\s*([0-9]{5,20})\b/gi,
  account: /\b(?:account|acct)\s*(?:#|no\.?|ending)?\s*([A-Z0-9-]{3,24})\b/gi,
  draw: /\b(?:draw)\s*(?:#|no\.?|number)?\s*([0-9]{1,3})\b/gi,
  escrow: /\b(?:escrow|file)\s*(?:#|no\.?|number)?\s*([A-Z0-9-]{3,24})\b/gi,
  lot: /\b(?:lot)\s*(?:#|no\.?|number)?\s*([A-Z0-9-]{1,12})\b/gi,
})

function unique(values) {
  return [...new Set(values.filter(Boolean))]
}

function collectMatches(pattern, text, group = 0) {
  const values = []
  pattern.lastIndex = 0
  let match
  while ((match = pattern.exec(text)) !== null) {
    values.push(match[group])
    if (match.index === pattern.lastIndex) pattern.lastIndex += 1
  }
  return values
}

export function normalizeExactKey(type, rawValue) {
  const raw = String(rawValue ?? '').trim()
  if (!raw) return ''

  if (type === 'amount') {
    const parsed = Number(raw.replace(/[$,\s]/g, ''))
    return Number.isFinite(parsed) ? parsed.toFixed(2) : ''
  }

  if (type === 'date') {
    const date = new Date(raw)
    return Number.isNaN(date.getTime()) ? raw.toLowerCase() : date.toISOString().slice(0, 10)
  }

  if (type === 'file') return raw.toLowerCase()
  if (type === 'bates') return raw.toUpperCase().replace(/[\s_-]+/g, ' ').trim()

  return raw.toUpperCase().replace(/[^A-Z0-9.-]+/g, '')
}

export function extractExactKeys(query) {
  const text = String(query ?? '')
  const keys = []

  for (const value of collectMatches(MONEY_PATTERN, text)) {
    const normalized = normalizeExactKey('amount', value)
    if (!normalized) continue
    // Prevent small integers and years from being treated as money unless marked with $ or cents/comma.
    if (!value.includes('$') && !value.includes(',') && !value.includes('.')) continue
    keys.push({ type: 'amount', raw: value, normalized })
  }

  for (const value of [
    ...collectMatches(ISO_DATE_PATTERN, text),
    ...collectMatches(US_DATE_PATTERN, text),
  ]) {
    keys.push({ type: 'date', raw: value, normalized: normalizeExactKey('date', value) })
  }

  for (const value of collectMatches(FILE_PATTERN, text)) {
    keys.push({ type: 'file', raw: value, normalized: normalizeExactKey('file', value) })
  }

  for (const value of collectMatches(BATES_PATTERN, text)) {
    if (!/\d{2,}/.test(value)) continue
    keys.push({ type: 'bates', raw: value, normalized: normalizeExactKey('bates', value) })
  }

  for (const [type, pattern] of Object.entries(LABEL_PATTERNS)) {
    for (const value of collectMatches(pattern, text, 1)) {
      keys.push({ type, raw: value, normalized: normalizeExactKey(type, value) })
    }
  }

  const seen = new Set()
  return keys.filter(key => {
    const signature = `${key.type}:${key.normalized}`
    if (!key.normalized || seen.has(signature)) return false
    seen.add(signature)
    return true
  })
}

export function buildExactRoutePlan(query, options = {}) {
  const exactKeys = extractExactKeys(query)
  const aliasTerms = unique(options.aliasTerms ?? [])
  const identityFirewalls = unique(options.identityFirewalls ?? [])
  const openDebtTerms = unique(options.openDebtTerms ?? [])

  const exactRoutes = exactKeys.map(key => ({
    stage: 1,
    engine: `${key.type}_index`,
    key: key.normalized,
    raw: key.raw,
    required: true,
  }))

  return {
    query: String(query ?? ''),
    exactKeys,
    identityFirewalls,
    routeOrder: [
      ...exactRoutes,
      {
        stage: 2,
        engine: 'file_hash_native_source_indexes',
        key: exactKeys.map(key => key.normalized),
        required: exactKeys.length > 0,
      },
      {
        stage: 3,
        engine: 'entity_alias_and_graph_router',
        key: aliasTerms,
        required: aliasTerms.length > 0,
      },
      {
        stage: 4,
        engine: 'proof_debt_dependency_router',
        key: openDebtTerms,
        required: openDebtTerms.length > 0,
      },
      {
        stage: 5,
        engine: 'semantic_retrieval',
        key: String(query ?? ''),
        required: true,
        guardrail: 'Semantic retrieval expands context but cannot override exact-key or identity-firewall results.',
      },
      {
        stage: 6,
        engine: 'source_tier_reranker',
        key: null,
        required: true,
      },
    ],
    collisionWarnings: buildCollisionWarnings(exactKeys),
    completenessRequirements: [
      'exact indexes queried',
      'identity firewalls checked',
      'open proof debts checked',
      'semantic expansion completed',
      'source-tier reranking completed',
      'search receipt written',
    ],
  }
}

function buildCollisionWarnings(keys) {
  const warnings = []
  const amountKeys = keys.filter(key => key.type === 'amount')
  for (const key of amountKeys) {
    const value = Number(key.normalized)
    if (Number.isFinite(value) && Number.isInteger(value)) {
      warnings.push(`Rounded amount ${key.normalized} requires date, account, project, or entity confirmation.`)
    }
  }

  const identityTypes = new Set(['loan', 'account', 'escrow', 'lot', 'check', 'invoice'])
  for (const key of keys) {
    if (identityTypes.has(key.type)) {
      warnings.push(`${key.type} ${key.normalized} must remain inside its verified identity scope.`)
    }
  }
  return unique(warnings)
}
