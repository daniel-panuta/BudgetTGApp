#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"
"$ROOT_DIR/.venv/bin/python" -m unittest tests/test_business_logic.py
"$ROOT_DIR/.venv/bin/python" tests/test_parser.py

cd "$ROOT_DIR/frontend/miniapp"
npm run build

cd "$ROOT_DIR"
rm -rf frontend/miniapp/dist frontend/miniapp/tsconfig.tsbuildinfo
find . -path './.git' -prune -o -path './.venv' -prune -o -name '__pycache__' -type d -exec rm -rf {} +

echo "Checks complete."
