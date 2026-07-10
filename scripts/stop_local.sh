#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"

stop_pid() {
  local name="$1"
  local pid_file="$2"

  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      echo "Stopped $name ($pid)"
    fi
    rm -f "$pid_file"
  fi
}

stop_pid "API" "$RUN_DIR/api.pid"
stop_pid "Bot" "$RUN_DIR/bot.pid"
stop_pid "Frontend" "$RUN_DIR/frontend.pid"

cd "$ROOT_DIR"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker compose stop db >/dev/null 2>&1 || true
fi

echo "Local services stopped."
