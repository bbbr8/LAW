from __future__ import annotations

import json
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import gradio as gr

from mfese.engine import SynthesisEngine
from mfese.hf_router import MODEL_ROUTES
from mfese.schemas import SourceManifest, SourceSpec


def run_engine(files, role_hints, hf_lanes, enable_network, dpi):
    if not files:
        raise gr.Error("Upload at least one PDF or image.")
    roles = [value.strip() for value in (role_hints or "").split(",")]
    sources = []
    for index, file_path in enumerate(files):
        role = roles[index] if index < len(roles) and roles[index] else None
        source = {"source_id": f"source-{index+1}", "path": str(file_path)}
        if role:
            source["role_hint"] = role
        sources.append(SourceSpec.model_validate(source))
    manifest = SourceManifest(
        privacy_mode="private_approved_network" if enable_network else "local_private",
        sources=sources,
        enable_hf_lanes=list(hf_lanes or []),
        render_dpi=int(dpi),
    )
    temp_dir = Path(tempfile.mkdtemp(prefix="mfese-"))
    report = SynthesisEngine(allow_network_models=bool(enable_network)).run(manifest, output_dir=temp_dir)
    summary = {
        "sources": len(report.source_analyses),
        "pair_relations": len(report.pair_relations),
        "candidate_findings": len(report.candidate_findings),
        "missing_lifecycle_stages": report.lifecycle_coverage.get("missing_stages"),
        "errors": report.errors,
    }
    return json.dumps(summary, indent=2), str(temp_dir / "mfese_report.json"), str(temp_dir / "mfese_graph.json")


with gr.Blocks(title="Multimodal Forensic Evidence Synthesis Engine") as demo:
    gr.Markdown("""
# Multimodal Forensic Evidence Synthesis Engine

**Models discover candidates. Deterministic extraction measures them. The evidence graph explains them. Native records prove or disprove them.**

Network model execution is off by default. Raw uploads are not committed to the repository.
""")
    files = gr.File(file_count="multiple", type="filepath", label="PDFs or images")
    role_hints = gr.Textbox(label="Optional comma-separated role hints", placeholder="proposal,draw_request,invoice")
    hf_lanes = gr.CheckboxGroup(choices=list(MODEL_ROUTES), value=[], label="Optional Hugging Face lanes")
    enable_network = gr.Checkbox(value=False, label="Explicitly allow private/approved model downloads")
    dpi = gr.Slider(100, 250, 150, step=25, label="Render DPI")
    button = gr.Button("Run synthesis", variant="primary")
    summary = gr.Code(language="json", label="Summary")
    report_file = gr.File(label="Report JSON")
    graph_file = gr.File(label="Evidence graph JSON")
    button.click(run_engine, [files, role_hints, hf_lanes, enable_network, dpi], [summary, report_file, graph_file])

if __name__ == "__main__":
    demo.launch()
