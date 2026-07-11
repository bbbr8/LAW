# Hugging Face + Google Drive + GitHub Expansion Plan

This plan expands the review-build scaffold without placing private source files in the public repository.

## Operating model

- Google Drive is the source-facing review workspace.
- GitHub stores repeatable scripts, schemas, tests, and configuration.
- Hugging Face model IDs are registered as optional local runs.
- Model outputs are never treated as source records.

## Expansion lanes

| Lane | Output | Primary files |
|---|---|---|
| Table QA | row/cell QA and total reconciliation | `scripts/reconcile_totals.py`, `config/hf_model_registry.yml` |
| Source inventory | file sizes and SHA-256 hashes | `scripts/hash_manifest.py` |
| PDF object inventory | image entry rows with xrefs and hashes | `scripts/inventory_pdf_images.py` |
| Semantic index | source-grounded JSONL chunks | `scripts/build_chunk_index.py` |
| HF registry | model-run matrix for local experiments | `scripts/build_hf_registry.py` |

## Guardrails

1. Keep source files outside GitHub unless the repository is private and approved.
2. Store every generated output with a build timestamp and source hash manifest.
3. Keep AI model outputs in separate review tabs.
4. Promote a model result only after manual review and source tie-out.
5. Use Drive links or source IDs for citations, not model-generated text.

## Recommended command sequence

```bash
python evidence-build/scripts/hash_manifest.py input outputs/source_manifest.csv
python evidence-build/scripts/build_hf_registry.py evidence-build/config/hf_model_registry.yml outputs/hf_model_registry.csv --jsonl outputs/hf_model_registry.jsonl
python evidence-build/scripts/reconcile_totals.py outputs/table_totals_input.csv outputs/table_reconciliation.csv
python evidence-build/scripts/build_chunk_index.py outputs/source_chunks.jsonl outputs/*.csv
```

The outputs can then be copied into the matching Google Sheet tabs.