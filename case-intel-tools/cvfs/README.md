# CVFS v3 Metadata Scanner

Status: generic code-only scanner. Do not commit native case evidence or scan outputs to GitHub.

## Purpose

CVFS v3 creates deterministic document, page, embedded-image, and font metadata records before expensive anomaly review or private model inference.

It adds these metadata families:

- ZIP entry path, CRC, compression, size, and timestamp.
- PDF version, object count, encryption, permissions, repair status, standard metadata, and XMP hash.
- Incremental-save, signature, form, action, attachment, optional-content, compression, soft-mask, and ICC token counts.
- Page boxes, rotation, page mode, text-layer metrics, widgets, annotations, visual hashes, entropy, edge density, and sharpness.
- Embedded-image hashes, dimensions, colorspace, filter, soft-mask relationship, and cross-file reuse.
- Font resource, base-font, encoding, type, and cross-document font-family evidence.
- Exact duplicate pages, near-duplicate visual pages, and cross-file embedded-image reuse groups.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r case-intel-tools/cvfs/requirements.txt
```

## Run

```bash
python case-intel-tools/cvfs/cv_forensic_metadata_scanner.py evidence.zip --out private-output
```

The input may be a PDF, a directory, or a ZIP containing PDFs.

## Outputs

```text
documents.jsonl
pages.jsonl
embedded_images.jsonl
fonts.jsonl
errors.jsonl
summary.json
```

Keep outputs in the private source-control lane. Only redacted aggregate rows or synthetic test records belong in GitHub.

## Two-stage execution

1. Run this fast corpus baseline.
2. Route selected pages to heavier CVFS methods such as copy-move, signature-crop comparison, noise residuals, blur maps, resampling analysis, JPEG quantization analysis, and model-based layout/visual embeddings.

This prevents one pathological page from blocking the entire corpus and creates a reproducible reason for every heavy scan.

## Hugging Face

See `../huggingface/CVFS_V3_MODEL_ROUTER.md`. Models are optional and are not executed by the baseline scanner. Private evidence stays local unless a separately approved private-compute workflow exists.

## Proof boundary

A fingerprint or model similarity score can identify a review candidate. It cannot independently prove alteration, identity, intent, authorization, payment application, damages, or liability.
