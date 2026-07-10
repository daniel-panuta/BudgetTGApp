#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ID="${1:-budget-app-500512}"
REGION="${2:-europe-west1}"
SERVICE_NAME="${3:-budgetapp-api}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/budgetapp/backend:latest"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is not installed or not in PATH."
  exit 1
fi

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing virtual environment. Run scripts/setup.sh first."
  exit 1
fi

cd "$ROOT_DIR"

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud config set run/region "$REGION" >/dev/null

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com >/dev/null

gcloud artifacts repositories describe budgetapp --location="$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create budgetapp --repository-format=docker --location="$REGION" >/dev/null

cat > /tmp/budgetapp-cloudbuild.yaml <<EOF
steps:
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - -f
      - backend/Dockerfile
      - -t
      - ${IMAGE}
      - .
images:
  - ${IMAGE}
EOF

gcloud builds submit --config /tmp/budgetapp-cloudbuild.yaml .

# Extract environment variables from .env and set them in Cloud Run
"$ROOT_DIR/.venv/bin/python" - <<'PY'
import os
from dotenv import dotenv_values

values = dotenv_values('.env')

# Build env-vars list for gcloud
env_vars = []
env_vars.append(f"DATABASE_URL={values.get('DATABASE_URL', '')}")
env_vars.append(f"LOG_LEVEL={values.get('LOG_LEVEL', 'INFO')}")
env_vars.append("API_NAME=BudgetApp API")
env_vars.append("API_VERSION=0.1.0")

# Write to file - one per line, gcloud will parse it correctly
with open('/tmp/cloudrun-env.txt', 'w') as f:
    for var in env_vars:
        f.write(var + '\n')
PY

# Read environment variables and pass them to gcloud run deploy
ENV_VARS=$(cat /tmp/cloudrun-env.txt | tr '\n' ',' | sed 's/,$//')

gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --image "$IMAGE" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars "$ENV_VARS" >/dev/null

URL="$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
echo "Cloud Run URL: $URL"
curl -fsS "$URL/health" && echo
