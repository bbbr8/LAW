from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy MFESE as a private Hugging Face Gradio Space.")
    parser.add_argument("--repo-id", default="Bbbr8/multimodal-forensic-evidence-synthesis")
    parser.add_argument("--public", action="store_true", help="Public deployment is opt-in; private is the default.")
    args = parser.parse_args()
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN with write permission is required.")
    root = Path(__file__).resolve().parent
    api = HfApi(token=token)
    api.create_repo(
        repo_id=args.repo_id,
        repo_type="space",
        space_sdk="gradio",
        private=not args.public,
        exist_ok=True,
    )
    result = api.upload_folder(
        repo_id=args.repo_id,
        repo_type="space",
        folder_path=str(root),
        ignore_patterns=[
            "tests/**", "synthetic/packet/**", "__pycache__/**", ".pytest_cache/**", "*.pyc",
            "private-manifests/**", "mfese-output/**", "*.pdf", "*.png", "*.jpg", "*.jpeg", "*.zip",
        ],
        commit_message="Deploy Multimodal Forensic Evidence Synthesis Engine",
    )
    print(result)
    print(f"https://huggingface.co/spaces/{args.repo_id}")


if __name__ == "__main__":
    main()
