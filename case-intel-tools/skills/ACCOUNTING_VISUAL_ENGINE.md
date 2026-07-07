# Accounting Visual Engine

Status: reusable accounting-visual reasoning layer for redacted or synthetic registry rows.

## Purpose

This skill turns money records into visuals that are clear, scaled correctly, and source-status controlled. It blocks vague charts that compare amounts without showing how the money was represented, requested, moved, applied, credited, or left unresolved.

## Accounting spine

Use this order unless the user asks for a narrow slice:

```text
Starting agreement
→ approved written changes
→ owner payments
→ lender or funding draws
→ operating account movement
→ vendor invoices
→ vendor payments
→ payment application
→ project allocation
→ credits or reimbursements
→ stated final balance
→ unexplained or bridge-missing delta
```

## Visual selection

| Question | Primary visual | Companion visual |
| --- | --- | --- |
| Where did funds move? | Sankey | ledger detail table |
| How did a balance change? | Waterfall | source-status notes |
| Which records support each amount? | Source matrix | evidence cards |
| Which amounts are native vs derived? | Status heatmap | calculation notes |
| Which amount needs closure? | Bridge board | custodian list |

## Money row contract

Every row should carry:

```text
row_id
money_role
date
amount
from_actor
to_actor
account_or_source
source_status
source_locator
calculation_status
bridge_needed
visual_type
scale_rule
export_status
```

## Scale rules

1. Bar and waterfall visuals use a zero baseline unless a nonzero baseline is clearly disclosed.
2. Sankey widths represent amount. If amounts are incomplete, use equal-width conceptual flow and label it as conceptual.
3. Timeline money events use actual dates unless the chart says categorical sequence.
4. Derived calculations must be labeled derived-analysis and separated from native facts.
5. Unknown or missing amounts stay in a bridge board, not a money chart.

## Pressure language

Use direct source-status conclusions:

- The row is native-closed.
- The amount is source-routed but requires closure.
- The amount is bridge-missing.
- The records create a source conflict.
- The adverse explanation does not close the accounting chain without the missing bridge row.

## Export gate

A money visual is export-ready only if:

- the controlling accounting question is stated;
- every displayed amount has a source status;
- missing amounts are labeled bridge-missing;
- derived math is separated from native records;
- scale rule is disclosed;
- audience is defined;
- old versions are retired or superseded.
