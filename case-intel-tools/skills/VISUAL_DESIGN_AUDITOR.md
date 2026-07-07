# Visual Design Auditor

Status: hard QA layer for case visuals.

## Purpose

This skill detects visuals that look impressive but fail evidence-control review. It targets overlap, scale distortion, wrong chart type, unreadable labels, missing source status, and mixed data-status contamination.

## Hard-fail conditions

A visual is not export-ready if any of these are true:

1. It has no single controlling question.
2. It mixes native facts, OCR, summaries, and derived analysis without labels.
3. It has no source-status chip or legend.
4. It uses a nonzero money scale without disclosure.
5. It uses fake date spacing without disclosure.
6. It uses a network graph when a table, matrix, or timeline would be clearer.
7. Nodes overlap.
8. Connectors cross so heavily that the route cannot be followed.
9. Labels require zooming beyond normal review size.
10. It contains more than one argument layer without separation.
11. It lacks audience and export date.
12. It lacks a supersession/retirement note for prior versions.

## Chart-type correction table

| Bad pattern | Why it fails | Replace with |
| --- | --- | --- |
| Giant spiderweb graph | Looks complex but hides causation and source status. | Case spine + contradiction matrix. |
| Generic heatmap | Color intensity without source meaning creates false confidence. | Source-status heatmap with exact labels. |
| Bar chart for money movement | Bars compare amounts but do not show flow or application. | Sankey + waterfall + ledger detail. |
| Timeline with equal event spacing | Misrepresents time gaps. | Actual-date timeline or disclosed categorical sequence. |
| Screenshot collage | Forces the reader to hunt. | Page-layout callout with source locator and claim. |
| Single overloaded dashboard | No hierarchy. | Navigation map + separate focused panels. |

## Layout rules

- Use left-to-right flow for chronology and money application.
- Use top-to-bottom flow for hierarchy and source closure.
- Use swimlanes when actor control matters.
- Use tables/matrices when the goal is comparison or contradiction.
- Use cards when each item needs source status, closure status, and next action.
- Use one color system consistently; color must mean source status or priority, not decoration.
- Keep a stable legend across all exports.

## Export-readiness score

Score each category 0, 1, or 2.

| Category | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Question | Missing | Broad | Precise |
| Source status | Missing | Partial | Complete |
| Chart type | Wrong | Acceptable | Correct |
| Scale | Misleading | Disclosed | Proper |
| Layout | Overlap | Some clutter | Clear |
| Audience | Missing | Implied | Explicit |
| Bridge closure | Missing | Partial | Complete |

Export-ready threshold: 12/14 with no hard-fail condition.

## Auditor output

```text
Visual title:
Controlling question:
Current visual type:
Recommended visual type:
Hard-fail findings:
Source-status defects:
Scale/date defects:
Layout defects:
Bridge-record defects:
Export decision:
Required fix:
```
