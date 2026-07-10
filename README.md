# Case Profile App

A React + Express case-management application with a living proof-debt and source-lineage backend.

## Setup & Run

```bash
npm install
npm run dev
```

The command starts:

- Express API on `http://localhost:3001`
- Vite dev server on `http://localhost:5173`

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
- Human review gate before proof-debt closure
- Hash-chained review decisions

The resolver never treats a match score as proof. Native provenance, identity checks, contrary-evidence review, and a recorded human decision are required before closure.

See:

- `docs/LIVING_PROOF_DEBT_RESOLVER.md`
- `docs/EXACT_RETRIEVAL_AND_INVALIDATION.md`
