#!/bin/sh
# Intentionally destructive demo reset. It only runs with the explicit --fresh flag.
set -eu

if [ "${1:-}" != "--fresh" ]; then
  echo "Refusing to erase the local demo database."
  echo "Usage: sh scripts/demo-reset.sh --fresh"
  exit 2
fi

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

echo "Removing the CampusPulse PostgreSQL volume and rebuilding the seeded demo state..."
docker compose down -v
docker compose up -d --build
echo "Fresh demo data is being created by the backend entrypoint."
echo "Run 'sh scripts/demo-healthcheck.sh' until all checks pass."
