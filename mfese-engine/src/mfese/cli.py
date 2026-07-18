from __future__ import annotations

import json
from pathlib import Path

import typer

from .engine import SynthesisEngine
from .schemas import SourceManifest, SourceSpec

app = typer.Typer(help="Multimodal Forensic Evidence Synthesis Engine")


@app.command()
def run(
    manifest: Path = typer.Argument(..., exists=True, readable=True),
    output_dir: Path = typer.Option(Path("mfese-output"), "--out"),
    allow_network_models: bool = typer.Option(False, "--allow-network-models"),
) -> None:
    spec = SourceManifest.from_path(manifest)
    engine = SynthesisEngine(allow_network_models=allow_network_models)
    report = engine.run(spec, output_dir=output_dir)
    typer.echo(json.dumps({
        "matter_id": report.matter_id,
        "sources_completed": len(report.source_analyses),
        "relations": len(report.pair_relations),
        "findings": len(report.candidate_findings),
        "errors": report.errors,
        "output_dir": str(output_dir),
    }, indent=2))


@app.command()
def scan(
    paths: list[Path] = typer.Argument(..., exists=True, readable=True),
    output_dir: Path = typer.Option(Path("mfese-output"), "--out"),
) -> None:
    manifest = SourceManifest(
        sources=[SourceSpec(source_id=f"source-{index+1}", path=str(path)) for index, path in enumerate(paths)]
    )
    report = SynthesisEngine().run(manifest, output_dir=output_dir)
    typer.echo(report.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
