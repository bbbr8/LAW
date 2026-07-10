# Case Review Reasoning Portals

This package turns the Entropy Dissolution Engine into a **source-bound case-review orchestrator**.

It does not ask one model for one flat answer. It compiles each material question into variables and routes the question through specialized portals that preserve:

- exact source locators;
- identity, time, money, scope, document, actor, process, alternative, and legal-element variables;
- if/then branches;
- falsification tests;
- competing explanations;
- missing bridge records;
- truth status;
- finding level;
- reopen triggers;
- human review status.

## Control boundary

Native records control. OCR, embeddings, rerankers, NLI, summaries, and portal observations are assistive work product.

Model outputs enter only as:

```text
DERIVED_ONLY + PROPOSED
```

A model cannot accept its own output. Proof-facing findings require exact anchors and human review.

## Included portals

1. Source Integrity / Chain of Custody
2. Identity / Loan / Lot / Account Firewall
3. Event-Time / Knowledge-Time / Litigation-Time
4. Money Rail / Same-Dollar / Credit
5. Contract Baseline / Change / Delivery
6. Visibility / Signature / Authorization
7. Claim / Label / Version Drift
8. Typed Contradiction / Compatibility
9. Alternative Explanation / Falsification
10. Expected Record / Proof Debt
11. Element-by-Element Evidence Mapping
12. Information Dissolution / Reconstructability

## Run

```bash
python case_review_portals.py example_case.json -o report.json
```

Request additional portals explicitly:

```bash
python case_review_portals.py example_case.json \
  --portal legal_elements \
  --portal contradiction \
  -o report.json
```

## Report structure

The output contains:

- direct answer;
- current truth status;
- routed portals;
- portal observations and metrics;
- key and open variables;
- surviving and defeated branches;
- bridge-record list;
- reproducible reasoning trace;
- reopen triggers;
- model-policy violations;
- audit metadata.

## Truth and finding controls

Machine review is conservative. An unresolved critical conflict, untested material branch, or missing bridge record keeps the report at `UNRESOLVED`.

Automated code may produce only:

- `L1_EXTRACTED`
- `L2_NORMALIZED`
- `L3_CORROBORATED`
- at most `L4_SOURCE_CLOSED_CANDIDATE` after additional source-closure logic

The following require humans or institutions:

- `L5_REVIEWER_ACCEPTED`
- `L6_COUNSEL_EXPERT_ADOPTED`
- `L7_ADJUDICATED`

## Hugging Face layer

`hf_model_manifest.json` defines the optional model stack and portal routes.

Default candidates:

- `ibm-granite/granite-docling-258M` for document/layout/table candidates
- `BAAI/bge-m3` for dense retrieval
- `BAAI/bge-reranker-v2-m3` for reranking
- `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` for contradiction candidates

The deterministic portal engine remains the decision-control layer.

## Google Drive integration pattern

Drive is treated as the source registry and work-product surface, not as an excuse to flatten evidence.

Recommended ingestion record:

```json
{
  "drive_file_id": "...",
  "drive_url": "...",
  "document_id": "DOC-...",
  "native_title": "...",
  "sha256": "...",
  "custodian": "...",
  "source_status": "NATIVE_VERIFIED",
  "case_id": "...",
  "loan_id": "...",
  "lot_id": "...",
  "project_id": "...",
  "bates_start": "...",
  "bates_end": "..."
}
```

Derived portal reports should link back to Drive file IDs and page/Bates/text anchors.

## Design basis

The architecture adopts ideas from current research directions including:

- executable counterfactual testing;
- graph-constrained legal reasoning;
- explicit evidence DAGs;
- source-attributable graph trajectories;
- provenance-preserving agents.

These ideas are implemented here as auditable data structures and deterministic portal rules, not hidden model reasoning.
