# Reproducible Source Build

This folder provides a scaffold for regenerating structured outputs from a controlled document folder.

Keep source files outside this public repository. Put source files in a private local `input/` folder, then run the scripts here to generate repeatable CSV and JSON outputs.

## Goals

1. Hash every input before extraction.
2. Rebuild table outputs and review queues from a manifest.
3. Run reconciliation tests before copying results into a review workbook.
4. Separate source text, automated extraction, and human review.

## Local layout

```text
input/                  # private source files; do not commit
outputs/                # generated CSV/JSON; review before sharing
evidence-build/
  config/
  scripts/
  schemas/
  tests/
```

## Boundary

This scaffold is for repeatable document review workflows. It does not replace native records or human review.