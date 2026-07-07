# Case Intelligence Tool Pack

Status: generic tool layer; synthetic/redacted data only.

This pack adds reusable reasoning skills, schemas, and lightweight Python checks for case visuals, accounting narratives, source-status routing, bridge-record closure, and dashboard readiness.

## Prime directive

Native/source records control. This repository should not store raw case evidence, private exhibits, bank records, signatures, native PDFs, witness files, confidential communications, or attorney work product that has not been cleared for repository use.

GitHub is the code and schema lane. Google Drive remains the source-of-truth lane. Hugging Face may be used only for private derivative routing, embeddings, clustering, reranking, and redacted synthetic review.

## Installed components

| Path | Use |
| --- | --- |
| `schemas/visual_claim.schema.json` | Data contract for any chart, diagram, evidence card, or dashboard object. |
| `skills/CASE_REASONING_SKILL_PACK.md` | Reusable reasoning skills for source status, accounting spine, contradiction routing, and bridge closure. |
| `skills/VISUAL_DESIGN_AUDITOR.md` | Hard visual QA rules for overlap, scale, wrong chart type, unreadable labels, and source-status failures. |
| `tools/chart_decision_router.py` | CLI helper that recommends the correct visual type from intent and data columns. |
| `tools/visual_registry_linter.py` | CLI helper that audits a visual registry CSV for missing source status, bridge closure, scale, and export readiness. |
| `huggingface/HF_PRIVATE_ROUTER_CARD.md` | Model-routing card for private semantic search and reranking. |
| `synthetic_samples/visual_registry_sample.csv` | Safe sample input with fake/redacted records only. |

## Reasoning order

Run the skills in this order:

1. Source-status route the claim.
2. Identify the case question.
3. Select the visual type.
4. Check accounting/date/actor scale.
5. Find bridge-missing records.
6. Build the visual from a registry row, not from memory.
7. Audit export readiness.
8. Retire or supersede the old visual.

## No-raw-evidence rule

Allowed in this repo:

- Code.
- Schemas.
- Synthetic examples.
- Design tokens.
- Redacted test rows.
- Generic reasoning prompts.

Not allowed in this repo:

- Raw bank statements.
- Native contracts or invoices.
- Draw packets.
- Signature images.
- Full deposition transcripts.
- Private counsel work product.
- Confidential personal identifiers.

## Quick CLI examples

```bash
python case-intel-tools/tools/chart_decision_router.py --intent accounting_flow --columns date,amount,payor,payee,source_status
python case-intel-tools/tools/visual_registry_linter.py case-intel-tools/synthetic_samples/visual_registry_sample.csv
```

## Output standard

A visual is export-ready only when it has:

- One question.
- One recommended visual type.
- A source-status label.
- A native/source locator or a bridge-missing label.
- A disclosed scale rule.
- An audience.
- An export decision.
