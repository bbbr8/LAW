from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelRoute:
    lane: str
    repo_id: str
    purpose: str
    executable: bool
    privacy: str = "local/private only"
    promotion_ceiling: str = "MODEL_CANDIDATE_PROMOTION_BLOCKED"


MODEL_ROUTES: dict[str, ModelRoute] = {
    "dinov2": ModelRoute("dinov2", "facebook/dinov2-base", "visual page/region family embeddings", True),
    "siglip2": ModelRoute("siglip2", "google/siglip2-base-patch16-224", "visual-semantic embeddings", True),
    "table_detection": ModelRoute("table_detection", "microsoft/table-transformer-detection", "table region candidates", True),
    "layoutlmv3": ModelRoute("layoutlmv3", "microsoft/layoutlmv3-base", "layout-aware token/box representations", False),
    "smoldocling": ModelRoute("smoldocling", "docling-project/SmolDocling-256M-preview", "document structure candidates", False),
    "bge_m3": ModelRoute("bge_m3", "BAAI/bge-m3", "text and metadata retrieval embeddings", False),
    "bge_reranker": ModelRoute("bge_reranker", "BAAI/bge-reranker-v2-m3", "candidate reranking", False),
}


def route_manifest() -> list[dict[str, Any]]:
    return [route.__dict__ for route in MODEL_ROUTES.values()]
