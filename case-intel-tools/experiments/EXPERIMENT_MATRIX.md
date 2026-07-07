# Experiment Matrix

Status: controlled experiments for redacted or synthetic case-intel rows.

## Experiment 1 — Visual Registry Fire Drill

Hypothesis: a redacted registry can be routed without source files in GitHub.

Input: `synthetic_samples/visual_registry_sample.csv`.

Tools: quality gate, scorecard, chart router.

Pass condition: CI passes and no raw evidence is required.

Output: pass/fail JSON, source-status counts, visual route.

## Experiment 2 — Bridge Closure Board

Hypothesis: bridge-missing rows can become action-board rows automatically.

Input: redacted registry with `bridge_missing` or `bridge_needed` fields.

Tool: `bridge_board_generator.py`.

Pass condition: every bridge row gets missing bridge, custodian placeholder, next action, and export status.

Output: bridge-board JSON or CSV.

## Experiment 3 — Evidence Graph Export

Hypothesis: relationship review can be handled as graph JSON instead of a cluttered visual.

Input: redacted registry rows.

Tool: `evidence_graph_exporter.py`.

Pass condition: claims connect to lane, source status, visual type, source locator, and bridge nodes.

Output: graph JSON for later visualization.

## Experiment 4 — Case Spine Preview

Hypothesis: a quick Mermaid spine can preview navigation before Figma design.

Input: rows with `stage_id`, `label`, `next_stage`, `source_status`.

Tool: `mermaid_case_spine_generator.py`.

Pass condition: Mermaid output is readable and source-status styled.

Output: Mermaid `flowchart LR`.

## Experiment 5 — Markdown Review Packet

Hypothesis: a plain Markdown report can summarize registry status before design work.

Input: redacted registry rows.

Tool: `registry_markdown_report.py`.

Pass condition: report lists counts, action rows, and boundary language.

Output: Markdown review note.

## Experiment 6 — HF Visual-Native Routing

Hypothesis: layout-sensitive pages can be flagged before OCR-derived values are charted.

Input: redacted visual-document metadata only.

Tool: HF private layout-router spec.

Pass condition: record routes to visual-document lane with review-required status.

Output: visual-native-required queue.

## Experiment 7 — Figma Token Handoff

Hypothesis: source-status tokens can make visual status consistent across diagrams.

Input: `figma/source_status_tokens.json`.

Tool: Figma component build spec.

Pass condition: every visual frame can display status, export rule, and audience.

Output: Figma source-status chip and component system.

## Boundary

These experiments route, score, summarize, and design-review redacted registry rows. They do not close source proof, authenticate records, calculate final accounting, or replace professional review.
