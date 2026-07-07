# Case Intelligence Tool Pack

Status: generic tool layer; synthetic/redacted data only.

This pack adds reusable reasoning skills, schemas, and lightweight Python checks for case visuals, accounting narratives, source-status routing, bridge-record closure, visual-document routing, and dashboard readiness.

## Prime directive

Native/source records control. This repository should not store raw case evidence, private exhibits, bank records, native PDFs, witness files, confidential communications, or attorney work product that has not been cleared for repository use.

GitHub is the code and schema lane. Google Drive remains the source-of-truth lane. Hugging Face may be used only for private derivative routing, embeddings, clustering, reranking, layout review, table detection, and redacted synthetic review.

## Installed components

| Path | Use |
| --- | --- |
| `schemas/visual_claim.schema.json` | Data contract for any chart, diagram, evidence card, or dashboard object. |
| `schemas/timeline_event.schema.json` | Data contract for timeline/accounting events with source status and date status. |
| `skills/CASE_REASONING_SKILL_PACK.md` | Reusable reasoning skills for source status, accounting spine, contradiction routing, and bridge closure. |
| `skills/VISUAL_DESIGN_AUDITOR.md` | Hard visual QA rules for overlap, scale, wrong chart type, unreadable labels, and source-status failures. |
| `skills/ACCOUNTING_VISUAL_ENGINE.md` | Accounting-specific reasoning layer for Sankey, waterfall, source matrix, and bridge-board visuals. |
| `skills/QUESTION_AND_DISCOVERY_ROUTER.md` | Converts pressure points into focused questions, record families, custodian routes, and closure actions. |
| `tools/chart_decision_router.py` | CLI helper that recommends the correct visual type from intent and data columns. |
| `tools/visual_registry_linter.py` | CLI helper that audits a visual registry CSV for missing source status, bridge closure, scale, and export readiness. |
| `tools/source_status_scorecard.py` | CLI helper that summarizes source-status readiness and action rows from a registry CSV. |
| `tools/mermaid_case_spine_generator.py` | CLI helper that converts redacted case-spine rows into Mermaid flowchart code. |
| `huggingface/HF_PRIVATE_ROUTER_CARD.md` | Model-routing card for private semantic search and reranking. |
| `huggingface/VISUAL_DOCUMENT_MODEL_ROUTER.md` | Model-routing card for layout-sensitive pages, table regions, and visual-document review. |
| `huggingface/PRIVATE_SPACE_SPEC.md` | Private Space spec for a redacted visual registry router. |
| `huggingface/space_requirements.txt` | Minimal private Space dependency list. |
| `synthetic_samples/visual_registry_sample.csv` | Safe sample input with fake/redacted records only. |

## Reasoning order

Run the skills in this order:

1. Source-status route the claim.
2. Identify the case question.
3. Select the visual type.
4. Check accounting/date/actor scale.
5. Check whether the page is visual-native-required.
6. Find bridge-missing records.
7. Build the visual from a registry row, not from memory.
8. Audit export readiness.
9. Retire or supersede the old visual.

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
- Full deposition transcripts.
- Private counsel work product.
- Confidential personal identifiers.

## Quick CLI examples

```bash
python case-intel-tools/tools/chart_decision_router.py --intent accounting_flow --columns date,amount,payor,payee,source_status
python case-intel-tools/tools/visual_registry_linter.py case-intel-tools/synthetic_samples/visual_registry_sample.csv
python case-intel-tools/tools/source_status_scorecard.py case-intel-tools/synthetic_samples/visual_registry_sample.csv
python case-intel-tools/tools/mermaid_case_spine_generator.py case-intel-tools/synthetic_samples/visual_registry_sample.csv
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
- A supersession/retirement status for prior versions.

## Working architecture

```text
Google Drive source registry
→ redacted/synthetic visual registry export
→ GitHub schema/linter/router checks
→ Hugging Face private semantic/layout routing when useful
→ Figma visual components and export frames
→ counsel/expert/internal review
```
