# Hugging Face Model Stack — PlanTakeoff Forensic Engine

Date: 2026-07-07
Purpose: define the optional model layer for house-plan, schedule, and takeoff review.

## Control rule

Hugging Face models are assistive. They help extract, segment, classify, rerank, or structure plan information. They do not make final expert conclusions, legal conclusions, or final quantity determinations.

Every model-derived quantity remains one of:

- DERIVED_ONLY
- SOURCE_ROUTED
- BRIDGE_MISSING
- SOURCE_CONFLICT

until verified against native plans, scale, dimensions, estimator workpapers, and source records.

## Current model candidates from Hugging Face search

### Floor-plan / plan-vision candidates

- `mudasir13cs/qwen25-vl-3b-floorplan-grpo`
  - Task: image-to-text
  - Use: structured JSON extraction / vectorization inspiration for floor plans.
  - Risk: not litigation-grade without calibration and verification.

- `mudasir13cs/qwen25-vl-3b-floorplan-sft`
  - Task: image-to-text
  - Use: floor-plan structured extraction.
  - Risk: model may hallucinate geometry. Verify with native page image and scale.

- `Hyunwoo1605/mask2former-floorplan-instance-segmentation`
  - Use: floorplan instance segmentation inspiration.
  - Risk: trained domain may not match custom construction plan sheets.

- `Yytsi/floorplan-to-3d-walls`
  - Use: wall segmentation / wall extraction concept.
  - Risk: likely better for simplified floor-plan images than full construction plan PDFs.

### Table and schedule extraction candidates

- `microsoft/table-transformer-detection`
  - Use: detect plan schedules, tables, footing schedules, door/window/beam schedules.

- `microsoft/table-transformer-structure-recognition`
  - Use: convert table regions into structured rows/columns.

- `microsoft/table-transformer-structure-recognition-v1.1-all`
  - Use: improved structure recognition candidate.

### Document layout candidates

- `microsoft/layoutlmv3-base`
- `microsoft/layoutlmv3-large`
- `nielsr/layoutlmv3-finetuned-funsd`

Use: title blocks, notes, forms, schedules, callouts, and text-region classification.

## Recommended AI-assisted pipeline

1. Render PDF page to high-resolution PNG.
2. Classify sheet type.
3. Detect title block and extract project/address/date/revision.
4. Detect schedule/table regions.
5. OCR schedule/table regions.
6. Detect likely dimension strings and scale notation.
7. Segment wall/room/foundation candidates where model confidence supports it.
8. Produce geometry candidates only, never final quantity.
9. Require calibration and manual/professional verification.
10. Compare source-routed quantities against invoices/draws/tickets.

## Model output schema

```json
{
  "model_name": "string",
  "source_page": "string",
  "page_number": 1,
  "detected_objects": [
    {
      "type": "wall|room|table|dimension|title_block|schedule|slab|footing|unknown",
      "bbox": [0, 0, 100, 100],
      "text": "optional OCR text",
      "confidence": 0.0,
      "source_status": "DERIVED_ONLY",
      "required_native_closure": "scale calibration + manual estimator verification"
    }
  ]
}
```

## Do not do this

Do not say:

> The AI proved the billed quantity is false.

Say:

> The engine identified a source-routed quantity conflict. Native plan scale, estimator measurement, tickets, invoices, and draw records must close the bridge.

## Best use in Bryce Jones matter

The model layer is most useful for:

- locating plan pages that contain foundation/footing/slab information;
- extracting plan schedules and wall/footing notes;
- detecting where dimensions exist;
- identifying likely plan-version differences;
- locating pages for human estimator review;
- comparing plan-supported ranges against A&D, Kilgore, BMC, and draw records.

## Professional threshold

A high-confidence professional takeoff requires:

- correct plan version;
- correct page;
- verified scale;
- dimension closure;
- explicit method;
- estimator/manual verification;
- comparison to invoices/tickets/draws;
- confidence tier and source-status label.
