# AI Search Integration — Google Drive + Hugging Face + GitHub

## Operating model

Google Drive remains the evidence plane. GitHub is the versioned control plane for search code, tests, configurations, and change history. Hugging Face supplies retrieval models that rank candidate passages; it does not decide whether a fact is proven.

## Interactive search path

1. Apply the Drive routing contract and identity firewall first.
2. Preserve exact file IDs, SHA-256 values, Bates labels, loan/account identifiers, dates, amounts, page numbers, rows, and source URLs.
3. Run lexical retrieval first because it is fast and reliable for exact legal/accounting identifiers.
4. Skip AI for exact lookups.
5. For conceptual queries, use a compact local Hugging Face embedding model only on the bounded candidate set.
6. Return ranked source passages with their original anchors.
7. Synthesize a response only after retrieval, while labeling confirmed fact, supported inference, candidate connection, and unresolved gap separately.

## Model tiers

| Tier | Purpose | Model path | Candidate cap |
|---|---|---|---:|
| Exact | Bates, account, loan, date, amount, filename | No model | 24 |
| Fast | Routine semantic retrieval | `onnx-community/bge-small-en-v1.5-ONNX` locally through Transformers.js | 24 |
| Deep | Offline multi-lane reconciliation | `BAAI/bge-m3` plus `BAAI/bge-reranker-v2-m3` | 60 |

The fast path is the default. Deep mode is not automatically triggered merely because a query is long.

## Efficiency controls

- Lazy-load the model only after lexical routing.
- Cache embeddings by model ID, dtype, and SHA-256 of the passage text.
- Re-embed only changed source units.
- Never embed the entire Drive for one interactive question.
- Bound request size, chunk count, candidate count, and returned results.
- Fall back to lexical results when the model is unavailable.
- Keep generated narrative outside the retrieval index unless it is clearly marked as derived analysis.

## Privacy controls

The default module downloads a model from Hugging Face and performs inference locally. It does not send case passages to a hosted inference endpoint. Any future remote endpoint must be explicitly enabled, documented, and limited to approved non-privileged material or a private controlled deployment.

## Evidence controls

- Native records control over indexes, embeddings, summaries, and model scores.
- A similarity score is not proof of identity, payment lineage, intent, falsity, or enterprise membership.
- Candidate entity merges remain pending until an exact source bridge is located.
- Negative controls and collision tests must remain in the regression suite.
- Search results must retain source and locator fields so an answer can cite the underlying record.

## GitHub change policy

Changes to routing, scoring, model selection, identity rules, and source-status labels should be made through a branch and pull request with tests. A model upgrade is not accepted solely because it is newer; it must improve a case-specific evaluation set without increasing contamination or losing exact-record recall.

## Initial evaluation set

Use the existing Draw 1–4, Fortis wires, owner advances, Central Bank deposits, BMC payments, plumbing invoices, and Lot 2 transfers. Measure:

- exact-ID recall;
- amount/date collision errors;
- property and loan contamination;
- source-anchor retention;
- top-5 and top-10 retrieval usefulness;
- latency in exact, fast, and deep modes;
- lexical fallback behavior;
- unsupported-link rate.
