# Question and Discovery Router

Status: reusable review skill for turning source-status findings into focused questions and record requests.

## Purpose

This skill converts a pressure point into a tight review sequence. It avoids broad narrative questions and forces the missing record, conflicting record, source route, and next action into view.

## Question ladder

Use this sequence:

```text
1. Identify the claim.
2. Identify the source status.
3. Identify the record family.
4. Identify the missing bridge.
5. Identify the likely custodian.
6. Ask the authentication question.
7. Ask the accounting/application question.
8. Ask the timeline question.
9. Ask the contradiction question.
10. Route the answer to an exhibit or closure task.
```

## Output template

```text
Pressure point:
Source status:
Record family:
Native/source locator:
Missing bridge:
Likely custodian:
First question:
Follow-up question:
Document request:
Visual lane:
Closure action:
```

## Record families

| Family | Use |
| --- | --- |
| agreement | starting representation and written-change structure |
| payment | money movement and application |
| draw | lender/funding packet route |
| invoice | vendor billing support |
| account | bank/account activity |
| communication | what was told, shown, sent, or relied on |
| visual_document | layout, signature-page, table, or attribution issue |
| final_accounting | credits, reimbursements, balances, and reconciliation |

## Source-status routing

| Status | Question posture |
| --- | --- |
| native_closed | lock the point, then test explanation |
| source_routed | ask for native closure |
| bridge_missing | ask who has the missing bridge record |
| source_conflict | ask why the records do not reconcile |
| ocr_derived | ask for the page image/native wording |
| summary_only | ask for the source behind the summary |
| derived_analysis | ask for the native inputs and formula |
| review_needed | hold for attorney/expert review before external use |

## Bad questions to avoid

Do not ask vague questions like:

- What happened here?
- Is this fraud?
- Why did you do that?
- Can you explain the accounting?

Replace with precise questions:

- Identify the native record supporting this amount.
- Identify where this payment was applied.
- Identify the written approval for this change.
- Identify the draw packet page that used this figure.
- Identify the record that reconciles these two amounts.
- Identify who controlled the missing record.

## Visual tie-in

Every question should map to a visual lane:

```text
source conflict -> contradiction matrix
missing record -> bridge board
money movement -> sankey or waterfall
timeline issue -> timeline
page layout issue -> page-layout callout
case navigation -> subway map
```
