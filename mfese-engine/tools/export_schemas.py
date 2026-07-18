from __future__ import annotations

import json
from pathlib import Path

from mfese.schemas import SourceManifest, SynthesisReport


root = Path(__file__).resolve().parents[1] / "schemas"
root.mkdir(parents=True, exist_ok=True)
(root / "source_manifest.schema.json").write_text(
    json.dumps(SourceManifest.model_json_schema(), indent=2), encoding="utf-8"
)
(root / "mfese_report.schema.json").write_text(
    json.dumps(SynthesisReport.model_json_schema(), indent=2), encoding="utf-8"
)
print(root)
