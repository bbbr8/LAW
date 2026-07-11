# Hugging Face hybrid search

This module adds local semantic ranking to the existing case-profile app without turning AI output into evidence.

## Search sequence

1. Preserve exact IDs, Bates labels, dates, amounts, source URLs, and locators.
2. Run a cheap lexical prefilter over no more than 200 supplied chunks.
3. Skip the model entirely for exact lookups.
4. For ordinary conceptual questions, embed only the top 24 candidates in `fast` mode or top 60 in `deep` mode.
5. Combine lexical and semantic scores while returning the original source anchor unchanged.
6. Fall back to lexical ranking if the model is unavailable.

The default model is `onnx-community/bge-small-en-v1.5-ONNX`, downloaded from Hugging Face and executed locally with Transformers.js. Case text is not sent to a hosted inference endpoint by this module.

## Environment controls

```bash
HF_SEARCH_ENABLED=true
HF_EMBED_MODEL=onnx-community/bge-small-en-v1.5-ONNX
HF_EMBED_DTYPE=q8
HF_CACHE_DIR=./server/.hf-cache
```

Set `HF_SEARCH_ENABLED=false` to force deterministic lexical-only behavior.

## API

`POST /api/ai-search`

```json
{
  "query": "Which records connect Draw 3 to the window payment?",
  "mode": "fast",
  "limit": 10,
  "chunks": [
    {
      "id": "stable-source-id",
      "title": "Draw 3 support",
      "text": "Extracted passage text",
      "source": "Google Drive file URL or immutable source ID",
      "locator": "page 14 / row 22",
      "metadata": { "sha256": "...", "sourceTier": "native" }
    }
  ]
}
```

The endpoint ranks candidate passages. It does not generate conclusions, merge entities, or promote an AI link to a confirmed fact.

## Deep mode

The Drive roadmap's heavier `BAAI/bge-m3` plus `BAAI/bge-reranker-v2-m3` pipeline remains appropriate for offline batch review. Keep it separate from the default interactive path so routine searches do not pay the latency and memory cost of the larger models.
