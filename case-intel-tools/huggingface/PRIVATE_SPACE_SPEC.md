# Private Router Space Spec

Goal: deploy a private Hugging Face Space that accepts a redacted CSV visual registry, recommends a visual type, and flags rows that are not review-ready.

## Inputs

- `claim_id`
- `case_question`
- `visual_lane`
- `source_status`
- `native_locator` or `drive_file_id`
- `money_amount`
- `bridge_needed`
- `conflict_type`
- `scale_rule`
- `audience`
- `export_status`

## Outputs

- `router_recommended_visual_type`
- `router_issues`
- `router_decision`
- `visual_type_counts`
- `blocked_row_count`
- `review_ready_row_count`

## Routing rules

| Lane | Visual |
| --- | --- |
| case_navigation | subway_map |
| accounting_flow | sankey or waterfall |
| timeline_evolution | timeline |
| source_status | heatmap |
| bridge_closure | bridge_board |
| contradiction | contradiction_matrix |
| deposition | deposition_cascade |
| document_layout | page_layout_callout |

## Review gates

Block export if:

- source status is missing;
- a native/source-routed row lacks a locator;
- a bridge-missing row lacks closure detail;
- a source-conflict row lacks conflict type;
- a row marked export-ready still has summary-only or bridge-missing status.

## Deployment boundary

Deploy privately. Use redacted rows only. The Space routes visual work; it does not close proof or replace native source review.
