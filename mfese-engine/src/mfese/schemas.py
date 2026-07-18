from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class DocumentRole(str, Enum):
    PROPOSAL = "proposal"
    ESTIMATE = "estimate"
    INVOICE = "invoice"
    DRAW_REQUEST = "draw_request"
    BUDGET = "budget"
    LINE_ITEM_TRANSFER = "line_item_transfer"
    PAYMENT_INSTRUMENT = "payment_instrument"
    BANK_STATEMENT = "bank_statement"
    LIEN_WAIVER = "lien_waiver"
    DELIVERY_RECORD = "delivery_record"
    EMAIL = "email"
    CONTRACT = "contract"
    OTHER = "other"
    UNKNOWN = "unknown"


class PromotionState(str, Enum):
    NATIVE_MEASUREMENT = "native_measurement"
    REPRODUCIBLE_CALCULATION = "reproducible_calculation"
    SOURCE_SUPPORTED_REVIEW = "source_supported_review_candidate"
    MODEL_CANDIDATE = "model_candidate_promotion_blocked"
    OPEN = "open"
    SUPERSEDED = "superseded"


class SourceSpec(BaseModel):
    source_id: str
    path: str
    role_hint: DocumentRole | None = None
    project_id: str | None = None
    native_locator: str | None = None
    actor: str | None = None
    vendor: str | None = None
    account: str | None = None
    event_date: str | None = None
    notes: str | None = None

    @field_validator("event_date", mode="before")
    @classmethod
    def normalize_event_date(cls, value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @field_validator("path")
    @classmethod
    def nonempty_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("path cannot be empty")
        return value


class KnownEvent(BaseModel):
    event_id: str
    stage: Literal[
        "proposal", "draw_request", "approval", "funding", "payment", "vendor_application",
        "delivery", "authorization", "owner_credit", "final_balance", "other",
    ]
    date: str | None = None
    amount: float | None = None
    source_id: str | None = None
    actor: str | None = None
    object: str | None = None
    proof_state: PromotionState = PromotionState.OPEN
    notes: str | None = None

    @field_validator("date", mode="before")
    @classmethod
    def normalize_date(cls, value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value


class ExactSumTask(BaseModel):
    task_id: str
    target: float
    source_ids: list[str] = Field(default_factory=list)
    tolerance: float = 0.01
    max_items: int = 24
    max_solutions: int = 25
    min_value: float = 1.0


class SourceManifest(BaseModel):
    matter_id: str = "local-private-matter"
    privacy_mode: Literal["local_private", "private_approved_network", "synthetic_public"] = "local_private"
    sources: list[SourceSpec]
    known_events: list[KnownEvent] = Field(default_factory=list)
    exact_sum_tasks: list[ExactSumTask] = Field(default_factory=list)
    enable_hf_lanes: list[str] = Field(default_factory=list)
    render_dpi: int = 150
    notes: str | None = None

    @classmethod
    def from_path(cls, path: str | Path) -> "SourceManifest":
        import json
        import yaml

        source = Path(path)
        raw = source.read_text(encoding="utf-8")
        if source.suffix.lower() in {".yaml", ".yml"}:
            return cls.model_validate(yaml.safe_load(raw))
        return cls.model_validate(json.loads(raw))


class ExtractedItem(BaseModel):
    kind: str
    value: Any
    normalized: str | None = None
    page: int | None = None
    bbox: list[float] | None = None
    source_method: str


class SourceAnalysis(BaseModel):
    source_id: str
    path: str
    native_locator: str | None = None
    source_sha256: str
    size: int
    mime_type: str
    role_candidates: list[dict[str, Any]]
    selected_role: str
    text_sha256: str
    text_length: int
    extracted_items: list[ExtractedItem]
    deterministic_report: dict[str, Any]
    hf_candidates: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PairRelation(BaseModel):
    relation_id: str
    left_source_id: str
    right_source_id: str
    classification: str
    promotion_state: PromotionState
    score: float
    signals: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    required_bridge: list[str] = Field(default_factory=list)


class CandidateFinding(BaseModel):
    finding_id: str
    title: str
    statement: str
    promotion_state: PromotionState
    supporting_source_ids: list[str]
    support: list[dict[str, Any]]
    competing_explanations: list[str] = Field(default_factory=list)
    missing_bridges: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    node_id: str
    node_type: str
    label: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    edge_id: str
    source: str
    target: str
    edge_type: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class SynthesisReport(BaseModel):
    schema_version: str = "mfese-synthesis-report/v1"
    engine_version: str
    generated_utc: str
    matter_id: str
    privacy_mode: str
    boundary: str
    source_analyses: list[SourceAnalysis]
    pair_relations: list[PairRelation]
    candidate_findings: list[CandidateFinding]
    lifecycle_coverage: dict[str, Any]
    exact_sum_results: list[dict[str, Any]]
    graph: dict[str, Any]
    run_receipt: dict[str, Any]
    errors: list[str] = Field(default_factory=list)
