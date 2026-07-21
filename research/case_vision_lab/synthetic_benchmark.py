#!/usr/bin/env python3
"""Run a reproducible, synthetic-only benchmark of the case vision lab.

This control benchmark verifies fixture generation, hash integrity, privacy
labels, immutable adapter pins, deterministic image output, and the
retroactive routing outcomes. It intentionally does not download or execute
third-party model weights; per-model inference remains a separate gated step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from PIL import __version__ as pillow_version

from research.case_vision_lab.model_adapters import load_model_adapters
from research.case_vision_lab.retroactive_cv_router import VisionEvalStore
from research.case_vision_lab.synthetic_doc_lab import generate_dataset, parse_transforms

BENCHMARK_REVISION = "0" * 40
TRANSFORMS = parse_transforms("clean,rotate,blur,low_contrast,jpeg,occlusion,shear")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def verify_fixtures(output: Path, count: int, seed: int) -> dict[str, Any]:
    first_dir = output / "dataset_a"
    second_dir = output / "dataset_b"
    started = time.perf_counter()
    first = generate_dataset(first_dir, count, seed, TRANSFORMS)
    elapsed = time.perf_counter() - started
    # A single repeated document is sufficient to prove seeded image
    # determinism without doubling the full benchmark's runtime and disk use.
    second = generate_dataset(second_dir, 1, seed, TRANSFORMS)

    first_hashes = [fixture.image_sha256 for fixture in first]
    second_hashes = [fixture.image_sha256 for fixture in second]
    records = load_jsonl(first_dir / "manifest.jsonl")
    integrity_failures = sum(
        sha256_file(Path(fixture.image_path)) != fixture.image_sha256 for fixture in first
    )
    privacy_failures = sum(
        record.get("privacy")
        != {
            "contains_native_case_data": False,
            "contains_real_signature": False,
            "synthetic_only": True,
        }
        for record in records
    )

    expected = count * len(TRANSFORMS)
    if len(first) != expected or len(records) != expected:
        raise RuntimeError(f"expected {expected} fixtures and manifest rows")
    if first_hashes[: len(TRANSFORMS)] != second_hashes:
        raise RuntimeError("same-seed image hashes were not deterministic")
    if integrity_failures or privacy_failures:
        raise RuntimeError("fixture integrity or privacy validation failed")

    return {
        "documents": count,
        "fixture_count": len(first),
        "transform_counts": dict(sorted(Counter(f.transform["name"] for f in first).items())),
        "unique_image_hashes": len(set(first_hashes)),
        "integrity_failures": integrity_failures,
        "privacy_failures": privacy_failures,
        "same_seed_hashes_deterministic": True,
        "generation_seconds": round(elapsed, 6),
        "fixtures_per_second": round(len(first) / elapsed, 3),
    }


def verify_router(output: Path) -> dict[str, Any]:
    scenarios = [
        ("line_item_table", 0.92, "line_item_table"),
        ("borrower_signature", 0.97, "decorative_mark"),
        ("abstain", 0.10, "construction_invoice"),
        ("needs_review", 0.50, "unresolved"),
    ]
    db_path = output / "router.sqlite3"
    with VisionEvalStore(db_path) as store:
        store.init()
        for index, (predicted, confidence, resolved) in enumerate(scenarios, start=1):
            observation = store.record_observation(
                source_hash=hashlib.sha256(f"synthetic-source-{index}".encode()).hexdigest(),
                model_name="case-vision-synthetic-control",
                model_revision=BENCHMARK_REVISION,
                task="control_route",
                document_type="synthetic_construction_invoice",
                predicted_label=predicted,
                confidence=confidence,
                features={"synthetic": True, "contains_native_case_data": False},
            )
            store.add_resolution(
                observation_id=observation.observation_id,
                resolved_label=resolved,
                relation="synthetic_expected_resolution",
                anchor_hash=hashlib.sha256(f"synthetic-anchor-{index}".encode()).hexdigest(),
                reviewer="synthetic-control",
            )
        results = store.reevaluate_pending()
        report = store.report()

    outcomes = Counter(result["outcome"] for result in results)
    routes = Counter(result["route"] for result in results)
    expected_outcomes = {
        "false_negative": 1,
        "false_positive": 1,
        "still_unresolved": 1,
        "true_positive": 1,
    }
    if dict(sorted(outcomes.items())) != expected_outcomes:
        raise RuntimeError("retroactive router did not produce the expected control outcomes")
    return {
        "observations": report["counts"]["observations"],
        "resolutions": report["counts"]["resolutions"],
        "reevaluations": report["counts"]["reevaluations"],
        "outcomes": dict(sorted(outcomes.items())),
        "routes": dict(sorted(routes.items())),
        "policy": report["policy"],
    }


def run(output: Path, count: int, seed: int) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"benchmark output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    adapters = load_model_adapters()
    result = {
        "benchmark": "case-vision-synthetic-control-v1",
        "scope": "synthetic fixtures and evaluation pipeline; third-party weights not executed",
        "seed": seed,
        "environment": {
            "python": platform.python_version(),
            "pillow": pillow_version,
            "platform": platform.platform(),
        },
        "adapter_pins": [
            {"model_id": item["model_id"], "revision": item["revision"]}
            for item in adapters["adapters"]
        ],
        "fixtures": verify_fixtures(output, count, seed),
        "router": verify_router(output),
        "privacy_and_promotion_safeguards_passed": True,
    }
    (output / "benchmark_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/case_vision_benchmark"))
    parser.add_argument("--count", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20260718)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.count < 1 or args.count > 10_000:
        print("error: --count must be between 1 and 10000", file=sys.stderr)
        return 2
    try:
        print(json.dumps(run(args.output, args.count, args.seed), indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
