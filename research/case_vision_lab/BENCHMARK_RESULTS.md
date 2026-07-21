# Case Vision Synthetic Control Benchmark

## Executed run

- Date: 2026-07-21
- Branch input SHA: `37094e48dddd9c5313a877da1d258d58e4954d08`
- Benchmark: `case-vision-synthetic-control-v1`
- Seed: `20260718`
- Environment: Python 3.12.13, Pillow 12.3.0, Linux x86_64
- Command:

```bash
python -m research.case_vision_lab.synthetic_benchmark \
  --output /tmp/law-case-vision-benchmark \
  --count 25 \
  --seed 20260718
```

## Results

| Control | Result |
| --- | ---: |
| Fictional base documents | 25 |
| Degraded fixtures | 175 |
| Fixtures per transform | 25 |
| Unique image SHA-256 hashes | 175 |
| Hash-integrity failures | 0 |
| Privacy-label failures | 0 |
| Same-seed image hashes deterministic | Yes |
| Generation time | 29.752348 seconds |
| Throughput | 5.882 fixtures/second |

The seven transformations were clean, rotate, blur, low contrast, JPEG
compression, occlusion, and shear.

The retroactive router control created four synthetic observations and four
source-hash-bound resolutions. It produced exactly one true positive, one false
positive, one false negative, and one still-unresolved result. The corresponding
routes were retain with monitoring, disable or retrain, inspect recall gap, and
hold. Raw case bytes remained disabled, automatic fact promotion remained
disabled, and human review remained required.

## Adapter-pin validation

The run loaded all three declared adapter records and validated each full
40-character commit SHA. The Oblix model card does not declare a license, so the
manifest blocks it behind explicit license review rather than inferring a
license.

## Limitation and decision

This run validates the synthetic generator and evaluation controls, not model
accuracy. It downloaded no third-party weights and executed no model inference.
The adapters remain candidates only. Decision: retain the lab controls; require
a separately reviewed, source-authorized inference run before approving any
adapter or changing a case conclusion.
