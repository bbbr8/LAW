from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .schemas import CandidateFinding, PairRelation, PromotionState, SourceAnalysis


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(raw).hexdigest()[:16]}"


def skill_measurements(analysis: SourceAnalysis, skill_id: str) -> dict[str, Any]:
    for skill in analysis.deterministic_report.get("skills", []):
        if skill.get("skill_id") == skill_id and skill.get("status") == "ok":
            return skill.get("measurements", {})
    return {}


def values_of_kind(analysis: SourceAnalysis, kind: str) -> list[Any]:
    return [item.value for item in analysis.extracted_items if item.kind == kind]


def _page_rows(analysis: SourceAnalysis) -> list[dict[str, Any]]:
    return skill_measurements(analysis, "page_fingerprints").get("pages", [])


def _embedded_hashes(analysis: SourceAnalysis) -> set[str]:
    objects = skill_measurements(analysis, "embedded_objects").get("objects", [])
    return {str(row.get("embedded_sha256")) for row in objects if row.get("embedded_sha256")}


def _hog_similarity(left: SourceAnalysis, right: SourceAnalysis) -> dict[str, Any]:
    left_pages, right_pages = _page_rows(left), _page_rows(right)
    pairs: list[float] = []
    for lp in left_pages:
        lv = np.asarray(lp.get("hog_embedding", []), dtype=np.float32)
        if lv.size == 0:
            continue
        for rp in right_pages:
            rv = np.asarray(rp.get("hog_embedding", []), dtype=np.float32)
            if rv.size != lv.size or rv.size == 0:
                continue
            pairs.append(float(cosine_similarity(lv.reshape(1, -1), rv.reshape(1, -1))[0, 0]))
    return {
        "max": round(max(pairs), 7) if pairs else None,
        "mean": round(float(np.mean(pairs)), 7) if pairs else None,
        "pair_count": len(pairs),
    }


def amount_relations(left: SourceAnalysis, right: SourceAnalysis) -> list[dict[str, Any]]:
    lvals = sorted(set(round(float(v), 2) for v in values_of_kind(left, "amount") if isinstance(v, (int, float))))
    rvals = sorted(set(round(float(v), 2) for v in values_of_kind(right, "amount") if isinstance(v, (int, float))))
    relations: list[dict[str, Any]] = []
    for lv in lvals:
        for rv in rvals:
            if abs(lv - rv) <= 0.01:
                relations.append({"type": "exact_match", "left": lv, "right": rv, "difference": round(lv-rv, 2)})
            if rv and abs(lv / rv - 0.5) <= 0.0001:
                relations.append({"type": "left_is_half", "left": lv, "right": rv, "ratio": round(lv/rv, 8)})
            if lv and abs(rv / lv - 0.5) <= 0.0001:
                relations.append({"type": "right_is_half", "left": lv, "right": rv, "ratio": round(rv/lv, 8)})
    return relations[:250]


def fuse_pair(left: SourceAnalysis, right: SourceAnalysis) -> PairRelation:
    left_pages, right_pages = _page_rows(left), _page_rows(right)
    left_rasters = [row.get("raster_sha256") for row in left_pages]
    right_rasters = [row.get("raster_sha256") for row in right_pages]
    same_page_count = len(left_rasters) == len(right_rasters) and len(left_rasters) > 0
    same_visible_render = same_page_count and left_rasters == right_rasters
    same_binary = left.source_sha256 == right.source_sha256
    text_identical = left.text_sha256 == right.text_sha256 and left.text_length > 0
    shared_objects = sorted(_embedded_hashes(left) & _embedded_hashes(right))
    hog = _hog_similarity(left, right)
    amounts = amount_relations(left, right)
    roles = {left.selected_role, right.selected_role}

    lifecycle_pairs = {
        frozenset({"proposal", "invoice"}),
        frozenset({"proposal", "draw_request"}),
        frozenset({"invoice", "draw_request"}),
        frozenset({"payment_instrument", "invoice"}),
        frozenset({"budget", "draw_request"}),
        frozenset({"line_item_transfer", "draw_request"}),
    }
    role_lifecycle = frozenset(roles) in lifecycle_pairs

    score_components = {
        "same_binary": 1.0 if same_binary else 0.0,
        "same_visible_render": 0.95 if same_visible_render else 0.0,
        "text_identical": 0.75 if text_identical else 0.0,
        "shared_object_signal": min(0.8, len(shared_objects) * 0.08),
        "visual_similarity": max(0.0, (hog.get("max") or 0.0) - 0.65),
        "amount_relation": 0.4 if amounts else 0.0,
        "role_lifecycle": 0.25 if role_lifecycle else 0.0,
    }
    score = min(1.0, sum(score_components.values()) / 2.0)
    warnings: list[str] = []
    bridges: list[str] = []

    if same_binary:
        classification = "same_binary_object"
        state = PromotionState.NATIVE_MEASUREMENT
    elif same_visible_render:
        classification = "same_visible_document_different_provenance"
        state = PromotionState.REPRODUCIBLE_CALCULATION
        warnings.append("Identical render does not merge custody or file provenance.")
        bridges.append("native custody/version history")
    elif role_lifecycle and amounts:
        classification = "document_lifecycle_amount_relation"
        state = PromotionState.SOURCE_SUPPORTED_REVIEW
        warnings.append("A proposal, invoice, draw request, and payment are different transaction roles.")
        bridges.extend(["funding record", "vendor cash application", "owner credit/final accounting"])
    elif (hog.get("max") or 0) >= 0.94:
        classification = "visual_family_candidate"
        state = PromotionState.SOURCE_SUPPORTED_REVIEW
        warnings.append("Visual similarity is not transaction identity.")
        bridges.append("native object/text/transaction comparison")
    elif amounts:
        classification = "amount_relation_only"
        state = PromotionState.OPEN
        warnings.append("Amount coincidence cannot establish purpose or application.")
        bridges.append("role, date, project, account and payment bridge")
    else:
        classification = "no_material_pair_relation"
        state = PromotionState.OPEN

    return PairRelation(
        relation_id=stable_id("REL", left.source_id, right.source_id, classification),
        left_source_id=left.source_id,
        right_source_id=right.source_id,
        classification=classification,
        promotion_state=state,
        score=round(score, 6),
        signals={
            "same_binary": same_binary,
            "same_visible_render": same_visible_render,
            "text_identical": text_identical,
            "shared_embedded_object_count": len(shared_objects),
            "shared_embedded_object_hashes": shared_objects[:100],
            "hog_similarity": hog,
            "amount_relations": amounts,
            "roles": sorted(roles),
            "score_components": score_components,
        },
        warnings=warnings,
        required_bridge=sorted(set(bridges)),
    )


