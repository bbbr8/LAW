# Visual Document Model Router

Status: model-routing note for private/redacted document-layout review.

## Why this layer exists

Some records fail when reduced to plain OCR text. Tables, page regions, invoices, statements, budgets, and layout-sensitive pages need visual-document routing before they become chart data.

## Model lanes checked on Hugging Face

| Use | Candidate model | Use boundary |
| --- | --- | --- |
| Layout-aware document classification | `microsoft/layoutlmv3-base` | Candidate for private layout-aware experiments after data review. |
| Table detection | `microsoft/table-transformer-detection` | Finds table regions before extraction or chart routing. |
| Document question answering | `naver-clova-ix/donut-base-finetuned-docvqa` | Controlled visual-question tests on redacted images. |
| Final semantic reranking | `BAAI/bge-reranker-v2-m3` | Reranks redacted claim candidates after embedding retrieval. |
| Fast semantic grouping | `sentence-transformers/all-MiniLM-L6-v2` | Fast baseline for clustering and duplicate detection. |
| Higher-quality semantic grouping | `sentence-transformers/all-mpnet-base-v2` | Stronger semantic matching for review queues. |

## Visual-native-required trigger

Send a record to the visual-document lane if any of these are true:

- table structure changes the meaning;
- a page region, mark, stamp, footer, or label matters;
- address, job label, vendor name, account number, or document number appears in a specific page area;
- row or column alignment affects the conclusion;
- OCR text is incomplete, scrambled, or detached from layout;
- a chart depends on values extracted from a table or statement page.

## Output contract

```text
record_id
document_type
visual_native_required
page_locator
layout_issue
table_detected
recommended_extraction_route
source_status
bridge_needed
review_required
```

## Review sequence

```text
1. Route page to visual-document lane.
2. Identify whether layout, table structure, attribution, or page placement matters.
3. Detect tables or regions if useful.
4. Extract redacted candidate values.
5. Label every extraction as OCR-derived or layout-derived.
6. Route candidate values back to Google Drive native/source closure.
7. Only then pass values to charting tools.
```

## Anti-contamination rule

A layout model can help find a table, region, or visual issue. It cannot close a source record, validate an accounting chain, or replace native source review.
