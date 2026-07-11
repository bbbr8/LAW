# Living Proof-Debt Resolver

## Purpose

The resolver turns missing records into durable, searchable dependencies. A proof debt does not disappear when a search ends. Every later source is compared against every open debt so an unrelated search can produce a candidate resolution, contradiction, split, or expansion event.

The system is deliberately conservative: it may create candidates and propagation events, but it never auto-closes a debt. Native provenance and human review remain required.

## Required search lifecycle

1. Load the case-wide pre-search context.
2. Classify all materially connected lanes.
3. Load open proof debts before building queries.
4. Extract exact identifiers and query exact indexes before semantic retrieval.
5. Expand through canonical aliases while enforcing identity firewalls.
6. Search direct issue terms and dependency-trigger terms.
7. Log a search receipt and coverage rows.
8. Compare every new source with every open debt.
9. Create candidate resolution events at the configured threshold.
10. Propagate each event through dependency edges.
11. Validate the native source and complete human review before changing a debt to Resolved.
12. Invalidate and rerun conclusions affected by the event.

## Core records

### Proof debt

```json
{
  "id": "PDR-009",
  "canonicalRecordNeed": "Bryce and Lot 2 project/customer ledgers",
  "priority": 1,
  "canonicalEntities": ["Bryce/Lot 5", "Lot 2/Loretta", "Suited Construction"],
  "aliases": ["Lot 2 ledger", "Loretta customer ledger"],
  "triggerTerms": ["reimbursement credit", "due to", "due from"],
  "amounts": [103453.21, 63543.47, 70000],
  "dateWindow": { "start": "2018-01-01", "end": "2019-12-31" },
  "expectedDocumentTypes": ["project ledger", "customer subledger"],
  "expectedCustodians": ["Suited", "Central Bank", "accountant"],
  "relatedLanes": ["Lot 2", "owner advances", "final accounting", "damages"],
  "identityKeys": ["105109326", "CB1563"],
  "sourceStatus": "bridge_missing",
  "resolutionStatus": "Open",
  "candidateHits": 0
}
```

### Evidence source

```json
{
  "id": "SRC-001",
  "searchRunId": "SR-001",
  "name": "Lot 2 customer subledger",
  "entities": ["Lot 2", "Suited Construction"],
  "amounts": [63543.47],
  "date": "2018-05-10",
  "documentType": "customer subledger",
  "custodian": "Central Bank",
  "lanes": ["Lot 2", "final accounting"],
  "accountLoanKeys": ["105109326"],
  "sourceStatus": "source_closed",
  "isNative": true,
  "nativeLocator": "Native XLSX / Ledger!A1:Q50"
}
```

### Search receipt

A search receipt should contain at minimum:

- user question;
- pre-search context version;
- lanes loaded;
- source families searched;
- exact and semantic query variants;
- direct and contrary hits;
- proof debts created or updated;
- candidate resolutions;
- identity firewalls checked;
- downstream consequences checked;
- completeness label.

## Candidate scoring

| Criterion | Weight |
|---|---:|
| Canonical entity or verified alias | 25 |
| Exact amount or documented split/aggregate | 25 |
| Date-window overlap | 15 |
| Expected document type or custodian | 10 |
| Lane or claim overlap | 10 |
| Account, loan, address, or project identity key | 10 |
| Native provenance and exact locator | 5 |

Thresholds:

- **0–39:** log only;
- **40–59:** low-confidence candidate;
- **60–79:** create a resolution event and route for review;
- **80–100:** high-priority human validation.

No score authorizes automatic closure.

## API

### Proof debts

- `GET /api/cases/:id/proof-debts`
- `POST /api/cases/:id/proof-debts`
- `PATCH /api/cases/:id/proof-debts/:debtId`

### Search runs

- `GET /api/cases/:id/search-runs`
- `POST /api/cases/:id/search-runs`

A search run requires `preSearchContextVersion` and at least one `lanesLoaded` entry.

### Query planning and exact indexes

- `POST /api/cases/:id/route-query`
- `POST /api/cases/:id/exact-index-entries`
- `GET /api/cases/:id/exact-index-entries`

Exact lookup precedes semantic expansion for money, dates, Bates numbers, checks, invoices, loans, accounts, draws, lots, escrow files, and filenames.

### Dependency edges

- `GET /api/cases/:id/dependencies`
- `POST /api/cases/:id/dependencies`

### Evidence ingestion and candidate matching

- `POST /api/cases/:id/evidence-sources`

The response returns the stored evidence source, all candidate debt matches, resolution events, dependency effects, and `autoResolved: false`.

### Evidence atoms and conclusions

- `POST /api/cases/:id/evidence-atoms`
- `GET /api/cases/:id/evidence-atoms`
- `POST /api/cases/:id/conclusions`
- `GET /api/cases/:id/conclusions`

A conclusion with a broken atom-to-source chain is stored as `Review Required`.

### Invalidation and human review

- `POST /api/cases/:id/reconcile-invalidations`
- `GET /api/cases/:id/invalidations`
- `POST /api/cases/:id/review-decisions`

An accepted review requires native, identity-firewall, and contrary-evidence checks. Review decisions are hash chained.

## Identity firewalls

Alias expansion increases recall but can increase contamination. Maintain explicit barriers for borrower and loan number, property and address, project or lot, bank account, legal entity, vendor account, document version, Bates family, and native source file.

A semantic alias match may create a candidate. It may not cross an identity firewall without exact source support.

## Downstream propagation

Dependency edges identify what changes when a debt is resolved or weakened. A project ledger can affect Lot 2, owner advances, final accounting, and damages. A Draw 3 parent email can affect authorization, lender process, causation, and claimed debt. A vendor credit can affect project application, missing scope, repeated charges, and damages. A later litigation exhibit can affect source status, reliance, discovery chronology, and limitations analysis.

## Drive integration

The Google Drive master dashboard contains:

- `PRE_SEARCH_CONTEXT`
- `PROOF_DEBT_RESOLVER`
- `ALIAS_ENTITY_REGISTRY`
- `SEARCH_RECEIPTS`
- `RESOLUTION_EVENTS`
- `DEPENDENCY_GRAPH`
- `RESOLVER_ANALYTICS`
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

See `docs/EXACT_RETRIEVAL_AND_INVALIDATION.md` for the second-stage controls.
