# Hub Publish Notes

Use a private Hugging Face Space for the Case Control System when case-specific material is involved.

## Manual publish pattern

1. Create a private Gradio Space named `case-control-system` under the Bbbr8 account.
2. Upload the contents of `case_control_system/` to the Space root.
3. Keep `app.py`, `requirements.txt`, `scripts/`, `CASE_CONTROL_SKILL.md`, `schemas/`, `templates/`, and `examples/` together.
4. Do not upload native evidence to a public repository.

## GitHub Actions sync

Add a repository secret named `HF_TOKEN`, then enable the sync workflow. The workflow is intentionally manual-capable through `workflow_dispatch`.
