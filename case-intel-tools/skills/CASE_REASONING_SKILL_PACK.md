# Case Reasoning Skill Pack

Status: reusable reasoning layer for source-bound case visuals and dashboards.

## Control rule

Do not reason from an isolated chart, screenshot, OCR extract, or summary if the question requires native proof. Route every pressure point through source status first.

## Skill 1 — Source Status Router

Classify each claim before styling it.

| Status | Meaning | Visual treatment |
| --- | --- | --- |
| `native_closed` | Native/source record is located and controls the point. | Solid border, highest confidence label. |
| `source_routed` | Route exists but native closure is not fully completed. | Solid label with route marker. |
| `bridge_missing` | A required record is missing. | Warning label; visual must identify custodian and closure step. |
| `source_conflict` | Records conflict. | Conflict label; do not flatten into neutral ambiguity. |
| `ocr_derived` | Text came from OCR/extraction. | OCR label; page image controls wording. |
| `summary_only` | Appears only in memo/report/narrative. | Not evidence-grade by itself. |
| `derived_analysis` | Math/model/inference layer. | Separate from native fact. |
| `counsel_review` | Needs legal/expert review before external use. | Review gate. |

Output format:

```text
Claim:
Status:
Source route:
Missing bridge:
Adverse explanation test:
Visual treatment:
Next closure step:
```

## Skill 2 — Visual Type Router

Use the claim question to select the visual. Do not pick the graphic because it looks impressive.

| Question | Visual |
| --- | --- |
| How does a reviewer navigate the case? | Subway map / case spine. |
| Where did money move? | Sankey + ledger table. |
| How did the claimed balance evolve? | Waterfall. |
| What changed over time? | Timeline with actual spacing. |
| Who controlled what? | Swimlane. |
| What is closed vs missing? | Source-status heatmap. |
| Which records conflict? | Contradiction matrix. |
| What needs discovery? | Bridge closure board. |
| Why does page layout matter? | Page-layout callout. |

## Skill 3 — Accounting Spine Engine

Normalize financial visuals into this spine:

```text
Agreement / represented cost
→ Approved written changes
→ Owner payments
→ Bank draws
→ Builder account movement
→ Vendor invoices
→ Vendor payments
→ Payment application
→ Project allocation
→ Credits / reimbursements
→ Claimed final balance
→ Unexplained or bridge-missing delta
```

Required outputs:

```text
Accounting role:
Money amount:
Date:
Source status:
Native/source locator:
Bridge record needed:
Recommended visual:
```

## Skill 4 — Contradiction Genome

Do not bury contradictions in narrative. Convert them into a structured conflict.

```text
Statement A:
Source A:
Statement B:
Source B:
Conflict type:
Why the conflict matters:
Adverse explanation test:
Bridge record needed:
Deposition question:
Visual treatment:
```

## Skill 5 — Bridge Gap Closer

Every bridge-missing issue gets a closure route.

```text
Pressure point:
Missing bridge record:
Likely custodian:
Demand/subpoena target:
Authentication route:
Deposition question:
Exhibit candidate:
Closure priority:
```

## Skill 6 — Visual Export Gate

Before export, answer:

1. What one question does this visual answer?
2. Which source records control it?
3. Which claims are native-closed?
4. Which are source-routed only?
5. Which are bridge-missing?
6. Which are source conflicts?
7. Are money scales honest?
8. Are dates honestly spaced?
9. Is the audience clear?
10. Is the old version retired or superseded?

## Failure language

Do not end with weak neutralizers. Use source-status conclusions:

- The record supports this pressure point.
- This is source-routed and requires native closure.
- This is bridge-missing.
- This is a source conflict, not a neutral ambiguity.
- The adverse explanation does not close without the missing bridge record.
