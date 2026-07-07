#!/usr/bin/env python3
"""Route case data to the correct visual type.

This tool is intentionally evidence-safe: it works from column names, intent,
and source-status metadata. It does not need raw evidence.

Examples:
    python chart_decision_router.py --intent accounting_flow --columns date,amount,payor,payee,source_status
    python chart_decision_router.py --intent contradiction --columns statement_a,statement_b,source_status,conflict_type
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from typing import Iterable, Set


@dataclass(frozen=True)
class ChartRoute:
    intent: str
    recommended_visual_type: str
    reason: str
    required_fields: list[str]
    source_status_requirement: str
    scale_rule: str
    warning: str | None = None


def normalize_columns(columns: Iterable[str]) -> Set[str]:
    return {c.strip().lower().replace(" ", "_") for c in columns if c.strip()}


def has_any(columns: Set[str], names: Iterable[str]) -> bool:
    return any(name in columns for name in names)


def choose_chart_type(intent: str, columns: Set[str]) -> ChartRoute:
    intent_key = intent.strip().lower().replace(" ", "_")
    has_date = has_any(columns, ["date", "date_start", "date_end", "event_date"])
    has_amount = has_any(columns, ["amount", "money_amount", "debit", "credit", "balance"])
    has_flow = has_any(columns, ["from", "to", "payor", "payee", "source", "target"])
    has_status = "source_status" in columns
    has_conflict = has_any(columns, ["conflict_type", "statement_a", "statement_b"])
    has_bridge = has_any(columns, ["bridge_needed", "missing_bridge", "custodian", "next_action"])

    if intent_key in {"case_navigation", "navigation", "overview", "case_spine"}:
        return ChartRoute(
            intent=intent,
            recommended_visual_type="subway_map",
            reason="Navigation needs stable route structure, not a decorative network graph.",
            required_fields=["stage", "label", "source_status", "next_stage"],
            source_status_requirement="Every node needs a source-status chip.",
            scale_rule="not_applicable",
            warning=None if has_status else "Missing source_status column.",
        )

    if intent_key in {"accounting_flow", "money_flow", "funds_flow"}:
        if has_amount and has_flow:
            visual = "sankey"
            reason = "Money movement requires direction plus amount."
        elif has_amount:
            visual = "waterfall"
            reason = "Amounts without direction are better for reconciliation/change in balance."
        else:
            visual = "table"
            reason = "Accounting visual lacks amount fields; table first, chart later."
        return ChartRoute(
            intent=intent,
            recommended_visual_type=visual,
            reason=reason,
            required_fields=["date", "money_amount", "accounting_role", "source_status", "native_locator"],
            source_status_requirement="Amounts must distinguish native bank record, invoice, derived math, and bridge-missing rows.",
            scale_rule="zero_baseline_required",
            warning=None if has_status else "Missing source_status column.",
        )

    if intent_key in {"timeline", "evolution", "workstream_evolution"}:
        return ChartRoute(
            intent=intent,
            recommended_visual_type="timeline",
            reason="Evolution questions require chronological order and disclosed date spacing.",
            required_fields=["date", "event", "lane", "source_status"],
            source_status_requirement="Each event needs source status and locator.",
            scale_rule="actual_date_spacing" if has_date else "categorical_spacing_disclosed",
            warning=None if has_date else "No date column; disclose categorical spacing.",
        )

    if intent_key in {"source_status", "proof_status", "closure"}:
        return ChartRoute(
            intent=intent,
            recommended_visual_type="heatmap",
            reason="Closure questions need matrix visibility across lanes and statuses.",
            required_fields=["lane", "pressure_point", "source_status", "required_closure"],
            source_status_requirement="Source status is the main encoded variable.",
            scale_rule="not_applicable",
            warning=None if has_status else "Missing source_status column.",
        )

    if intent_key in {"bridge", "bridge_gap", "discovery", "closure_board"} or has_bridge:
        return ChartRoute(
            intent=intent,
            recommended_visual_type="bridge_board",
            reason="Missing proof should become an action board, not a narrative footnote.",
            required_fields=["pressure_point", "bridge_needed", "likely_custodian", "next_action", "source_status"],
            source_status_requirement="Bridge-missing rows must identify custodian and closure path.",
            scale_rule="not_applicable",
            warning=None if has_status else "Missing source_status column.",
        )

    if intent_key in {"contradiction", "conflict", "deposition"} or has_conflict:
        visual = "deposition_cascade" if intent_key == "deposition" else "contradiction_matrix"
        return ChartRoute(
            intent=intent,
            recommended_visual_type=visual,
            reason="Conflicts need side-by-side source comparison and follow-up questions.",
            required_fields=["statement_a", "source_a", "statement_b", "source_b", "conflict_type", "deposition_question"],
            source_status_requirement="Do not flatten source conflict into neutral ambiguity.",
            scale_rule="not_applicable",
            warning=None if has_status else "Add source_status or per-source status fields.",
        )

    if intent_key in {"document_layout", "signature", "draw_packet", "invoice_layout"}:
        return ChartRoute(
            intent=intent,
            recommended_visual_type="page_layout_callout",
            reason="Visual-document meaning requires page layout, not OCR-only text.",
            required_fields=["document_type", "page_locator", "visual_issue", "source_status"],
            source_status_requirement="Page image/native document controls the visual claim.",
            scale_rule="not_applicable",
            warning=None if has_status else "Missing source_status column.",
        )

    return ChartRoute(
        intent=intent,
        recommended_visual_type="table",
        reason="Intent is not specific enough for a higher-order chart. Start with a table and route again.",
        required_fields=["case_question", "source_status", "native_locator", "recommended_visual_type"],
        source_status_requirement="Every row needs source status before visual design.",
        scale_rule="not_applicable",
        warning="Unknown intent; use table until the question is narrowed.",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Route case data to the correct chart/diagram type.")
    parser.add_argument("--intent", required=True, help="Case question intent, e.g. accounting_flow or contradiction")
    parser.add_argument("--columns", required=True, help="Comma-separated column names available in the data")
    args = parser.parse_args()

    columns = normalize_columns(args.columns.split(","))
    route = choose_chart_type(args.intent, columns)
    print(json.dumps(asdict(route), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
