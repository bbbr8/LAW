# Native Accounting Reconciliation Engine

## Purpose

This layer converts open accounting proof debts into executable acquisition, ledger, and reconciliation work. It does not assume that a deposit restored a customer, that equal amounts are duplicates, or that an aggregate final balance is an invoice-level debt.

The controlling chain is:

`obligation -> funding source -> actual application -> reimbursement -> customer credit -> final charge -> nonduplicative loss`

Any broken link remains visible as proof debt.

## Core controls

### 1. Native acquisition queue

Every requested record carries:

- proof-debt ID;
- specific native record;
- likely custodian;
- exact search terms;
- candidate source and locator;
- collapse value and damages impact;
- human-review requirement;
- affected conclusions.

### 2. Source-family lineage

Workbooks, Numbers packages, PDFs, images, exports, and duplicate copies are grouped by stable source-family ID. Hashes and UUIDs identify exact objects. Duplicate copies do not count as independent corroboration.

### 3. Money-event ledger

Each deposit, request, draw, wire, payment, reimbursement, refund, or credit is a separate event. The ledger preserves:

- event date;
- event type;
- source entity;
- account or loan;
- amount;
- represented purpose;
- actual beneficiary and project;
- instrument;
- source status;
- authorization status;
- customer-credit status;
- linked obligation and proof debts.

### 4. Obligation/funding/credit reconciliation

An obligation can produce a confirmed loss only after the following fields are source-closed:

- project identity;
- invoice;
- delivery or installed scope;
- payment;
- customer credit;
- final accounting treatment;
- duplicate risk.

Unresolved funding is displayed separately and never used to reduce or create confirmed loss.

### 5. Final-balance control

The engine may calculate an arithmetic balance from source-closed totals. It may not automatically include unresolved credits, omitted checks, reclassifications, or other candidate adjustments.

Example:

- total cost: `$1,101,159.96`;
- confirmed budget: `$792,256.00`;
- confirmed owner-check total in the located workbook: `$251,522.43`;
- confirmed arithmetic balance: `$57,381.53`;
- unresolved candidate credits/reclassifications remain outside that total.

### 6. Duplicate-funding candidates

Equal amounts may create a candidate review event, but duplicate treatment requires the same obligation, project, instrument, funding role, and final accounting treatment. A `$70,000` Lot 2/Loretta event must remain separate from a `$70,000` Bryce owner-payment event unless native records connect them.

## Accounting service

The reconciliation APIs run as a separate Express service on port `3002` during development.

```bash
npm run accounting
```

`npm run dev` starts the primary API, accounting API, and client together.

Health endpoint:

- `GET /api/accounting-health`

## API routes

### Money events

- `GET /api/cases/:id/money-events`
- `POST /api/cases/:id/money-events`

A money event requires date, type, amount, source status, accounting role, and project or identity scope.

### Accounting obligations

- `GET /api/cases/:id/accounting-obligations`
- `POST /api/cases/:id/accounting-obligations`
- `PATCH /api/cases/:id/accounting-obligations/:obligationId`

### Reconciliation

- `POST /api/cases/:id/reconcile-accounting`
- `GET /api/cases/:id/accounting-reconciliation-runs`

The run returns obligation results, duplicate-funding candidates, and a completeness label. It never automatically creates a confirmed loss from unresolved proof.

### Final-balance controls

- `POST /api/cases/:id/final-balance-controls`
- `GET /api/cases/:id/final-balance-controls`

Unresolved adjustments are returned separately. `candidateNetBalance` remains `null` by design.

### Source acquisition

- `GET /api/cases/:id/source-requests`
- `POST /api/cases/:id/source-requests`
- `GET /api/cases/:id/acquisition-priorities`

Requests are ranked by information gain, collapse value, damages impact, linked claims, availability, and cost.

## Drive counterpart

The Drive workbook `02_NATIVE_ACCOUNTING_RECONCILIATION_ENGINE_2026-07-10` contains:

- `DASHBOARD`
- `NATIVE_ACQUISITION`
- `SOURCE_FAMILY_LINEAGE`
- `MONEY_EVENT_LEDGER`
- `OBLIGATION_FUNDING_CREDIT`
- `FINAL_BALANCE_RECON`
- `RECON_EXCEPTIONS`
- `SOURCE_REQUEST_PACKETS`
- `PHASE2_HEALTH`
- `DATA_DICTIONARY`

## Proof boundary

The engine is an accounting-control and investigative-routing system. It is not a final expert opinion, legal conclusion, or damages calculation. Native records, human review, counsel, and qualified expert analysis control final use.
