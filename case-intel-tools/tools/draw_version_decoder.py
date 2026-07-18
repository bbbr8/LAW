#!/usr/bin/env python3
"""Decode redacted document versions into arithmetic, similarity, and routing metadata.

Input JSON contains line_keys, versions, optional support_records, and optional
payment_candidates. This generic tool never reads native evidence. Its outputs are
review routes only: they do not prove chronology, identity, authorization, payment
application, intent, damages, or liability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

BOUNDARY = (
    "Arithmetic, similarity, and routing scores do not prove chronology, identity, "
    "authorization, payment application, intent, damages, or liability."
)


def number(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    return [0.0 for _ in values] if not norm else [value / norm for value in values]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def parse(payload: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    keys = payload.get("line_keys")
    raw_versions = payload.get("versions")
    if not isinstance(keys, list) or not keys or not all(isinstance(key, str) for key in keys):
        raise ValueError("line_keys must be a non-empty string list")
    if not isinstance(raw_versions, list) or len(raw_versions) < 2:
        raise ValueError("versions must contain at least two states")
    versions = []
    seen = set()
    for index, raw in enumerate(raw_versions):
        if not isinstance(raw, dict):
            raise ValueError(f"versions[{index}] must be an object")
        version_id = str(raw.get("version_id", "")).strip()
        if not version_id or version_id in seen:
            raise ValueError("version_id values must be unique and non-empty")
        seen.add(version_id)
        vector = raw.get("amount_vector")
        if not isinstance(vector, list) or len(vector) != len(keys):
            raise ValueError(f"{version_id}.amount_vector must match line_keys")
        versions.append({
            "version_id": version_id,
            "vector": [number(value, f"{version_id}.amount_vector") for value in vector],
            "request_total": number(raw.get("request_total"), f"{version_id}.request_total"),
            "visible_dates": raw.get("visible_dates") or {},
            "source_status": str(raw.get("source_status", "OPEN")),
        })
    return keys, versions


def support_audit(payload: dict[str, Any]) -> dict[str, Any]:
    rows = []
    totals: dict[str, float] = {}
    for index, raw in enumerate(payload.get("support_records") or []):
        if not isinstance(raw, dict):
            raise ValueError(f"support_records[{index}] must be an object")
        amount = number(raw.get("amount"), "support amount")
        version_id = str(raw.get("version_id", "UNASSIGNED"))
        project = str(raw.get("project_id", "OPEN"))
        expected_project = str(raw.get("expected_project_id", project))
        role = str(raw.get("document_role", "OPEN"))
        expected_role = str(raw.get("expected_role", role))
        totals[version_id] = totals.get(version_id, 0.0) + amount
        rows.append({
            "support_id": str(raw.get("support_id", f"SUP-{index + 1:03d}")),
            "version_id": version_id,
            "amount": amount,
            "project_conflict": project != expected_project,
            "role_conflict": role != expected_role,
            "project_id": project,
            "expected_project_id": expected_project,
            "document_role": role,
            "expected_role": expected_role,
        })
    return {
        "totals_by_version": totals,
        "conflicts": [row for row in rows if row["project_conflict"] or row["role_conflict"]],
        "boundary": "Exact arithmetic does not cure project or document-role conflicts.",
    }


def candidate_routes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    weights = {
        "same_day_message": 0.20,
        "same_day_document": 0.20,
        "explicit_purpose_match": 0.25,
        "support_in_package": 0.10,
        "category_present": 0.10,
    }
    output = []
    for index, raw in enumerate(payload.get("payment_candidates") or []):
        difference = abs(number(raw.get("amount_difference", 0), "amount_difference"))
        features = raw.get("features") or {}
        amount_score = max(0.0, 1.0 - difference / 1000.0)
        score = amount_score * 0.15
        contributions = {"amount_nearness": amount_score * 0.15}
        for feature, weight in weights.items():
            value = min(1.0, max(0.0, float(features.get(feature, 0))))
            contributions[feature] = value * weight
            score += contributions[feature]
        output.append({
            "candidate_id": str(raw.get("candidate_id", f"CAND-{index + 1:03d}")),
            "label": str(raw.get("label", "Unnamed candidate")),
            "routing_score": round(score, 6),
            "amount_difference": difference,
            "contributions": {key: round(value, 6) for key, value in contributions.items()},
            "boundary": "Routing priority is not proof of application.",
        })
    return sorted(output, key=lambda row: row["routing_score"], reverse=True)


def decode(payload: dict[str, Any]) -> dict[str, Any]:
    keys, versions = parse(payload)
    checks = []
    for version in versions:
        line_sum = sum(version["vector"])
        checks.append({
            "version_id": version["version_id"],
            "request_total": version["request_total"],
            "line_sum": line_sum,
            "reconciles": math.isclose(line_sum, version["request_total"], abs_tol=0.01),
        })
    deltas = []
    for left, right in zip(versions, versions[1:]):
        changed = []
        for key, before, after in zip(keys, left["vector"], right["vector"]):
            if not math.isclose(before, after, abs_tol=1e-9):
                changed.append({"line_key": key, "left": before, "right": after, "delta": after - before})
        request_delta = right["request_total"] - left["request_total"]
        line_delta = sum(row["delta"] for row in changed)
        deltas.append({
            "left_version_id": left["version_id"],
            "right_version_id": right["version_id"],
            "request_delta": request_delta,
            "line_delta_sum": line_delta,
            "changed_lines": changed,
            "reconciles": math.isclose(request_delta, line_delta, abs_tol=0.01),
        })
    vectors = {version["version_id"]: normalize(version["vector"]) for version in versions}
    similarity = []
    for index, left in enumerate(versions):
        for right in versions[index + 1:]:
            similarity.append({
                "left_version_id": left["version_id"],
                "right_version_id": right["version_id"],
                "cosine_similarity": round(cosine(vectors[left["version_id"]], vectors[right["version_id"]]), 10),
                "boundary": "Similarity routes review and cannot establish chronology or identity.",
            })
    return {
        "schema": "draw-version-decoder/v1",
        "promotion_boundary": BOUNDARY,
        "request_total_checks": checks,
        "version_deltas": deltas,
        "economic_similarity": similarity,
        "support_audit": support_audit(payload),
        "payment_candidate_routing": candidate_routes(payload),
        "chronology_status": "OPEN_UNLESS_NATIVE_EVENT_LOGS_SUPPLIED",
        "required_closure_records": payload.get("required_closure_records", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    result = decode(payload)
    result["input_sha256"] = hashlib.sha256(args.input_json.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
