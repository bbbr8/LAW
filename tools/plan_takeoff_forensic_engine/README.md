# PlanTakeoff Forensic Engine

Date: 2026-07-07
Repository: bbbr8/LAW
Purpose: litigation-support and forensic construction-plan quantity review for Bryce Jones / Fraud case materials.

## What this package is

PlanTakeoff Forensic Engine is a hybrid rule-based + AI-assisted plan review framework. It is designed to read house-plan PDFs, extract plan identity and schedule text, classify sheets, detect scale and dimensions where possible, estimate selected quantities, compare quantities against invoices/draws/tickets/takeoff spreadsheets, and produce a confidence-tiered professional review packet.

This package is not a replacement for a retained estimator, engineer, architect, or licensed professional. It is a source-routing and forensic quantity-control engine. It is built to identify where a billed quantity appears consistent, overstated, under-supported, source-routed, bridge-missing, or in conflict with the plan/source record.

## Core rule

Do not present AI-derived plan quantities as final expert measurements unless the relevant page, scale, dimensions, and quantity method are verified. Every quantity must receive a confidence tier and source-status label.

## Source-status labels

- SOURCE_CLOSED: Quantity is supported by native plan/schedule or verified measurement and has a clear source path.
- SOURCE_ROUTED: Source path is identified, but manual estimator/native closure is still required.
- BRIDGE_MISSING: A required bridge is missing, such as scale, page, schedule, dimension, or project attribution.
- SOURCE_CONFLICT: Plan/takeoff/invoice/draw records conflict.
- DERIVED_ONLY: Output depends on OCR/AI extraction only.
- LEAD_ONLY: Useful direction, not proof.
- QUARANTINE: Do not use attorney-facing until identity/source issues are resolved.

## Primary lanes

1. Foundation and footings
2. Foundation wall length and height
3. Slab and flatwork area
4. Suspended slab / lower garage / shop or under-garage spaces
5. Framing and lumber takeoff comparison
6. Roof area and pitch support
7. Drywall/flooring/cabinet/counter areas where sheet data permits
8. Plan-version comparison
9. Draw/invoice/ticket comparison
10. Comparator-home takeoff comparison

## Existing Drive inspiration

The Drive already contains plan and takeoff artifacts, including:

- Jones plans and Peterson/Colby plan sets.
- Kleinman Residence plans and takeoff method workpapers.
- Jones lumber material takeoff spreadsheets.
- Strong, Kleinman, Colby/Peterson, and Friendly Acres takeoff spreadsheets.
- Advanced construction takeoff report for Bryce/Jones foundation and concrete analysis.

This GitHub package turns that concept into reusable code.

## Hugging Face inspiration layer

Use Hugging Face models only as assistive extractors/rankers. Good candidate classes:

- Floor-plan segmentation/vectorization models for wall/room/line extraction.
- Vision-language floor-plan models for structured JSON extraction.
- Microsoft Table Transformer for schedules and plan tables.
- Layout/document models for drawing notes, title blocks, and schedules.
- Rerankers to match plan evidence against invoices/draw lines.

Do not use a model to make a final legal or expert conclusion.

## Basic command

```bash
python -m tools.plan_takeoff_forensic_engine.plan_takeoff_engine \
  --input ./plans \
  --comparators ./comparators \
  --output ./outputs/plan_takeoff_run
```

## Expected outputs

- `plan_manifest.csv`
- `sheet_index.csv`
- `scale_candidates.csv`
- `dimension_candidates.csv`
- `quantity_estimates.csv`
- `takeoff_confidence_flags.csv`
- `invoice_draw_comparison.csv`
- `professional_takeoff_report.md`
- `run_summary.json`

## Attorney-facing use

The attorney-facing output should not say: "AI measured the house."

It should say:

> The plan/takeoff engine identified plan-supported quantity benchmarks and source gaps. Where billed/drawn quantities exceed plan-supported ranges, the issue is source-routed or source-conflicted and should be closed with native plans, estimator workpapers, vendor invoices, tickets, and payment records.

## Highest-value case use

For the Bryce Jones matter, this package should prioritize:

1. A&D / concrete / footing / foundation quantity comparisons.
2. Kilgore / flatwork area and yardage comparisons.
3. BMC / lumber and framing comparisons.
4. Suspended slab / basement / wall-height change claims.
5. Plan-version conflicts: Jones vs Peterson/Colby vs later plan copies.
6. Comparator homes: Kleinman, Strong, Colby/Peterson, James, Friendly Acres.
