# Fraud Clarity Review Skill

This Hugging Face-ready package contains a private, case-review skill and deterministic routing script for fraud-clarity analysis.

## Files

```text
skills/fraud_clarity_review/SKILL.md
scripts/fraud_clarity_router.py
```

## Intended repository type

Use a **private dataset repository** or a **private Space** if storing any case-specific material. Do not upload native case evidence unless access controls have been intentionally set.

## Local use

```bash
python scripts/fraud_clarity_router.py evidence.json --focus pivot --out fraud_review.md
```

## Hub upload pattern

```python
from huggingface_hub import create_repo, upload_folder

repo_id = "Bbbr8/fraud-clarity-skill"
create_repo(repo_id=repo_id, repo_type="dataset", private=True, exist_ok=True)

upload_folder(
    folder_path=".",
    repo_id=repo_id,
    repo_type="dataset",
    ignore_patterns=[".git/*", "__pycache__/*", "*.zip"],
)
```

## Caution

This skill is for routing and counsel review. It identifies fraud indicators, bridge-record gaps, reliance issues, and accounting/discovery questions. It does not make legal conclusions.
