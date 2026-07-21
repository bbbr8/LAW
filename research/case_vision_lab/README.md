# Case Vision Lab

Privacy-safe computer-vision research for the Case Profile and Evidence-Control App.

This lab is deliberately separated from native case evidence. It creates synthetic fixtures, records bounded model observations, and measures what later review shows worked or failed. A model score is never promoted directly into a case fact.

## Included scripts

### `synthetic_doc_lab.py`

Creates fictional construction invoices and controlled image degradations:

- clean source page;
- small rotation;
- Gaussian blur;
- low contrast;
- JPEG compression;
- partial occlusion;
- affine shear.

Each page receives a SHA-256 hash, expected field values, clean-page region annotations, transformation metadata, and explicit privacy flags. The generated signature and stamp are abstract test marks, not copied or modeled from any person.

```bash
python -m pip install pillow
python research/case_vision_lab/synthetic_doc_lab.py \
  --output .artifacts/case_vision_synthetic \
  --count 25 \
  --seed 20260718
```

### `retroactive_cv_router.py`

Stores source hashes, model/revision identifiers, bounded features, predictions, confidence, later resolutions, and reevaluation outcomes in SQLite. It stores no native image bytes or case text.

```bash
python research/case_vision_lab/retroactive_cv_router.py \
  --db .artifacts/case_vision_eval.sqlite3 init

python research/case_vision_lab/retroactive_cv_router.py \
  --db .artifacts/case_vision_eval.sqlite3 observe \
  --source-hash SHA256_OF_LOCAL_PAGE \
  --model HURIDOCS/pdf-document-layout-analysis \
  --revision IMMUTABLE_40_CHARACTER_COMMIT_SHA \
  --task layout_region \
  --document-type construction_invoice \
  --label line_item_table \
  --confidence 0.91 \
  --region-json '{"x":110,"y":620,"width":1480,"height":602}' \
  --features-json '{"degradation":"jpeg","synthetic":true}'

python research/case_vision_lab/retroactive_cv_router.py \
  --db .artifacts/case_vision_eval.sqlite3 resolve \
  --observation-id OBSERVATION_ID \
  --label line_item_table \
  --relation later_human_review \
  --anchor-hash HASH_OF_REVIEW_RECORD \
  --reviewer HUMAN_REVIEWER_ID

python research/case_vision_lab/retroactive_cv_router.py \
  --db .artifacts/case_vision_eval.sqlite3 reevaluate

python research/case_vision_lab/retroactive_cv_router.py \
  --db .artifacts/case_vision_eval.sqlite3 report
```

The CLI rejects mutable tags, branch names, missing revisions, and malformed
source or anchor hashes. Revisions must be full 40-character commit SHAs and
source anchors must be SHA-256 hex digests, canonicalized to lowercase.

## Candidate model adapters

The lab does not bundle model weights. Every declared adapter is recorded in
`model_adapters.json`, and `model_adapters.py` rejects missing or mutable
revisions and incomplete privacy or promotion policy. Revisions were resolved
from the model repositories on 2026-07-21.

| Candidate | Immutable revision | License posture | Threshold |
| --- | --- | --- | ---: |
| [HURIDOCS/pdf-document-layout-analysis](https://huggingface.co/HURIDOCS/pdf-document-layout-analysis) | `d67bff2431df3584a114ac9e82d5c77ced364c4f` | Apache-2.0 | 0.85 |
| [Oblix/yolov10m-doclaynet_ONNX_document-layout-analysis](https://huggingface.co/Oblix/yolov10m-doclaynet_ONNX_document-layout-analysis) | `ded498025f9b377ebb079bb6984c46967ada1505` | Not declared; license review required | 0.35 |
| [pascalrai/Deformable-DETR-Document-Layout-Analysis](https://huggingface.co/pascalrai/Deformable-DETR-Document-Layout-Analysis) | `7e0570a0d7b072bf7c6ecb6ce5da59284d9952e5` | Apache-2.0 | 0.50 |

A candidate is not approved merely because it has a high public benchmark score. It must be tested against the synthetic degradation matrix and then validated locally on source-authorized derivatives under the existing evidence controls.

## Synthetic control benchmark

The reproducible control benchmark generates only fictional pages. It checks
all image hashes, manifest privacy labels, same-seed image determinism, adapter
revision pins, and the true-positive, false-positive, false-negative, and
unresolved retroactive routes.

```bash
python -m pip install pillow
python -m research.case_vision_lab.synthetic_benchmark \
  --output .artifacts/case_vision_benchmark \
  --count 25 \
  --seed 20260718
```

This is an evaluation-pipeline control benchmark. It does not download or
execute third-party model weights and must not be represented as model-quality
evidence. See `BENCHMARK_RESULTS.md` for the executed run and its limitations.

## Retroactive learning loop

1. Generate synthetic pages with known labels.
2. Run one or more pinned model revisions locally.
3. Record every observation, including abstentions and low-confidence outputs.
4. Add later human resolutions or source-bound cross-reference outcomes.
5. Reevaluate all pending observations.
6. Compare accuracy, confidence error, false positives, false negatives, and critical routes by model, revision, task, and document type.
7. Disable, retrain, or tighten thresholds when high-confidence predictions conflict with later resolutions.
8. Preserve the original prediction and the later correction; never rewrite history.

## Promotion and privacy rules

- No native evidence bytes in GitHub or Hugging Face.
- No privileged text, credentials, real signatures, or personally identifying case content in fixtures or logs.
- Hashes and source locators remain the bridge back to authorized local/Drive records.
- Similarity, OCR output, object detections, and model confidence are investigative candidates only.
- Human review and exact source anchors are required before any case conclusion changes.
- Failed or exculpatory results remain in the evaluation record.
- Changes stay on a research branch until tests and review pass.

## Recommended recurring output

Each research cycle should produce one small, reviewable change rather than a pile of untested scripts:

- one hypothesis;
- one synthetic test matrix;
- one code or configuration change;
- one reproducible command;
- one result summary;
- one list of failures and limitations;
- one explicit decision: retain, adjust, disable, or investigate.
