#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${1:-}"

if [[ -z "$API_URL" ]]; then
  echo "Usage: scripts/deploy_vercel.sh <API_URL>"
  echo "Example: scripts/deploy_vercel.sh https://budgetapp-api-gqlcvqw5aq-ew.a.run.app"
  exit 1
fi

if ! command -v vercel >/dev/null 2>&1; then
  echo "Vercel CLI is missing. Installing globally with npm..."
  npm install -g vercel
fi

cd "$ROOT_DIR/frontend/miniapp"

vercel deploy --prod --yes \
  --build-env "VITE_API_BASE_URL=$API_URL" \
  --env "VITE_API_BASE_URL=$API_URL"
