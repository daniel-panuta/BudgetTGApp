#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing virtual environment. Run scripts/setup.sh first."
  exit 1
fi

cd "$ROOT_DIR"

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker compose up -d db
  echo "Started local DB with docker compose"
else
  echo "Docker daemon not available. Skipping local DB startup."
  echo "If you use Neon DATABASE_URL, this is expected and safe."
fi

if [[ -f "$RUN_DIR/api.pid" ]] && kill -0 "$(cat "$RUN_DIR/api.pid")" 2>/dev/null; then
  echo "API already running."
else
  nohup "$ROOT_DIR/.venv/bin/python" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/api.log" 2>&1 &
  echo $! > "$RUN_DIR/api.pid"
  echo "Started API on :8000"
fi

if [[ -f "$RUN_DIR/bot.pid" ]] && kill -0 "$(cat "$RUN_DIR/bot.pid")" 2>/dev/null; then
  echo "Bot already running."
else
  nohup "$ROOT_DIR/.venv/bin/python" main.py > "$LOG_DIR/bot.log" 2>&1 &
  echo $! > "$RUN_DIR/bot.pid"
  echo "Started bot"
fi

if [[ -f "$RUN_DIR/frontend.pid" ]] && kill -0 "$(cat "$RUN_DIR/frontend.pid")" 2>/dev/null; then
  echo "Frontend already running."
else
  cd "$ROOT_DIR/frontend/miniapp"
  nohup npm run dev -- --host 0.0.0.0 --port 5173 > "$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$RUN_DIR/frontend.pid"
  echo "Started frontend on :5173"
fi

echo "All local services are up. Logs: $LOG_DIR"
