#!/bin/bash
# ─── RunPod entry point ────────────────────────────────────────────────────────
# Usage:
#   bash runpod_run.sh --source /workspace/data --output /workspace/out
#
# Full backend (GPU recommended for Stage 6):
#   bash runpod_run.sh --source /workspace/data/marine-acoustic-core --output /workspace/out
#
# Skip GPU-heavy clustering:
#   bash runpod_run.sh --source /workspace/data --output /workspace/out --no-cluster

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Installing dependencies ==="
pip install -r requirements.txt

echo "=== Running pipeline ==="
python -m backend.run "$@"
