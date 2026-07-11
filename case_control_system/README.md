# Case Control System — Fraud Clarity Expansion

This package adds the operational proof-control layer above the Fraud Clarity Review Skill.

## What it builds

- Source Closure Matrix
- Decision-Pivot Reliance Binder
- Money Bucket Reconciliation Engine
- Draw Authorization Validator
- Statement-to-Record Contradiction Ledger
- Discovery Target Generator
- Exhibit Card Builder
- Timeline State Machine
- Non-Delivered Scope Ledger
- Bank / Gatekeeper Lane

## Run

```bash
python case_control_system/scripts/case_control_engine.py case_control_system/examples/sample_evidence.json --out-dir case_control_out --focus all
```

## Input formats

- JSON
- JSONL
- CSV
- TXT
- Markdown

## Output

The engine writes structured Markdown, CSV, and JSONL files into the selected output folder.

## Use standard

This is a source-status and bridge-record system. It separates source-closed facts, source-routed facts, bridge-missing issues, source conflicts, deposition closure points, and discovery targets.
