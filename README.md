# Case Profile App

A React + Express case-management application with living proof-debt, exact-retrieval, source-lineage, and native-accounting reconciliation services.

## Setup & Run

```bash
npm install
npm run dev
```

The command starts:

- Primary Express API on `http://localhost:3001`
- Accounting reconciliation API on `http://localhost:3002`
- Vite dev server on `http://localhost:5173`

Run the accounting service alone with:

```bash
npm run accounting
```

Run tests with:

```bash
npm test
```

## Evidence-control capabilities on the resolver branch

- Case records, messages, and tasks
- File hash intake
- Persistent proof debts and search receipts
- Candidate matching across all open proof debts
- Dependency propagation and resolution events
- Exact-first routing for amounts, dates, Bates numbers, checks, invoices, loans, accounts, lots, escrow files, and filenames
- Evidence atoms with exact source lineage
- Conclusion dependency tracking and stale-answer invalidation
- Dead-lead and exculpatory memory
- Source-family deduplication and version control
- Human review gate before proof-debt closure
- Hash-chained review decisions
- Money-event ledger and accounting-obligation persistence
- Obligation → funding → reimbursement → customer-credit → final-treatment reconciliation
- Duplicate-funding candidate detection without automatic duplicate findings
- Final-balance controls that exclude unresolved adjustments from confirmed net calculations
- Ranked native-record acquisition requests

The system never treats a match score, aggregate balance, equal amount, derived report, or unresolved adjustment as proof. Native provenance, identity checks, contrary-evidence review, customer-credit closure, and a recorded human decision remain required.

See:

- `docs/LIVING_PROOF_DEBT_RESOLVER.md`
- `docs/EXACT_RETRIEVAL_AND_INVALIDATION.md`
- `docs/NATIVE_ACCOUNTING_RECONCILIATION_ENGINE.md`
- `docs/DRIVE_SYNC_SCHEMA.md`
