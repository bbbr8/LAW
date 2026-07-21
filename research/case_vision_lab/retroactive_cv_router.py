#!/usr/bin/env python3
"""Retroactive, source-bound evaluation for document computer vision.

This module records model observations without storing raw case evidence, then
re-scores those observations when later evidence or human review establishes a
better label. It is intentionally conservative: similarity and confidence never
become case facts, and all promotion decisions remain review-gated.

The SQLite database stores hashes, bounded metadata, labels, confidence scores,
and review events. Do not put privileged text, images, credentials, or native
case bytes into any CLI argument or JSON field.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "1.0"
ABSTAIN_LABELS = {"", "abstain", "unknown", "unresolved", "needs_review"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def bounded_json(value: Any, *, max_bytes: int = 16_384) -> str:
    encoded = canonical_json(value)
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError(f"metadata exceeds {max_bytes} bytes")
    return encoded


def clamp_confidence(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("confidence must be finite")
    if value < 0.0 or value > 1.0:
        raise ValueError("confidence must be in [0, 1]")
    return float(value)


def require_sha256(value: str, *, field: str) -> str:
    normalized = value.strip().lower()
    if not SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field} must be a 64-character SHA-256 hex digest")
    return normalized


def require_immutable_revision(value: str) -> str:
    normalized = value.strip().lower()
    if not COMMIT_SHA_RE.fullmatch(normalized):
        raise ValueError("model_revision must be an immutable 40-character commit SHA")
    return normalized


@dataclass(frozen=True)
class Observation:
    observation_id: str
    source_hash: str
    model_name: str
    model_revision: str
    task: str
    document_type: str
    predicted_label: str
    confidence: float
    region: Mapping[str, float] | None
    features: Mapping[str, Any]
    created_at: str


@dataclass(frozen=True)
class Resolution:
    resolution_id: str
    observation_id: str
    resolved_label: str
    relation: str
    anchor_hash: str
    reviewer: str
    notes: str
    created_at: str


class VisionEvalStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "VisionEvalStore":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS observations (
                observation_id TEXT PRIMARY KEY,
                source_hash TEXT NOT NULL,
                model_name TEXT NOT NULL,
                model_revision TEXT NOT NULL,
                task TEXT NOT NULL,
                document_type TEXT NOT NULL,
                predicted_label TEXT NOT NULL,
                confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
                region_json TEXT,
                features_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resolutions (
                resolution_id TEXT PRIMARY KEY,
                observation_id TEXT NOT NULL REFERENCES observations(observation_id),
                resolved_label TEXT NOT NULL,
                relation TEXT NOT NULL,
                anchor_hash TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reevaluations (
                reevaluation_id TEXT PRIMARY KEY,
                observation_id TEXT NOT NULL REFERENCES observations(observation_id),
                resolution_id TEXT NOT NULL REFERENCES resolutions(resolution_id),
                outcome TEXT NOT NULL,
                exact_match INTEGER NOT NULL,
                confidence_error REAL NOT NULL,
                route TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(observation_id, resolution_id)
            );

            CREATE INDEX IF NOT EXISTS idx_obs_model_task
                ON observations(model_name, model_revision, task, document_type);
            CREATE INDEX IF NOT EXISTS idx_res_obs_time
                ON resolutions(observation_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_reeval_route
                ON reevaluations(route, outcome);
            """
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
        self.conn.commit()

    def record_observation(
        self,
        *,
        source_hash: str,
        model_name: str,
        model_revision: str,
        task: str,
        document_type: str,
        predicted_label: str,
        confidence: float,
        region: Mapping[str, float] | None = None,
        features: Mapping[str, Any] | None = None,
        created_at: str | None = None,
    ) -> Observation:
        created_at = created_at or utc_now()
        confidence = clamp_confidence(confidence)
        source_hash = require_sha256(source_hash, field="source_hash")
        model_revision = require_immutable_revision(model_revision)
        features = dict(features or {})
        normalized_region = self._validate_region(region)
        identity = {
            "source_hash": source_hash,
            "model_name": model_name,
            "model_revision": model_revision,
            "task": task,
            "document_type": document_type,
            "predicted_label": predicted_label.strip(),
            "confidence": confidence,
            "region": normalized_region,
            "features": features,
            "created_at": created_at,
        }
        observation_id = f"obs_{stable_hash(identity)[:24]}"
        observation = Observation(observation_id=observation_id, **identity)
        self.conn.execute(
            """
            INSERT OR IGNORE INTO observations(
                observation_id, source_hash, model_name, model_revision, task,
                document_type, predicted_label, confidence, region_json,
                features_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.observation_id,
                observation.source_hash,
                observation.model_name,
                observation.model_revision,
                observation.task,
                observation.document_type,
                observation.predicted_label,
                observation.confidence,
                bounded_json(observation.region) if observation.region else None,
                bounded_json(observation.features),
                observation.created_at,
            ),
        )
        self.conn.commit()
        return observation

    def add_resolution(
        self,
        *,
        observation_id: str,
        resolved_label: str,
        relation: str,
        anchor_hash: str,
        reviewer: str,
        notes: str = "",
        created_at: str | None = None,
    ) -> Resolution:
        created_at = created_at or utc_now()
        if not self.conn.execute(
            "SELECT 1 FROM observations WHERE observation_id = ?", (observation_id,)
        ).fetchone():
            raise KeyError(f"unknown observation_id: {observation_id}")
        payload = {
            "observation_id": observation_id,
            "resolved_label": resolved_label.strip(),
            "relation": relation.strip(),
            "anchor_hash": require_sha256(anchor_hash, field="anchor_hash"),
            "reviewer": reviewer.strip(),
            "notes": notes.strip(),
            "created_at": created_at,
        }
        resolution_id = f"res_{stable_hash(payload)[:24]}"
        resolution = Resolution(resolution_id=resolution_id, **payload)
        self.conn.execute(
            """
            INSERT OR IGNORE INTO resolutions(
                resolution_id, observation_id, resolved_label, relation,
                anchor_hash, reviewer, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(asdict(resolution).values()),
        )
        self.conn.commit()
        return resolution

    def reevaluate_pending(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT o.*, r.resolution_id, r.resolved_label, r.relation,
                   r.anchor_hash, r.reviewer, r.notes, r.created_at AS resolved_at
            FROM observations o
            JOIN resolutions r ON r.observation_id = o.observation_id
            LEFT JOIN reevaluations e
              ON e.observation_id = o.observation_id
             AND e.resolution_id = r.resolution_id
            WHERE e.reevaluation_id IS NULL
            ORDER BY r.created_at, o.created_at
            """
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            result = self._score(row)
            self.conn.execute(
                """
                INSERT INTO reevaluations(
                    reevaluation_id, observation_id, resolution_id, outcome,
                    exact_match, confidence_error, route, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result["reevaluation_id"],
                    result["observation_id"],
                    result["resolution_id"],
                    result["outcome"],
                    int(result["exact_match"]),
                    result["confidence_error"],
                    result["route"],
                    result["reason"],
                    result["created_at"],
                ),
            )
            results.append(result)
        self.conn.commit()
        return results

    def report(self) -> dict[str, Any]:
        group_rows = self.conn.execute(
            """
            SELECT o.model_name, o.model_revision, o.task, o.document_type,
                   COUNT(*) AS n,
                   AVG(e.exact_match) AS accuracy,
                   AVG(e.confidence_error) AS mean_confidence_error,
                   SUM(CASE WHEN e.outcome = 'false_positive' THEN 1 ELSE 0 END) AS false_positives,
                   SUM(CASE WHEN e.outcome = 'false_negative' THEN 1 ELSE 0 END) AS false_negatives,
                   SUM(CASE WHEN e.route = 'disable_or_retrain' THEN 1 ELSE 0 END) AS critical_routes
            FROM reevaluations e
            JOIN observations o ON o.observation_id = e.observation_id
            GROUP BY o.model_name, o.model_revision, o.task, o.document_type
            ORDER BY accuracy ASC, n DESC
            """
        ).fetchall()
        groups = [dict(row) for row in group_rows]
        confidence_values = [
            row["confidence"]
            for row in self.conn.execute(
                """
                SELECT o.confidence
                FROM observations o JOIN reevaluations e USING(observation_id)
                """
            ).fetchall()
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "counts": {
                "observations": self._count("observations"),
                "resolutions": self._count("resolutions"),
                "reevaluations": self._count("reevaluations"),
            },
            "confidence": {
                "mean": statistics.fmean(confidence_values) if confidence_values else None,
                "median": statistics.median(confidence_values) if confidence_values else None,
            },
            "groups": groups,
            "policy": {
                "raw_case_bytes_stored": False,
                "automatic_fact_promotion": False,
                "human_review_required": True,
            },
        }

    def _count(self, table: str) -> int:
        allowed = {"observations", "resolutions", "reevaluations"}
        if table not in allowed:
            raise ValueError("invalid table")
        return int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    @staticmethod
    def _validate_region(region: Mapping[str, float] | None) -> Mapping[str, float] | None:
        if region is None:
            return None
        required = {"x", "y", "width", "height"}
        if set(region) != required:
            raise ValueError(f"region keys must be exactly {sorted(required)}")
        result = {key: float(region[key]) for key in required}
        if any(not math.isfinite(value) for value in result.values()):
            raise ValueError("region values must be finite")
        if result["width"] <= 0 or result["height"] <= 0:
            raise ValueError("region width and height must be positive")
        return result

    @staticmethod
    def _score(row: sqlite3.Row) -> dict[str, Any]:
        predicted = row["predicted_label"].strip().lower()
        resolved = row["resolved_label"].strip().lower()
        confidence = float(row["confidence"])
        prediction_abstained = predicted in ABSTAIN_LABELS
        resolution_abstained = resolved in ABSTAIN_LABELS
        exact_match = predicted == resolved and not resolution_abstained

        if resolution_abstained:
            outcome = "still_unresolved"
            target = 0.5
            route = "hold"
            reason = "Later review did not establish a usable resolved label."
        elif prediction_abstained:
            outcome = "false_negative"
            target = 0.0
            route = "inspect_recall_gap"
            reason = "The model abstained where later evidence established a label."
        elif exact_match:
            outcome = "true_positive"
            target = 1.0
            route = "retain_with_monitoring"
            reason = "Prediction matched the later resolved label."
        else:
            outcome = "false_positive"
            target = 0.0
            route = "disable_or_retrain" if confidence >= 0.85 else "tighten_threshold"
            reason = "Prediction conflicted with the later resolved label."

        confidence_error = abs(confidence - target)
        created_at = utc_now()
        reevaluation_id = "reeval_" + stable_hash(
            {
                "observation_id": row["observation_id"],
                "resolution_id": row["resolution_id"],
                "outcome": outcome,
                "created_at": created_at,
            }
        )[:24]
        return {
            "reevaluation_id": reevaluation_id,
            "observation_id": row["observation_id"],
            "resolution_id": row["resolution_id"],
            "outcome": outcome,
            "exact_match": exact_match,
            "confidence_error": confidence_error,
            "route": route,
            "reason": reason,
            "created_at": created_at,
        }


def load_json_argument(value: str) -> Any:
    path = Path(value)
    if path.exists() and path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def emit(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="case_vision_eval.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    observe = sub.add_parser("observe")
    observe.add_argument("--source-hash", required=True)
    observe.add_argument("--model", required=True)
    observe.add_argument("--revision", required=True)
    observe.add_argument("--task", required=True)
    observe.add_argument("--document-type", default="unknown")
    observe.add_argument("--label", required=True)
    observe.add_argument("--confidence", type=float, required=True)
    observe.add_argument("--region-json")
    observe.add_argument("--features-json", default="{}")

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--observation-id", required=True)
    resolve.add_argument("--label", required=True)
    resolve.add_argument("--relation", required=True)
    resolve.add_argument("--anchor-hash", required=True)
    resolve.add_argument("--reviewer", required=True)
    resolve.add_argument("--notes", default="")

    sub.add_parser("reevaluate")
    sub.add_parser("report")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with VisionEvalStore(args.db) as store:
            store.init()
            if args.command == "init":
                emit({"database": str(store.db_path), "schema_version": SCHEMA_VERSION})
            elif args.command == "observe":
                observation = store.record_observation(
                    source_hash=args.source_hash,
                    model_name=args.model,
                    model_revision=args.revision,
                    task=args.task,
                    document_type=args.document_type,
                    predicted_label=args.label,
                    confidence=args.confidence,
                    region=load_json_argument(args.region_json) if args.region_json else None,
                    features=load_json_argument(args.features_json),
                )
                emit(asdict(observation))
            elif args.command == "resolve":
                resolution = store.add_resolution(
                    observation_id=args.observation_id,
                    resolved_label=args.label,
                    relation=args.relation,
                    anchor_hash=args.anchor_hash,
                    reviewer=args.reviewer,
                    notes=args.notes,
                )
                emit(asdict(resolution))
            elif args.command == "reevaluate":
                emit({"reevaluations": store.reevaluate_pending()})
            elif args.command == "report":
                emit(store.report())
        return 0
    except (ValueError, KeyError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
