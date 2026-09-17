#!/bin/sh
# Start the packaged CampusPulse demo without deleting any local data.
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

if [ "${1:-}" = "--build" ]; then
  docker compose up -d --build
else
  docker compose up -d
fi

echo "CampusPulse is starting. Run 'sh scripts/demo-healthcheck.sh' before presenting."
echo "Open http://localhost:5173 when the health check passes."