def generate_pair_findings(relations: list[PairRelation]) -> list[CandidateFinding]:
    findings: list[CandidateFinding] = []
    for relation in relations:
        if relation.classification == "same_visible_document_different_provenance":
            findings.append(CandidateFinding(
                finding_id=stable_id("FND", relation.relation_id),
                title="Same visible document, different provenance",
                statement=(
                    f"{relation.left_source_id} and {relation.right_source_id} render identically while their "
                    "binary source identities differ. They must remain separate custody/version objects."
                ),
                promotion_state=PromotionState.REPRODUCIBLE_CALCULATION,
                supporting_source_ids=[relation.left_source_id, relation.right_source_id],
                support=[relation.model_dump()],
                competing_explanations=["normal re-export", "production wrapper", "file renaming or repackaging"],
                missing_bridges=relation.required_bridge,
            ))
        if relation.classification == "document_lifecycle_amount_relation":
            findings.append(CandidateFinding(
                finding_id=stable_id("FND", relation.relation_id),
                title="Document lifecycle amount relation",
                statement=(
                    f"{relation.left_source_id} and {relation.right_source_id} share one or more exact/ratio amount "
                    "relationships while occupying different document roles. The relationship is useful for routing "
                    "but does not convert one role into another."
                ),
                promotion_state=PromotionState.SOURCE_SUPPORTED_REVIEW,
                supporting_source_ids=[relation.left_source_id, relation.right_source_id],
                support=[relation.model_dump()],
                competing_explanations=["ordinary staged billing", "allowance accounting", "partial payment schedule"],
                missing_bridges=relation.required_bridge,
            ))
    return findings


def exact_sum_solver(values: list[tuple[str, float]], target: float, *, tolerance: float = 0.01, max_items: int = 24, max_solutions: int = 25, min_value: float = 1.0) -> list[dict[str, Any]]:
    filtered = [(key, round(float(value), 2)) for key, value in values if value >= min_value][:max_items]
    if not filtered:
        return []
    half = len(filtered) // 2
    left, right = filtered[:half], filtered[half:]

    def subsets(rows: list[tuple[str, float]]) -> list[tuple[float, tuple[str, ...]]]:
        result: list[tuple[float, tuple[str, ...]]] = []
        for mask in range(1 << len(rows)):
            total = 0.0
            keys: list[str] = []
            for idx, (key, value) in enumerate(rows):
                if mask & (1 << idx):
                    total += value
                    keys.append(key)
            result.append((round(total, 2), tuple(keys)))
        return result

    left_subsets = subsets(left)
    right_subsets = sorted(subsets(right), key=lambda row: row[0])
    right_totals = np.asarray([row[0] for row in right_subsets], dtype=float)
    solutions: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for left_total, left_keys in left_subsets:
        need = target - left_total
        pos = int(np.searchsorted(right_totals, need))
        for candidate_pos in range(max(0, pos - 2), min(len(right_subsets), pos + 3)):
            right_total, right_keys = right_subsets[candidate_pos]
            total = round(left_total + right_total, 2)
            if abs(total - target) <= tolerance:
                keys = tuple(sorted(left_keys + right_keys))
                if not keys or keys in seen:
                    continue
                seen.add(keys)
                solutions.append({"keys": list(keys), "sum": total, "difference": round(total-target, 2), "cardinality": len(keys)})
                if len(solutions) >= max(max_solutions * 10, 100):
                    break
        if len(solutions) >= max(max_solutions * 10, 100):
            break
    solutions.sort(key=lambda row: (row["cardinality"], abs(row["difference"]), row["keys"]))
    return solutions[:max_solutions]
