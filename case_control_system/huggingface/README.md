---
title: Case Control System
emoji: 🧭
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
---

# Case Control System

Private Hugging Face Space wrapper for the Case Control Engine.

## Use

Paste JSON, JSONL, CSV, TXT, or Markdown evidence records into the interface. The app returns a full case-control report plus routed JSONL.

## Safety / access

Use a private Space or private dataset repository for case-specific material. Do not upload native case evidence to a public repository.

## GitHub sync

The workflow in `.github/workflows/sync-case-control-to-hf.yml` can sync this package to Hugging Face after adding an `HF_TOKEN` secret.
