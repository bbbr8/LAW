# Case Intel Runbook

Status: operating runbook for the source-status visual toolchain.

## Goal

Convert redacted registry rows into clear review artifacts without mixing proof status, visual design, and source closure.

## Standard pipeline

```text
1. Export a redacted visual registry from the source-control system.
2. Run the visual quality gate.
3. Run the source-status scorecard.
4. Generate bridge-board rows.
5. Generate graph JSON if navigation or relationship review is needed.
6. Generate Mermaid case spine if the reviewer needs a quick route map.
7. Route visual-native-required rows to the Hugging Face private/layout lane only after redaction review.
8. Send approved rows to Figma components and export frames.
9. Retire or supersede older visuals.
```

## Commands

```bash
python case-intel-tools/tools/visual_quality_gate.py registry.csv
python case-intel-tools/tools/source_status_scorecard.py registry.csv
python case-intel-tools/tools/bridge_board_generator.py registry.csv --format csv
python case-intel-tools/tools/evidence_graph_exporter.py registry.csv
python case-intel-tools/tools/mermaid_case_spine_generator.py registry.csv
```

## Quality gates

A row is blocked when:

- source status is missing;
- a routed row lacks a locator;
- bridge-missing status lacks closure detail;
- source-conflict status lacks conflict type;
- a blocking source status is marked export-ready;
- overlap or wrong-chart flags are set;
- money or timeline scale is undisclosed.

## Artifact routing

| Output | Use |
| --- | --- |
| visual quality gate JSON | pass/fail control record |
| source-status scorecard JSON | readiness dashboard input |
| bridge board CSV/JSON | closure task board |
| evidence graph JSON | relationship/navigation review |
| Mermaid case spine | quick visual route map |
| Figma tokens | design-system implementation |
| HF private router outputs | semantic/layout routing only |

## Review language

Use source-status conclusions:

- Native closed.
- Source routed; closure required.
- Bridge missing.
- Source conflict.
- OCR/layout derived.
- Summary only.
- Derived analysis.
- Review required.

## Non-negotiable boundary

A tool output can route work, expose a defect, or prepare a visual. It cannot replace native/source review, attorney review, accounting review, or expert review.
