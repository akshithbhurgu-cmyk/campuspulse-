#!/bin/sh
# Fast pre-demo check for the packaged app. Ollama is optional, but required for AI/extraction.
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

printf '%s\n' "Checking Docker services..."
docker compose ps

printf '%s\n' "Checking FastAPI..."
curl --fail --silent --show-error http://localhost:8000/health >/dev/null
printf '%s\n' "  FastAPI: ready"

printf '%s\n' "Checking browser proxy..."
curl --fail --silent --show-error http://localhost:5173/api/health >/dev/null
printf '%s\n' "  Frontend proxy: ready"

printf '%s\n' "Checking seeded dashboard..."
curl --fail --silent --show-error http://localhost:8000/dashboard >/dev/null
printf '%s\n' "  Seeded dashboard: ready"

if curl --fail --silent --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
  printf '%s\n' "  Ollama: reachable (AI chat and notice extraction available)"
else
  printf '%s\n' "  Ollama: not reachable from the Mac. Dashboard still works; start Ollama before the AI/extraction portion."
fi

printf '%s\n' "Demo health check complete."
