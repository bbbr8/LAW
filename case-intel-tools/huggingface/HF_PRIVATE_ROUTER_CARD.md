# Hugging Face Private Router Card

Status: private derivative routing only. Do not upload raw evidence, native records, signatures, bank statements, confidential exhibits, or attorney work product.

## Role of Hugging Face

Hugging Face is useful for semantic routing, clustering, and reranking. It is not the evidence repository and it does not replace native/source review.

## Safe data policy

Allowed:

- Redacted claim rows.
- Synthetic examples.
- Non-sensitive labels.
- Source-status categories.
- Case-lane names.
- Derived embeddings from reviewed/redacted text when privacy-cleared.

Not allowed:

- Raw evidence files.
- Native PDFs.
- Bank records.
- Signature images.
- Deposition transcripts.
- Full private communications.
- Personal identifiers not required for routing.

## Recommended model routing

| Job | Model family | Reason |
| --- | --- | --- |
| Fast semantic clustering | `sentence-transformers/all-MiniLM-L6-v2` | Fast, high-use baseline for sentence similarity. |
| Higher-quality semantic routing | `sentence-transformers/all-mpnet-base-v2` | Stronger general-purpose semantic matching. |
| Question-to-record retrieval | `sentence-transformers/multi-qa-mpnet-base-dot-v1` | Designed for query-to-answer/document matching. |
| Final reranking | `BAAI/bge-reranker-v2-m3` | Reranks candidate matches after embedding retrieval. |
| Multilingual or paraphrase-heavy search | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Handles broader paraphrase/language variation. |

## Pipeline

```text
Redacted visual registry rows
→ source-status normalization
→ embedding generation
→ nearest-neighbor candidate retrieval
→ reranker pass
→ route to visual lane
→ human review
→ Google Drive source closure
→ Figma/GitHub visual export
```

## Output labels

Every routed record should receive:

```text
claim_id
semantic_cluster
recommended_visual_lane
recommended_visual_type
source_status
bridge_needed
conflict_type
confidence_band
human_review_required
```

## Confidence bands

| Band | Meaning | Action |
| --- | --- | --- |
| High | Strong semantic match to an existing lane. | Route, then verify source. |
| Medium | Useful candidate but needs human review. | Queue for review. |
| Low | Weak match or ambiguous lane. | Do not use for export. |

## Anti-contamination rule

Semantic similarity is not proof. A model can route a row to a lane, but it cannot close native proof, authenticate a document, resolve a source conflict, or calculate damages.

## Private Space idea

A private Space can expose a review screen with:

- Upload redacted CSV.
- Run source-status normalization.
- Cluster similar claims.
- Recommend visual type.
- Flag bridge-missing records.
- Export a clean visual registry CSV for Google Drive/Figma.

No public Space should contain raw case data.
