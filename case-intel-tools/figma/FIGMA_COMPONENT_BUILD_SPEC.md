# Figma Component Build Spec

Status: design-system spec generated from the case-intel source-status model.

## Core pages

```text
00 Cover and rules
01 Source-status chips
02 Evidence cards
03 Accounting visuals
04 Timeline visuals
05 Bridge boards
06 Contradiction matrices
07 Export frames
08 Retired visuals
```

## Required components

| Component | Fields |
| --- | --- |
| SourceStatusChip | status, short_label, export_rule |
| EvidenceCard | title, source_status, locator, pressure_point, next_action |
| MoneyMovementCard | date, amount, from_actor, to_actor, accounting_role, source_status |
| BridgeGapCard | pressure_point, missing_record, likely_custodian, next_action |
| TimelineEvent | date, lane, event_label, source_status, locator |
| ContradictionPair | statement_a, source_a, statement_b, source_b, conflict_type |
| ExportFrame | title, audience, source_boundary, version_date, export_status |

## Source-status display rules

| Status | Design meaning |
| --- | --- |
| native_closed | highest-confidence source chip |
| source_routed | route exists; native closure still tracked |
| bridge_missing | missing record; show closure action |
| source_conflict | conflict; do not flatten into neutral ambiguity |
| ocr_derived | extracted text; page image controls |
| summary_only | not evidence-grade by itself |
| derived_analysis | math/model/inference layer |
| counsel_review | hold for review before external use |

## Frame sizes

Use stable export frames:

```text
Slide 16:9
Letter portrait
Letter landscape
Evidence card 4:3
Dashboard wide
```

## Export footer

Every frame needs:

```text
visual title
case question
source boundary
version date
export audience
source-status legend
```

## Design failure rules

Do not export if:

- nodes overlap;
- labels are unreadable at normal zoom;
- connectors cross heavily;
- source status is missing;
- money scale is undisclosed;
- visual type does not match the question;
- old version is not retired or superseded.
