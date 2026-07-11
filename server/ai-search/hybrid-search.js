import crypto from 'crypto'

const DEFAULT_MODEL = process.env.HF_EMBED_MODEL || 'onnx-community/bge-small-en-v1.5-ONNX'
const DEFAULT_DTYPE = process.env.HF_EMBED_DTYPE || 'q8'
const MAX_QUERY_CHARS = 2_000
const MAX_CHUNKS = 200
const MAX_CHUNK_CHARS = 20_000

let extractorPromise
const embeddingCache = new Map()

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function normalizeText(value = '') {
  return String(value)
    .toLowerCase()
    .replace(/,/g, '')
    .replace(/[^a-z0-9$./_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function tokenize(value = '') {
  return normalizeText(value)
    .split(' ')
    .filter(token => token.length > 1)
}

function stableHash(value) {
  return crypto.createHash('sha256').update(value).digest('hex')
}

function numericWeight(token) {
  return /\d/.test(token) ? 2.5 : 1
}

export function isExactLookup(query) {
  const value = String(query || '')
  const hasBates = /\b(?:CB|REV|BFS|BUILDERSFS)[-_ ]?\d{3,}\b/i.test(value)
  const hasLongIdentifier = /\b\d{6,}\b/.test(value)
  const hasPreciseAmount = /\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})\b/.test(value)
  const hasExactDate = /\b(?:\d{1,2}[/-]){2}\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b/.test(value)
  return hasBates || hasLongIdentifier || hasPreciseAmount || hasExactDate
}

function chunkSearchText(chunk) {
  const metadata = chunk?.metadata && typeof chunk.metadata === 'object'
    ? JSON.stringify(chunk.metadata)
    : ''

  return [chunk?.title, chunk?.text, chunk?.source, chunk?.locator, metadata]
    .filter(Boolean)
    .join(' ')
}

export function lexicalScore(query, chunk) {
  const normalizedQuery = normalizeText(query)
  const haystack = normalizeText(chunkSearchText(chunk))
  if (!normalizedQuery || !haystack) return 0

  const queryTokens = [...new Set(tokenize(normalizedQuery))]
  const haystackTokens = new Set(tokenize(haystack))

  let score = haystack.includes(normalizedQuery) ? 6 : 0
  for (const token of queryTokens) {
    if (haystackTokens.has(token)) score += numericWeight(token)
  }

  const coverage = queryTokens.length
    ? queryTokens.filter(token => haystackTokens.has(token)).length / queryTokens.length
    : 0

  return score + coverage * 3
}

export function lexicalRank(query, chunks, limit = 24) {
  return chunks
    .map((chunk, index) => ({ chunk, index, lexical: lexicalScore(query, chunk) }))
    .filter(item => item.lexical > 0)
    .sort((a, b) => b.lexical - a.lexical || a.index - b.index)
    .slice(0, limit)
}

async function getExtractor() {
  if (!extractorPromise) {
    extractorPromise = (async () => {
      const { env, pipeline } = await import('@huggingface/transformers')
      env.cacheDir = process.env.HF_CACHE_DIR || './server/.hf-cache'

      const options = { dtype: DEFAULT_DTYPE }
      try {
        return await pipeline('feature-extraction', DEFAULT_MODEL, options)
      } catch (error) {
        if (DEFAULT_DTYPE === 'fp32') throw error
        return pipeline('feature-extraction', DEFAULT_MODEL, { dtype: 'fp32' })
      }
    })()
  }
  return extractorPromise
}

async function embedTexts(texts) {
  const extractor = await getExtractor()
  const output = await extractor(texts, { pooling: 'mean', normalize: true })
  return output.tolist()
}

async function getEmbeddings(texts) {
  const modelKey = `${DEFAULT_MODEL}:${DEFAULT_DTYPE}`
  const keys = texts.map(text => stableHash(`${modelKey}\n${text}`))
  const missing = []
  const missingIndexes = []

  keys.forEach((key, index) => {
    if (!embeddingCache.has(key)) {
      missing.push(texts[index])
      missingIndexes.push(index)
    }
  })

  if (missing.length) {
    const vectors = await embedTexts(missing)
    vectors.forEach((vector, offset) => {
      embeddingCache.set(keys[missingIndexes[offset]], vector)
    })
  }

  return keys.map(key => embeddingCache.get(key))
}

function dotProduct(left, right) {
  let total = 0
  const length = Math.min(left.length, right.length)
  for (let index = 0; index < length; index += 1) total += left[index] * right[index]
  return total
}

function publicChunk(chunk) {
  return {
    id: chunk.id,
    title: chunk.title,
    text: chunk.text,
    source: chunk.source,
    locator: chunk.locator,
    metadata: chunk.metadata,
  }
}

function validateInput(query, chunks) {
  if (typeof query !== 'string' || !query.trim()) throw new TypeError('query must be a non-empty string')
  if (query.length > MAX_QUERY_CHARS) throw new RangeError(`query exceeds ${MAX_QUERY_CHARS} characters`)
  if (!Array.isArray(chunks)) throw new TypeError('chunks must be an array')
  if (chunks.length > MAX_CHUNKS) throw new RangeError(`chunks exceeds ${MAX_CHUNKS} items`)

  return chunks.map((chunk, index) => {
    if (!chunk || typeof chunk !== 'object') throw new TypeError(`chunks[${index}] must be an object`)
    const text = String(chunk.text || '')
    if (!text.trim()) throw new TypeError(`chunks[${index}].text must be non-empty`)
    if (text.length > MAX_CHUNK_CHARS) throw new RangeError(`chunks[${index}].text exceeds ${MAX_CHUNK_CHARS} characters`)
    return { ...chunk, text }
  })
}

export async function hybridSearch({ query, chunks, limit = 10, mode = 'fast', useSemantic = true }) {
  const cleanChunks = validateInput(query, chunks)
  const exactLookup = isExactLookup(query)
  const safeLimit = clamp(Number(limit) || 10, 1, 50)
  const candidateLimit = mode === 'deep' ? 60 : 24
  const lexicalCandidates = lexicalRank(query, cleanChunks, candidateLimit)

  // When lexical search finds nothing, preserve recall by sampling the first bounded candidates.
  const candidates = lexicalCandidates.length
    ? lexicalCandidates
    : cleanChunks.slice(0, candidateLimit).map((chunk, index) => ({ chunk, index, lexical: 0 }))

  const maxLexical = Math.max(...candidates.map(item => item.lexical), 1)
  const semanticAllowed = useSemantic && !exactLookup && process.env.HF_SEARCH_ENABLED !== 'false'
  let semanticStatus = semanticAllowed ? 'used' : exactLookup ? 'skipped_exact_lookup' : 'disabled'
  let queryVector
  let candidateVectors

  if (semanticAllowed) {
    try {
      const texts = [query, ...candidates.map(item => chunkSearchText(item.chunk))]
      const vectors = await getEmbeddings(texts)
      queryVector = vectors[0]
      candidateVectors = vectors.slice(1)
    } catch (error) {
      semanticStatus = 'lexical_fallback'
    }
  }

  const lexicalWeight = semanticStatus === 'used' ? (mode === 'deep' ? 0.35 : 0.45) : 1
  const semanticWeight = semanticStatus === 'used' ? 1 - lexicalWeight : 0

  const results = candidates
    .map((item, index) => {
      const lexical = item.lexical / maxLexical
      const semantic = semanticStatus === 'used'
        ? clamp((dotProduct(queryVector, candidateVectors[index]) + 1) / 2, 0, 1)
        : 0
      const score = lexical * lexicalWeight + semantic * semanticWeight

      return {
        ...publicChunk(item.chunk),
        score: Number(score.toFixed(6)),
        match: {
          lexical: Number(lexical.toFixed(6)),
          semantic: Number(semantic.toFixed(6)),
        },
      }
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, safeLimit)

  return {
    query,
    mode,
    exactLookup,
    semantic: {
      status: semanticStatus,
      model: semanticStatus === 'used' ? DEFAULT_MODEL : null,
      localInference: true,
    },
    candidateCount: candidates.length,
    results,
  }
}
