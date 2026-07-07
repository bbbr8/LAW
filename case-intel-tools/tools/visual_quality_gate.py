#!/usr/bin/env python3
"""Run a full quality gate over a redacted visual registry CSV."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

VALID_STATUS = {
    "native_closed",
    "source_routed",
    "bridge_missing",
    "source_conflict",
    "ocr_derived",
    "summary_only",
    "derived_analysis",
    "counsel_review",
}

VALID_EXPORT = {
    "draft",
    "needs_source_closure",
    "needs_design_fix",
    "review_ready",
    "export_ready",
    "retired_superseded",
}

BLOCKING_STATUS = {"bridge_missing", "source_conflict", "summary_only"}


def norm(value):
    return str(value or "").strip().lower().replace(" ", "_")


def read_rows(path):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [norm(name) for name in (reader.fieldnames or [])]
        return list(reader)


def audit(rows):
    errors = []
    warnings = []
    status_counts = Counter()
    visual_counts = Counter()
    lane_counts = Counter()

    for idx, row in enumerate(rows, start=2):
        claim_id = str(row.get("claim_id") or f"row_{idx}").strip()
        status = norm(row.get("source_status"))
        export_status = norm(row.get("export_status"))
        visual = norm(row.get("recommended_visual_type")) or "missing"
        lane = norm(row.get("visual_lane")) or "missing"
        locator = str(row.get("native_locator") or row.get("drive_file_id") or row.get("source_locator") or "").strip()
        question = str(row.get("case_question") or "").strip()

        status_counts[status or "missing"] += 1
        visual_counts[visual] += 1
        lane_counts[lane] += 1

        def err(code, message):
            errors.append({"row": idx, "claim_id": claim_id, "code": code, "message": message})

        def warn(code, message):
            warnings.append({"row": idx, "claim_id": claim_id, "code": code, "message": message})

        if len(question) < 12:
            err("QUESTION_MISSING", "case_question is missing or too short")
        if status not in VALID_STATUS:
            err("STATUS_INVALID", "source_status is missing or invalid")
        if export_status not in VALID_EXPORT:
            err("EXPORT_INVALID", "export_status is missing or invalid")
        if status in {"native_closed", "source_routed", "ocr_derived"} and not locator:
            err("LOCATOR_MISSING", "source-routed row lacks locator")
        if status == "bridge_missing" and not str(row.get("bridge_needed") or "").strip():
            err("BRIDGE_MISSING_DETAIL", "bridge_missing row lacks bridge_needed")
        if status == "source_conflict" and not str(row.get("conflict_type") or "").strip():
            err("CONFLICT_TYPE_MISSING", "source_conflict row lacks conflict_type")
        if export_status == "export_ready" and status in BLOCKING_STATUS:
            err("EXPORT_OVERCLAIM", "blocking source status cannot be export_ready")
        if lane in {"accounting_flow", "timeline_evolution"} and norm(row.get("scale_rule")) in {"", "not_applicable"}:
            warn("SCALE_RULE_WEAK", "accounting/timeline row needs scale or date-spacing disclosure")
        if norm(row.get("overlap_flag")) in {"true", "yes", "1"}:
            err("OVERLAP_FLAG", "visual overlap blocks export")
        if norm(row.get("wrong_chart_flag")) in {"true", "yes", "1"}:
            err("WRONG_CHART", "wrong chart flag blocks export")

    return {
        "passed": len(errors) == 0,
        "row_count": len(rows),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "status_counts": dict(status_counts),
        "visual_counts": dict(visual_counts),
        "lane_counts": dict(lane_counts),
        "errors": errors,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="Run visual registry quality gate.")
    parser.add_argument("csv_path")
    args = parser.parse_args()
    result = audit(read_rows(args.csv_path))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
