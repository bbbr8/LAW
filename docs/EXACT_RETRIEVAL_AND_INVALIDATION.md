# Exact Retrieval, Evidence Lineage, and Conclusion Invalidation

## Why this layer exists

A context-aware search can still return the wrong record when exact identifiers are blurred. Amounts, dates, Bates numbers, checks, invoices, loans, accounts, addresses, lots, filenames, and source hashes must be resolved before semantic similarity is allowed to expand the search.

A correct answer can also become stale when a later source changes an open proof debt. The system must therefore preserve a dependency chain from each conclusion to its evidence atoms, sources, context version, search receipt, and unresolved debts.

## Retrieval order

1. Extract exact keys from the question.
2. Query exact amount, date, Bates, check, invoice, loan, account, lot, escrow, filename, hash, and native-source indexes.
3. Apply project, borrower, account, property, entity, and version identity firewalls.
4. Load open proof-debt aliases and trigger terms.
5. Traverse entity and dependency graph neighbors.
6. Run semantic retrieval for language expansion.
7. Rerank by source species, proof tier, exact identity, and meaning impact.
8. Write a search receipt and coverage rows.

Semantic retrieval cannot override an exact-key conflict or identity firewall.

## Evidence atoms

Every material conclusion should cite one or more small, neutral facts with:

- stable atom ID;
- neutral fact text;
- source ID;
- exact page, Bates, row, cell, email, attachment, or bank-item locator;
- source species;
- proof tier and source status;
- event and document dates;
- actors, amount, project, account, and loan;
- candidate claim roles;
- linked proof debts and contradictions;
- observer-time status;
- extraction method;
- hash or revision.

The required backward chain is:

`conclusion -> atom -> data/source object -> exact locator -> native file/hash`

A broken link must remain visible as proof debt.

## Conclusion invalidation

A conclusion becomes `Review Required` when a changed source, atom, proof debt, identity assignment, or context version touches one of its dependencies.

Invalidation does not automatically reverse the conclusion. It records:

- trigger;
- impacted conclusion;
- old and new status;
- reason;
- matched dependencies;
- required rerun;
- replacement conclusion, when available.

Superseded answers remain in history for audit and regression testing.

## Dead-lead and exculpatory memory

The system must remember when a theory has been rejected, materially limited, or preserved only as context. A dead or limited lead may be reopened only when a stated new-evidence trigger is met.

This prevents an unrelated keyword search from reviving an earlier overclaim while preserving the record of why the theory changed.

## Source families and deduplication

Copies and versions are grouped into source families using:

- Drive/file ID;
- SHA-256;
- normalized filename;
- document metadata;
- content similarity;
- revision date;
- native-parent relationship.

Duplicate copies do not count as independent corroboration. Conflicting versions remain separate until the canonical native controller is identified.

## Human review gate

Automated matching creates candidates only. A proof debt can move to `Resolved` only after a reviewer records:

- decision and rationale;
- native source check;
- identity-firewall check;
- contrary-evidence check;
- affected conclusions;
- propagation completion.

Review decisions are chained with SHA-256 hashes so later changes are detectable.

## New API routes

### Query planning

- `POST /api/cases/:id/route-query`

Returns exact keys, exact-index routes, identity firewalls, open-debt routing, semantic expansion, reranking, and completeness requirements.

### Exact index

- `POST /api/cases/:id/exact-index-entries`
- `GET /api/cases/:id/exact-index-entries?type=amount&key=103453.21`

### Evidence atoms

- `POST /api/cases/:id/evidence-atoms`
- `GET /api/cases/:id/evidence-atoms`

### Conclusions and lineage

- `POST /api/cases/:id/conclusions`
- `GET /api/cases/:id/conclusions`

A conclusion with missing or invalid atoms is stored as `Review Required`.

### Invalidation

- `POST /api/cases/:id/reconcile-invalidations`
- `GET /api/cases/:id/invalidations`

### Human review

- `POST /api/cases/:id/review-decisions`

An `accept` decision fails unless the native, identity, and contrary-evidence checks are all true.

## Drive control tabs

The master dashboard now includes:

- `CONTEXT_VERSIONS`
- `EXACT_INDEX_ROUTER`
- `EVIDENCE_ATOMS`
- `ANSWER_LINEAGE`
- `CONCLUSION_INVALIDATION`
- `DEAD_LEAD_EXCULPATORY`
- `SOURCE_FAMILY_DEDUP`
- `HUMAN_REVIEW_QUEUE`
- `COVERAGE_GATE`
- `NEXT_BEST_SEARCH`

These extend the original living-proof-debt tabs without replacing native evidence or human judgment.
