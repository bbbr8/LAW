# Case Profile and Evidence-Control App

A React + Express case-management application with efficient local Hugging Face hybrid search, living proof-debt resolution, exact-first retrieval, evidence lineage, AI New Finding review, conclusion invalidation, native-accounting reconciliation services, a source-bound connector communication bus, and versioned first-person statement/recollection mini-learning.

## Setup and run

```bash
npm install
npm run dev
```

The command starts:

- Primary Express API on `http://localhost:3001`
- Accounting reconciliation API on `http://localhost:3002`
- Vite client on `http://localhost:5173`

Run tests with:

```bash
npm test
```

## Search and evidence controls

- Exact Bates numbers, amounts, dates, checks, invoices, loans, accounts, lots, filenames, and other identifiers route before semantic search.
- Conceptual searches use bounded lexical-plus-semantic ranking through local Hugging Face embeddings.
- If the embedding model is unavailable, deterministic lexical ranking remains available.
- Source IDs, native locators, evidence status, and identity firewalls remain attached to results.
- Search similarity never proves identity, payment lineage, intent, falsity, or enterprise membership.

## Living proof-debt and lineage controls

- Persistent proof debts and search receipts
- Candidate matching across all open proof debts
- Dependency propagation and resolution events
- Evidence atoms with exact source lineage
- Conclusion dependency tracking and stale-answer invalidation
- Dead-lead and exculpatory memory
- Source-family deduplication and version control
- Human review gate before proof-debt closure
- Hash-chained review decisions

## AI New Finding lifecycle

An AI conclusion that appears accurate or worth pursuing is preserved as an **AI New Finding**, not discarded as generic AI output and not promoted directly to fact.

Every AI New Finding records:

- the proposed finding;
- confidence and why it is worth pursuing;
- supporting evidence atoms and exact source anchors;
- questions that must be answered;
- competing or innocent explanations;
- missing bridge records;
- next investigative actions;
- human review history.

Possible statuses include:

- `AI New Finding — Needs Source Anchors`
- `AI New Finding — Questioned`
- `AI New Finding — Worth Pursuing`
- `AI New Finding — Supported, Not Confirmed`
- `Human-Confirmed Finding`
- `Rejected / Superseded`

Human confirmation requires source-complete lineage plus native-source, identity-firewall, contrary-evidence, and question-resolution checks. The AI origin remains visible after confirmation.

## Accounting controls

- Money-event ledger and accounting-obligation persistence
- Obligation → funding → reimbursement → customer-credit → final-treatment reconciliation
- Duplicate-funding candidate detection without automatic duplicate findings
- Final-balance controls that exclude unresolved adjustments from confirmed net calculations
- Ranked native-record acquisition requests

The system never treats a match score, equal amount, aggregate balance, derived report, AI finding, or unresolved adjustment as proof by itself. Native provenance and recorded human review remain controlling.

## Connector communication bus

The connector bus provides one auditable message contract for Google Drive, Gmail, GitHub, Hugging Face, Figma/FigJam, Dropbox, and the Case API.

- Every transfer retains stable object identity, native locator, hash/revision, source status, proof tier, privacy mode, correlation history, and promotion state.
- Message creation and per-target delivery rows use a transactional outbox.
- Deterministic idempotency prevents repeated synchronization from becoming false duplicate corroboration.
- Delivery workers claim messages, record attempts and receipts, acknowledge completed work, and maintain stream checkpoints.
- Google Drive and other mutations require explicit scoped authorization.
- GitHub never receives raw case text or privileged evidence.
- Hugging Face receives only bounded local/private derivative work and returns promotion-blocked candidates.
- Figma/FigJam receives source-manifested visual projections rather than proof.
- Native evidence bytes and connector credentials are prohibited from the message payload.

See `docs/CONNECTOR_COMMUNICATION_PROTOCOL.md` and `schemas/connector-envelope.schema.json`.

## First-person statement and recollection mini-learning

The system preserves user statements, recollections, authored-source summaries, sworn first-person facts, interpretations, and later corrections as versioned source objects.

- Exact user language remains preserved alongside any normalized retrieval text.
- Statements are classified by scope: self action, knowledge, authorization, receipt timing, understanding, accounting correction, recollection of another statement/event, or interpretation.
- A correction creates a new version and an open conflict when dates, amounts, classifications, or other material features change; the prior statement remains visible.
- Topic examples include positive routes, hard negatives, exact-key features, required source fields, expected labels, and promotion gates.
- Candidate evidence is scored against exact identifiers, topic overlap, lexical similarity, and source posture without automatic promotion.
- Hugging Face projections exclude exact language by default and remain metadata-only unless a private approved workflow explicitly includes it.
- A confirmed first-person fact remains limited to what the speaker did, knew, received, understood, or authorized; recollections about another actor still require independent attribution and intent proof.

See `docs/FIRST_PERSON_RECOLLECTION_LEARNING.md`.

## Documentation

- `docs/AI_NEW_FINDING_LIFECYCLE.md`
- `docs/AI_SEARCH_INTEGRATION.md`
- `docs/LIVING_PROOF_DEBT_RESOLVER.md`
- `docs/EXACT_RETRIEVAL_AND_INVALIDATION.md`
- `docs/NATIVE_ACCOUNTING_RECONCILIATION_ENGINE.md`
- `docs/DRIVE_SYNC_SCHEMA.md`
- `docs/CONNECTOR_COMMUNICATION_PROTOCOL.md`
- `docs/FIRST_PERSON_RECOLLECTION_LEARNING.md`
- `schemas/connector-envelope.schema.json`
