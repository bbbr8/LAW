#!/usr/bin/env python3
"""Audit a visual registry CSV for evidence-control and design-readiness defects.

The linter is deliberately conservative. It does not certify a chart as true;
it checks whether the registry row carries the minimum source-status, scale,
audience, and export controls required before visual design.

Example:
    python visual_registry_linter.py synthetic_samples/visual_registry_sample.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

VALID_SOURCE_STATUS = {
    "native_closed",
    "source_routed",
    "bridge_missing",
    "source_conflict",
    "ocr_derived",
    "summary_only",
    "derived_analysis",
    "counsel_review",
}

VALID_EXPORT_STATUS = {
    "draft",
    "needs_source_closure",
    "needs_design_fix",
    "review_ready",
    "export_ready",
    "retired_superseded",
}

REQUIRED_COLUMNS = {
    "claim_id",
    "case_question",
    "visual_lane",
    "recommended_visual_type",
    "source_status",
    "scale_rule",
    "audience",
    "export_status",
}

SOURCE_LOCATOR_COLUMNS = {"native_locator", "drive_file_id", "source_locator"}


@dataclass
class Finding:
    row_number: int
    claim_id: str
    severity: str
    code: str
    message: str


def clean(value: object) -> str:
    return str(value or "").strip()


def normalize_header(header: Iterable[str]) -> list[str]:
    return [h.strip().lower().replace(" ", "_") for h in header]


def audit_row(row_number: int, row: dict[str, str]) -> list[Finding]:
    claim_id = clean(row.get("claim_id")) or f"ROW_{row_number}"
    findings: list[Finding] = []

    def add(severity: str, code: str, message: str) -> None:
        findings.append(Finding(row_number, claim_id, severity, code, message))

    source_status = clean(row.get("source_status"))
    export_status = clean(row.get("export_status"))
    scale_rule = clean(row.get("scale_rule"))
    question = clean(row.get("case_question"))
    visual_type = clean(row.get("recommended_visual_type"))
    lane = clean(row.get("visual_lane"))

    if len(question) < 12:
        add("error", "QUESTION_MISSING", "Controlling case question is missing or too vague.")

    if source_status not in VALID_SOURCE_STATUS:
        add("error", "BAD_SOURCE_STATUS", f"Invalid or missing source_status: {source_status!r}.")

    has_locator = any(clean(row.get(col)) for col in SOURCE_LOCATOR_COLUMNS)
    if source_status in {"native_closed", "source_routed", "ocr_derived"} and not has_locator:
        add("error", "LOCATOR_MISSING", "Native/source-routed/OCR-derived rows need a locator.")

    if source_status == "bridge_missing" and not clean(row.get("bridge_needed")):
        add("error", "BRIDGE_DETAIL_MISSING", "Bridge-missing row needs bridge_needed detail.")

    if source_status == "source_conflict" and not clean(row.get("conflict_type")):
        add("error", "CONFLICT_TYPE_MISSING", "Source-conflict row needs conflict_type.")

    if export_status not in VALID_EXPORT_STATUS:
        add("error", "BAD_EXPORT_STATUS", f"Invalid or missing export_status: {export_status!r}.")

    if export_status == "export_ready" and source_status in {"summary_only", "bridge_missing"}:
        add("error", "EXPORT_READY_OVERCLAIM", "Summary-only or bridge-missing rows cannot be export_ready without review override.")

    if lane in {"accounting_flow", "timeline_evolution"} and scale_rule in {"", "not_applicable"}:
        add("warning", "SCALE_RULE_WEAK", "Accounting/timeline visuals need disclosed scale/date spacing.")

    if visual_type in {"sankey", "waterfall"} and not clean(row.get("money_amount")):
        add("warning", "AMOUNT_MISSING", "Money visual lacks money_amount.")

    if visual_type == "timeline" and not (clean(row.get("date_start")) or clean(row.get("date"))):
        add("warning", "DATE_MISSING", "Timeline row lacks date/date_start.")

    if clean(row.get("overlap_flag")).lower() in {"yes", "true", "1"}:
        add("error", "VISUAL_OVERLAP", "Registry marks overlap. Not export-ready.")

    if clean(row.get("wrong_chart_flag")).lower() in {"yes", "true", "1"}:
        add("error", "WRONG_CHART_TYPE", "Registry marks wrong chart type. Reroute before export.")

    return findings


def audit_csv(path: Path) -> tuple[list[Finding], dict[str, int]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            raw_header = next(reader)
        except StopIteration:
            raise ValueError("CSV is empty")

        header = normalize_header(raw_header)
        missing = sorted(REQUIRED_COLUMNS - set(header))
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        rows = [dict(zip(header, values)) for values in reader]

    findings: list[Finding] = []
    for idx, row in enumerate(rows, start=2):
        findings.extend(audit_row(idx, row))

    counts = {
        "rows": len(rows),
        "errors": sum(1 for f in findings if f.severity == "error"),
        "warnings": sum(1 for f in findings if f.severity == "warning"),
    }
    return findings, counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint a case visual registry CSV.")
    parser.add_argument("csv_path", help="Path to visual registry CSV")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of readable text")
    args = parser.parse_args()

    path = Path(args.csv_path)
    try:
        findings, counts = audit_csv(path)
    except Exception as exc:  # noqa: BLE001 - CLI should show clean error
        print(f"fatal: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"summary": counts, "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        print(f"rows={counts['rows']} errors={counts['errors']} warnings={counts['warnings']}")
        for finding in findings:
            print(f"{finding.severity.upper()} row={finding.row_number} claim={finding.claim_id} {finding.code}: {finding.message}")

    return 1 if counts["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
