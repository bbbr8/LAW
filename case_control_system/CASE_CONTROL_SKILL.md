# Case Control System Skill

**Version:** 2026-07-07  
**Build layer:** Fraud Clarity Review Skill expansion  
**Primary use:** Convert evidence review into a controlled proof system for source closure, reliance, money movement, draw authorization, statement contradiction, discovery targeting, exhibit routing, and counsel explanation.

---

## Mission

This skill builds the operational layer above the Fraud Clarity Review Skill. Every fact must be routed into a proof lane, a source-status lane, a money bucket, a bridge-record requirement, a deposition closure question, and an exhibit-card use.

The system answers five counsel-facing questions:

1. What is already source-closed?
2. What is source-routed but still needs native closure?
3. What bridge record must exist if the adverse version is true?
4. What deposition question closes the point?
5. How does this fact help explain fraud indicators, reliance, authorization, money movement, credit treatment, or damages?

---

## Required modules

### Source Closure Matrix

Every record must be assigned one source status:

| Status | Meaning |
|---|---|
| `SOURCE_CLOSED` | Native or direct source supports the point. |
| `SOURCE_ROUTED` | The point is routed to a source family but needs native/metadata/page closure. |
| `BRIDGE_MISSING` | The adverse claim requires a bridge record that has not been produced or found. |
| `SOURCE_CONFLICT` | Two or more records conflict. This is not neutral ambiguity. |
| `DEPOSITION_CLOSURE_NEEDED` | Witness lock-in is needed. |
| `DISCOVERY_TARGET` | A specific document request, subpoena, or production demand should be generated. |

### Decision-Pivot Reliance Binder

Build a dedicated binder titled:

> **Why Bryce Chose the Jeff / Colby / Suited Transaction Instead of the Home He Was Already Buying**

This binder must explain the original path, the replacement pitch, the reliance bridge, what Bryce gave up, who benefited, and how numbers/labels/risk/credit treatment later changed.

### Money Bucket Reconciliation Engine

Every amount must be placed into one or more money buckets: land, signed construction, loan-funded draw, owner cash advance, reimbursement expected, vendor invoice, builder payment, claimed overage, claimed balance, credit owed to Bryce, non-delivered scope, or lien/title payoff.

### Draw Authorization Validator

Every draw record must answer: draw number, date, amount, signature method, owner authorization source, email transmittal, bank recipient, line items, vendor support, payment proof, owner-paid overlap, later litigation use, signature issue, fraud-clarity finding, and bridge record needed.

### Statement-to-Record Contradiction Engine

Every speaker statement must be converted into a testable record issue: statement, context, what it asks the reader to believe, record supporting it, record contradicting it, money affected, reliance affected, bridge record needed, and deposition question.

### Discovery Target Generator

Every `BRIDGE_MISSING`, `SOURCE_CONFLICT`, or `DEPOSITION_CLOSURE_NEEDED` finding must generate a document request, deposition question, native-file/metadata request, bank/vendor/title record request, and explanation of why the record matters.

### Exhibit Card Builder

Every useful document must get an exhibit card: document, date, source status, what it shows, why it matters, fraud-clarity point, money affected, reliance affected, adverse explanation, record response, bridge record needed, counsel use, and deposition question.

### Timeline State Machine

Route records to: original home path, investment/replacement pitch, signed baseline, loan/appraisal support, owner advances, draw submissions, budget expansion, credit confusion, final balance claim, and litigation use.

---

## Writing standard

Use source-status language. Do not soften source-supported pressure points.

Use:

- `SOURCE_CLOSED`
- `SOURCE_ROUTED`
- `BRIDGE_MISSING`
- `SOURCE_CONFLICT`
- `DEPOSITION_CLOSURE_NEEDED`
- `DISCOVERY_TARGET`
- “Record supports this pressure point.”
- “The adverse explanation requires the following bridge record.”

The correct issue is not timid proof language. The correct issue is source status.

---

## Master workflow prompt

```text
Evaluate this record under the Case Control System Skill.

Do not summarize only.

For each record, identify:
1. the representation, omission, number, label, payment, authorization, or contradiction;
2. what Bryce likely understood at the time;
3. what later changed;
4. whether the fact affects reliance, money, authorization, credit, debt, lien risk, or damages;
5. who benefited from the changed meaning;
6. whether this is SOURCE_CLOSED, SOURCE_ROUTED, BRIDGE_MISSING, SOURCE_CONFLICT, DEPOSITION_CLOSURE_NEEDED, or DISCOVERY_TARGET;
7. the exact bridge record required if the adverse version is true;
8. the plain-English explanation for counsel;
9. the deposition question that would close the point;
10. the exhibit-card summary.
```
