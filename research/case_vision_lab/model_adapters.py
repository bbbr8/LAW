"""Load and validate privacy-gated model adapter metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DEFAULT_MANIFEST = Path(__file__).with_name("model_adapters.json")


def load_model_adapters(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    policy = manifest.get("promotion_policy", {})
    required_policy = {
        "automatic_fact_promotion": False,
        "human_review_required": True,
        "exact_source_anchor_required": True,
        "native_case_data_allowed_in_repository": False,
    }
    if policy != required_policy:
        raise ValueError("model adapter manifest must preserve the complete promotion and privacy policy")

    adapters = manifest.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        raise ValueError("model adapter manifest must contain at least one adapter")

    seen: set[str] = set()
    required = {
        "model_id",
        "revision",
        "task",
        "runtime",
        "license",
        "input_normalization",
        "confidence_threshold",
        "license_review_required",
        "promotion_rule",
    }
    for index, adapter in enumerate(adapters):
        if not isinstance(adapter, dict) or set(adapter) != required:
            raise ValueError(f"adapter {index} must contain exactly {sorted(required)}")
        model_id = adapter["model_id"]
        if not isinstance(model_id, str) or not model_id.strip() or model_id in seen:
            raise ValueError(f"adapter {index} has a missing or duplicate model_id")
        seen.add(model_id)
        if not COMMIT_SHA_RE.fullmatch(str(adapter["revision"])):
            raise ValueError(f"adapter {model_id} revision must be an immutable 40-character commit SHA")
        threshold = adapter["confidence_threshold"]
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            raise ValueError(f"adapter {model_id} confidence_threshold must be in [0, 1]")
        if adapter["license"] == "not-declared-in-model-card" and not adapter["license_review_required"]:
            raise ValueError(f"adapter {model_id} must require license review")
    return manifest
