#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="python3"

if [[ -x "${ROOT_DIR}/ml-python-engine/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/ml-python-engine/.venv/bin/python"
fi

echo "[contract] running Rust gateway tests..."
(cd "$ROOT_DIR/backend-rust-gateway" && cargo test)

echo "[contract] running ML API contract tests..."
(cd "$ROOT_DIR/ml-python-engine" && "$PYTHON_BIN" -m pytest -k contract -q)

echo "[contract] complete."
