from pathlib import Path

import fitz

from mfese.engine import SynthesisEngine
from mfese.schemas import SourceManifest, SourceSpec


def _pdf(path: Path, title: str, metadata_title: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), title)
    doc.set_metadata({"title": metadata_title})
    doc.save(path)
    doc.close()


def test_same_visible_different_provenance(tmp_path):
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _pdf(a, "Proposal Total $100.00", "A")
    _pdf(b, "Proposal Total $100.00", "B")
    manifest = SourceManifest(sources=[
        SourceSpec(source_id="a", path=str(a), role_hint="proposal"),
        SourceSpec(source_id="b", path=str(b), role_hint="proposal"),
    ])
    report = SynthesisEngine().run(manifest)
    assert len(report.source_analyses) == 2
    assert any(relation.classification == "same_visible_document_different_provenance" for relation in report.pair_relations)
    assert report.graph["metrics"]["node_count"] > 0
