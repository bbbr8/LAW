from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .extract import classify_role, extract_items, extract_text, text_sha256
from .fusion import exact_sum_solver, fuse_pair, generate_pair_findings
from .graph import build_graph
from .hf_router import MODEL_ROUTES, route_manifest
from .schemas import CandidateFinding, SourceAnalysis, SourceManifest, SynthesisReport
from .skills import DEFAULT_SKILLS, ForensicWizard


ENGINE_VERSION = "0.1.0"
BOUNDARY = (
    "Models discover candidates. Deterministic extraction measures them. The evidence graph explains them. "
    "Native records prove or disprove them. Similarity, embeddings, arithmetic matches, graph proximity and "
    "review scores never independently prove authorship, intent, authorization, payment application, damages, fraud or liability."
)


class SynthesisEngine:
    def __init__(self, *, allow_network_models: bool = False, deterministic_skills: Sequence[str] | None = None) -> None:
        self.allow_network_models = allow_network_models
        self.deterministic_skills = tuple(deterministic_skills or DEFAULT_SKILLS)
        self.wizard = ForensicWizard(allow_network_models=allow_network_models)

    def analyze_source(self, source, *, render_dpi: int, enable_hf_lanes: Sequence[str]) -> SourceAnalysis:
        path = Path(source.path)
        if not path.exists():
            raise FileNotFoundError(path)
        executable = [lane for lane in enable_hf_lanes if MODEL_ROUTES.get(lane) and MODEL_ROUTES[lane].executable]
        deterministic = self.wizard.scan_file(
            path,
            skills=self.deterministic_skills,
            enable_models=executable if self.allow_network_models else (),
            render_dpi=render_dpi,
        ).model_dump()
        text, pages = extract_text(path)
        roles = classify_role(text, path.name, source.role_hint)
        selected_role = roles[0]["role"]
        items = extract_items(text, pages)
        hf_candidates = [skill for skill in deterministic.get("skills", []) if str(skill.get("skill_id", "")).startswith("hf_")]
        warnings = list(deterministic.get("errors", []))
        if enable_hf_lanes and not self.allow_network_models:
            warnings.append("HF lanes were requested but network model execution was disabled; routes are registered only.")
        return SourceAnalysis(
            source_id=source.source_id,
            path=str(path),
            native_locator=source.native_locator,
            source_sha256=deterministic["source"]["sha256"],
            size=deterministic["source"]["size"],
            mime_type=deterministic["source"]["mime_type"],
            role_candidates=roles,
            selected_role=selected_role,
            text_sha256=text_sha256(text),
            text_length=len(text),
            extracted_items=items,
            deterministic_report=deterministic,
            hf_candidates=hf_candidates,
            warnings=warnings,
        )

    def _lifecycle_coverage(self, manifest: SourceManifest, analyses: list[SourceAnalysis]) -> dict[str, Any]:
        ordered = [
            "proposal", "draw_request", "approval", "funding", "payment", "vendor_application",
            "delivery", "authorization", "owner_credit", "final_balance",
        ]
        events = [event.model_dump(mode="json") for event in manifest.known_events]
        present = {event["stage"] for event in events}
        role_stage_map = {
            "proposal": "proposal", "estimate": "proposal", "draw_request": "draw_request",
            "payment_instrument": "payment", "delivery_record": "delivery",
        }
        for analysis in analyses:
            if analysis.selected_role in role_stage_map:
                present.add(role_stage_map[analysis.selected_role])
        return {
            "ordered_stages": ordered,
            "present_stages": [stage for stage in ordered if stage in present],
            "missing_stages": [stage for stage in ordered if stage not in present],
            "events": events,
            "boundary": "A missing stage is a proof gap, not evidence that the event never occurred.",
        }

    def _exact_sum_results(self, manifest: SourceManifest, analyses: list[SourceAnalysis]) -> list[dict[str, Any]]:
        by_source = {analysis.source_id: analysis for analysis in analyses}
        output: list[dict[str, Any]] = []
        for task in manifest.exact_sum_tasks:
            values: list[tuple[str, float]] = []
            for source_id in task.source_ids:
                analysis = by_source.get(source_id)
                if not analysis:
                    continue
                for index, item in enumerate(analysis.extracted_items):
                    if item.kind == "amount" and isinstance(item.value, (int, float)):
                        values.append((f"{source_id}:p{item.page}:a{index}:{float(item.value):.2f}", float(item.value)))
            solutions = exact_sum_solver(
                values,
                task.target,
                tolerance=task.tolerance,
                max_items=task.max_items,
                max_solutions=task.max_solutions,
                min_value=task.min_value,
            )
            output.append({
                "task_id": task.task_id,
                "target": task.target,
                "source_ids": task.source_ids,
                "candidate_value_count": len(values),
                "solutions": solutions,
                "boundary": "Exact mathematical assembly does not establish role, project identity, payment, or intent.",
            })
        return output

    def run(self, manifest: SourceManifest, *, output_dir: str | Path | None = None) -> SynthesisReport:
        errors: list[str] = []
        analyses: list[SourceAnalysis] = []
        for source in manifest.sources:
            try:
                analyses.append(self.analyze_source(source, render_dpi=manifest.render_dpi, enable_hf_lanes=manifest.enable_hf_lanes))
            except Exception as exc:
                errors.append(f"{source.source_id}: {exc}")

        relations = []
        for index, left in enumerate(analyses):
            for right in analyses[index + 1:]:
                relations.append(fuse_pair(left, right))
        findings: list[CandidateFinding] = generate_pair_findings(relations)
        lifecycle = self._lifecycle_coverage(manifest, analyses)
        exact_sums = self._exact_sum_results(manifest, analyses)
        graph = build_graph(analyses, relations, [event.model_dump(mode="json") for event in manifest.known_events])

        receipt = {
            "engine_version": ENGINE_VERSION,
            "python": sys.version,
            "platform": platform.platform(),
            "privacy_mode": manifest.privacy_mode,
            "allow_network_models": self.allow_network_models,
            "registered_hf_routes": route_manifest(),
            "executed_hf_lanes": manifest.enable_hf_lanes if self.allow_network_models else [],
            "deterministic_skills": list(self.deterministic_skills),
            "source_count_requested": len(manifest.sources),
            "source_count_completed": len(analyses),
            "manifest_sha256": hashlib.sha256(manifest.model_dump_json().encode()).hexdigest(),
        }
        report = SynthesisReport(
            engine_version=ENGINE_VERSION,
            generated_utc=datetime.now(timezone.utc).isoformat(),
            matter_id=manifest.matter_id,
            privacy_mode=manifest.privacy_mode,
            boundary=BOUNDARY,
            source_analyses=analyses,
            pair_relations=relations,
            candidate_findings=findings,
            lifecycle_coverage=lifecycle,
            exact_sum_results=exact_sums,
            graph=graph,
            run_receipt=receipt,
            errors=errors,
        )
        if output_dir:
            self.save(report, output_dir)
        return report

    @staticmethod
    def save(report: SynthesisReport, output_dir: str | Path) -> dict[str, str]:
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        report_path = directory / "mfese_report.json"
        graph_path = directory / "mfese_graph.json"
        receipt_path = directory / "mfese_run_receipt.json"
        report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        graph_path.write_text(json.dumps(report.graph, indent=2), encoding="utf-8")
        receipt_path.write_text(json.dumps(report.run_receipt, indent=2), encoding="utf-8")
        manifest = {}
        for path in [report_path, graph_path, receipt_path]:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest[path.name] = {"sha256": digest, "size": path.stat().st_size}
        manifest_path = directory / "mfese_output_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {name: str(directory / name) for name in manifest} | {"manifest": str(manifest_path)}
