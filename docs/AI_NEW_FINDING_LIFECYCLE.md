# AI New Finding Lifecycle

## Purpose

Potentially accurate or strategically valuable AI conclusions should not be reduced to a generic `AI` label. They should be preserved as **AI New Findings** so they can be tested, challenged, sourced, promoted, rejected, or superseded without confusing them with confirmed evidence.

## Core rule

An AI New Finding is a structured investigative lead. It is more valuable than an untracked model note, but it is not a proven fact.

The label must remain visible throughout the review lifecycle. Human confirmation changes the status, not the historical origin.

## Required fields

Every finding should contain:

- stable finding ID;
- proposed finding text;
- why it matters or why it is worth pursuing;
- confidence score;
- supporting evidence-atom IDs;
- exact source anchors;
- source-completeness result;
- questions that test the finding;
- contrary or innocent explanations;
- missing bridge records;
- next investigative actions;
- model or search-run metadata when available;
- review history.

## Status ladder

1. `AI New Finding — Needs Source Anchors`
2. `AI New Finding — Questioned`
3. `AI New Finding — Worth Pursuing`
4. `AI New Finding — Supported, Not Confirmed`
5. `Human-Confirmed Finding`
6. `Rejected / Superseded`

A high confidence score can help route a finding for pursuit, but it cannot skip the source and review gates.

## Questioning requirement

Each finding must ask, at minimum:

1. What exact native record, page, row, transaction, or communication supports it?
2. What evidence would disprove or materially limit it?
3. Does it survive the person, property, loan, account, amount-stage, date, and version firewalls?
4. What innocent or competing explanation should be tested?
5. What missing bridge record would most efficiently resolve the uncertainty?

## Promotion rules

### Worth pursuing

A finding may be marked worth pursuing when it has meaningful support or an exact anchor and either:

- confidence is at least 0.65; or
- a reviewer explicitly chooses `pursue`.

### Supported, not confirmed

Requires source-complete lineage and a recorded native-source check.

### Human confirmed

Requires:

- source-complete evidence lineage;
- native source checked;
- identity firewall checked;
- contrary evidence checked;
- review questions resolved;
- named reviewer and rationale.

No route automatically confirms a finding.

## API

- `GET /api/cases/:id/ai-findings`
- `POST /api/cases/:id/ai-findings`
- `POST /api/cases/:id/ai-findings/:findingId/review`

Review decisions are `pursue`, `support`, `confirm`, or `reject`.

## Drive sync

The recommended Drive lane is `AI_NEW_FINDINGS`, keyed by the stable `AIF-` ID. Drive rows should preserve the status, source anchors, open questions, missing bridges, next actions, and review history. Row position is never identity.
