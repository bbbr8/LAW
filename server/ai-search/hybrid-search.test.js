import test from 'node:test'
import assert from 'node:assert/strict'
import { hybridSearch, isExactLookup, lexicalRank } from './hybrid-search.js'

test('detects exact legal/accounting lookups', () => {
  assert.equal(isExactLookup('Find CB00406'), true)
  assert.equal(isExactLookup('loan 600000673'), true)
  assert.equal(isExactLookup('show the $22,089.00 draw item'), true)
  assert.equal(isExactLookup('explain the money pattern'), false)
})

test('lexical ranking favors exact source identifiers', () => {
  const ranked = lexicalRank('CB00406 plumbing', [
    { id: 'a', text: 'General plumbing discussion' },
    { id: 'b', text: 'CB00406 Jim Miller plumbing invoice' },
  ])
  assert.equal(ranked[0].chunk.id, 'b')
})

test('hybrid search remains deterministic when the model is bypassed', async () => {
  const result = await hybridSearch({
    query: 'Fortis wire 275813.66',
    chunks: [
      { id: 'one', text: 'Fortis wire was $275,813.66', source: 'bank statement', locator: 'p. 4' },
      { id: 'two', text: 'Unrelated construction note' },
    ],
    useSemantic: false,
  })

  assert.equal(result.semantic.status, 'skipped_exact_lookup')
  assert.equal(result.results[0].id, 'one')
  assert.equal(result.results[0].locator, 'p. 4')
})
