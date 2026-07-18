---
title: Multimodal Forensic Evidence Synthesis Engine
emoji: 🧬
colorFrom: blue
colorTo: purple
sdk: gradio
app_file: app.py
pinned: false
license: mit
short_description: Local/private PDF forensics, HF model routing, exact arithmetic, lifecycle firewalls, and evidence graphs.
---

# Multimodal Forensic Evidence Synthesis Engine

A local/private forensic document engine that combines deterministic PDF/image measurements, optional Hugging Face model candidates, exact arithmetic, document-role firewalls, chronology controls, and an evidence graph.

> **Models discover candidates. Deterministic extraction measures them. The evidence graph explains them. Native records prove or disprove them.**

## What it builds

1. **Source identity** — raw hashes, MIME type, size and native locator.
2. **PDF/image fingerprints** — revision structure, page hashes, pHash/dHash/HOG, embedded objects, fonts, scanner measurements and signature candidates.
3. **Document-role firewall** — proposal, invoice, draw request, payment, budget, delivery and other roles remain distinct.
4. **Pairwise fusion** — same binary, same visible/different provenance, visual-family, amount relation and lifecycle relation.
5. **Exact-sum solver** — identifies document combinations that assemble to a target while explicitly blocking causation claims.
6. **Lifecycle coverage** — proposal → draw → approval → funding → payment → vendor application → delivery → authorization → owner credit → final balance.
7. **Evidence graph** — source, role, amount, address, identifier, event and relation nodes/edges.
8. **Optional HF lanes** — DINOv2, SigLIP 2 and Table Transformer execute only after explicit opt-in. LayoutLMv3, SmolDocling, BGE-M3 and reranking are registered routes for later approved adapters.

## Privacy

- Network model execution is **off by default**.
- No raw case evidence belongs in GitHub or a public Hugging Face repository.
- Private manifests and generated reports should remain outside the code repository.
- Model outputs are always promotion-blocked candidates.
- Similarity, arithmetic, graph proximity and review scores are not proof of identity, intent, authorization, payment, damages, fraud or liability.

## Local installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

Optional HF models and Gradio:

```bash
pip install -e .[hf,space]
```

## Run a manifest

```bash
mfese run private-manifest.yaml --out mfese-output
```

## Scan files without a manifest

```bash
mfese scan file1.pdf file2.pdf --out mfese-output
```

## Manifest example

```yaml
matter_id: local-private-matter
privacy_mode: local_private
render_dpi: 150
enable_hf_lanes: []
sources:
  - source_id: proposal
    path: /private/path/proposal.pdf
    role_hint: proposal
  - source_id: draw
    path: /private/path/draw.pdf
    role_hint: draw_request
known_events:
  - event_id: funding-1
    stage: funding
    date: 2018-04-10
    amount: 100000
    proof_state: native_measurement
exact_sum_tasks:
  - task_id: request-assembly
    target: 100000
    source_ids: [proposal, draw]
```

## Outputs

- `mfese_report.json`
- `mfese_graph.json`
- `mfese_run_receipt.json`
- `mfese_output_manifest.json`

## Hugging Face architecture

The engine uses Hugging Face as a controlled model catalog/runtime, not as the evidence authority:

```text
native source → deterministic scan → page/region routing → HF candidate model
→ feature fusion → exact identifiers/accounting joins → evidence graph
→ missing-bridge queue → human/native-source verification
```
