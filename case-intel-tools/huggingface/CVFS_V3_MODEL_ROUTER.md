# CVFS v3 Hugging Face Model Router

Status: private/local derivative-routing configuration. Native evidence must not be uploaded to public Spaces, public datasets, or public model endpoints.

## Prime boundary

Hugging Face models may generate embeddings, candidate regions, layout labels, or review queues. They cannot establish alteration, authorship, forgery, intent, authorization, payment application, damages, or legal liability.

## Approved local/private lanes

| Lane | Model | Proposed output | Promotion ceiling |
| --- | --- | --- | --- |
| Layout and spatial document representation | `microsoft/layoutlmv3-base` | layout-aware page/region vectors | retrieval candidate only |
| Compact page parsing | `docling-project/SmolDocling-256M-preview` | candidate document structure and region text | OCR/layout-derived candidate |
| Table region detection | `microsoft/table-transformer-detection` | table bounding boxes | region candidate only |
| Table structure | `microsoft/table-transformer-structure-recognition` | row/column/cell candidates | layout-derived candidate |
| Visual family clustering | `facebook/dinov2-base` | page and crop embeddings | similarity route only |
| Zero-shot visual labels | `google/siglip2-base-patch16-224` | bounded page/crop labels | review label only |
| Region segmentation | `facebook/sam2-hiera-base-plus` | masks for stamps, signatures, tables, or overlays | candidate mask only |

## Do not send

- Native PDFs or bank/check images to public endpoints.
- Names, addresses, account numbers, Bates ranges, or exact case text to public model services.
- Unredacted signature crops to public Spaces.
- Raw evidence hashes paired with identifying filenames outside the private control plane.

## Safe execution modes

1. Local model cache with network disabled.
2. Private approved compute job with encrypted temporary storage and deletion receipt.
3. Redacted or synthetic test pages for public compatibility testing.

## Output fields

```text
model_id
model_revision
model_file_hashes
runtime_library_versions
input_derivative_sha256
input_redaction_status
page_or_crop_locator
embedding_dimension
embedding_sha256
candidate_label
candidate_score
nearest_neighbors
promotion_ceiling
human_review_required
```

## Model-provenance requirement

Record the exact model revision, downloaded file hashes, Transformers version, preprocessing configuration, image size, normalization, device, precision, and random seed. A model name alone is not reproducible provenance.

## Retrieval rules

- Exact hashes and native identifiers route before embeddings.
- DINOv2/SigLIP similarity may prioritize review but never merge source identities.
- LayoutLMv3/SmolDocling output remains separate from native text extraction.
- Table Transformer cell output must retain page coordinates and source locator.
- SAM masks must retain the prompt type and cannot be treated as object identity.

## Required hard negatives

- Repeated logos and letterhead.
- Blank forms and standard templates.
- Legitimate digital-signature widgets.
- Bank processing stamps.
- OCR/accessibility layers.
- Reprinted or regenerated copies with identical visible content.
- Repeated invoice layouts from one vendor.
