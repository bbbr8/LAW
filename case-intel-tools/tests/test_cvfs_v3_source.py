import json
import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cvfs_v3_scanner_compiles(tmp_path):
    source = ROOT / "cvfs" / "cv_forensic_metadata_scanner.py"
    target = tmp_path / "cv_forensic_metadata_scanner.pyc"
    py_compile.compile(str(source), cfile=str(target), doraise=True)
    assert target.exists()


def test_cvfs_v3_schema_is_valid_json():
    schema = ROOT / "schemas" / "cvfs_metadata_record.schema.json"
    payload = json.loads(schema.read_text(encoding="utf-8"))
    assert payload["title"] == "CVFS Metadata Record"
    assert "record_type" in payload["properties"]


def test_cvfs_v3_model_router_preserves_private_boundary():
    router = (ROOT / "huggingface" / "CVFS_V3_MODEL_ROUTER.md").read_text(encoding="utf-8")
    assert "must not be uploaded to public Spaces" in router
    assert "cannot establish alteration" in router
