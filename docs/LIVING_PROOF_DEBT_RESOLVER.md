# Living Proof-Debt Resolver

## Purpose

The resolver turns missing records into durable, searchable dependencies. A proof debt does not disappear when a search ends. Every later source is compared against every open debt so an unrelated search can produce a candidate resolution, contradiction, split, or expansion event.

The system is deliberately conservative: it may create candidates and propagation events, but it never auto-closes a debt. Native provenance and human review remain required.

## Required search lifecycle

1. Load the case-wide pre-search context.
2. Classify all materially connected lanes.
3. Load open proof debts before building queries.
4. Expand through canonical aliases while enforcing identity firewalls.
5. Search direct issue terms and dependency-trigger terms.
6. Log a search receipt.
7. Compare every new source with every open debt.
8. Create candidate resolution events at the configured threshold.
9. Propagate each event through dependency edges.
10. Validate the native source before changing a debt to Resolved.
11. Rerun any conclusions affected by the event.

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
- query variants;
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

### Create or list proof debts

- `GET /api/cases/:id/proof-debts`
- `POST /api/cases/:id/proof-debts`
- `PATCH /api/cases/:id/proof-debts/:debtId`

### Log search runs

- `GET /api/cases/:id/search-runs`
- `POST /api/cases/:id/search-runs`

A search run requires `preSearchContextVersion` and at least one `lanesLoaded` entry.

### Create dependency edges

- `GET /api/cases/:id/dependencies`
- `POST /api/cases/:id/dependencies`

### Ingest evidence and evaluate all open debts

- `POST /api/cases/:id/evidence-sources`

The response returns:

- the stored evidence source;
- all candidate proof-debt matches;
- resolution events;
- propagated dependency effects;
- `autoResolved: false` as an explicit guardrail.

### Read resolution history

- `GET /api/cases/:id/resolution-events`

## Identity firewalls

Alias expansion increases recall but can increase contamination. Maintain explicit barriers for:

- borrower and loan number;
- property and address;
- project or lot;
- bank account;
- legal entity;
- vendor account;
- document version;
- Bates family and native source file.

A semantic alias match may create a candidate. It may not cross an identity firewall without exact source support.

## Downstream propagation

Dependency edges should identify what changes when a debt is resolved or weakened. Examples:

- a project ledger affects Lot 2, owner advances, final accounting, and damages;
- a Draw 3 parent email affects authorization, lender process, causation, and claimed debt;
- a vendor credit memo affects project application, missing scope, duplicate charges, and damages;
- a later litigation exhibit affects source status, reliance, discovery chronology, and limitations analysis.

## Drive integration

The Google Drive master dashboard contains the corresponding control tabs:

- `PRE_SEARCH_CONTEXT`
- `PROOF_DEBT_RESOLVER`
- `ALIAS_ENTITY_REGISTRY`
- `SEARCH_RECEIPTS`
- `RESOLUTION_EVENTS`
- `DEPENDENCY_GRAPH`
- `RESOLVER_ANALYTICS`

The code and Drive schema should use stable IDs so events can be synchronized without relying on row position.
