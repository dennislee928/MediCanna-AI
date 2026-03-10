"""Bootstrap ML artifacts for inference.

This script trains artifacts only when required files are missing or empty.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REQUIRED_FILES = [
    Path("models/kmeans_model.pkl"),
    Path("models/tfidf_vectorizer.pkl"),
    Path("models/type_encoder.pkl"),
    Path("data/clustered_strains.csv"),
]


def missing_or_empty_files(base_dir: Path) -> list[Path]:
    missing: list[Path] = []
    for relative in REQUIRED_FILES:
        file_path = base_dir / relative
        if not file_path.exists() or file_path.stat().st_size == 0:
            missing.append(relative)
    return missing


def run_training(base_dir: Path) -> None:
    print("[bootstrap] required artifacts missing. running train_pipeline.py ...")
    subprocess.run([sys.executable, "train_pipeline.py"], cwd=base_dir, check=True)


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    missing = missing_or_empty_files(base_dir)
    if missing:
        print("[bootstrap] missing/empty artifacts:")
        for item in missing:
            print(f"  - {item}")
        run_training(base_dir)
    else:
        print("[bootstrap] artifacts already available. skipping training.")

    post_check = missing_or_empty_files(base_dir)
    if post_check:
        print("[bootstrap] artifact validation failed:")
        for item in post_check:
            print(f"  - {item}")
        return 1

    print("[bootstrap] artifacts ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
