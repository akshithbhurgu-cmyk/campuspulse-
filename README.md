# CampusPulse

CampusPulse is a local-first academic operations workspace: React, FastAPI, PostgreSQL, deterministic planning engines, a local Ollama/Gemma agent, review-first ingestion, replanning, and an explainable change timeline.

## Quick start

Prerequisite: Docker Desktop running. Ollama is optional for ordinary dashboard use, but required for AI chat and notice extraction.

```bash
cd "/Users/bhurguakshith/Documents/ChatGPT/campus pulse"
cp .env.example .env
docker compose up --build
```

Open the app at <http://localhost:5173>, API docs at <http://localhost:8000/docs>, and health check at <http://localhost:8000/health>.

The backend runs Alembic migrations and the idempotent synthetic Semester 5 seed automatically. A fresh local database therefore starts with `docker compose up` alone.

Stop with `docker compose down`. PostgreSQL data remains in `postgres_data`. To deliberately erase the local database, run `docker compose down -v`.

## Packaged services

| Service | Purpose | Local address |
| --- | --- | --- |
| `frontend` | Nginx-served React production build | <http://localhost:5173> |
| `backend` | FastAPI, migrations, seed and engines | <http://localhost:8000> |
| `db` | PostgreSQL 16 | `localhost:5432` |

The frontend uses an Nginx `/api` reverse proxy to FastAPI, so the packaged browser app needs no CORS setup.

## Local Ollama / Gemma

Ollama stays on your Mac. The backend reaches it through `http://host.docker.internal:11434`.

```bash
ollama serve
ollama list
```

The default model is `gemma4:e4b`; change `OLLAMA_MODEL` in `.env` if needed. If Ollama is offline, dashboards and direct APIs still work; AI chat and extraction return a safe error.

## Gmail (optional)

Gmail is read-only and optional. OAuth files are excluded from Git and Docker images. To enable local Gmail ingestion, create a local Compose override that mounts your user-owned files:

```yaml
services:
  backend:
    volumes:
      - ./backend/credentials.json:/app/credentials.json:ro
      - ./backend/gmail_token.json:/app/gmail_token.json
```

Never commit these files. Gmail messages remain review previews until you choose Apply or Ignore.

## Configuration and verification

Copy `.env.example` to `.env`; never commit it or put secrets in frontend variables.

```bash
cd backend
../.venv/bin/python -m unittest discover -s tests

cd ../frontend
npm ci
npm run build
```

Before publishing to GitHub, verify no `.env`, OAuth JSON, tokens, virtual environments, build output, or `node_modules` are staged. The supplied `.gitignore` excludes them.

## Hackathon demo

Phase 18 adds a safe demo start command, a deliberate fresh-reset command, and a preflight health check:

```bash
sh scripts/demo-start.sh --build
sh scripts/demo-healthcheck.sh
```

`demo-start.sh` keeps existing local data. Only `sh scripts/demo-reset.sh --fresh` removes the local PostgreSQL volume and recreates seeded data. Use it only when you explicitly want to discard local changes.

The presenter package is in [docs/DEMO_RUNBOOK.md](docs/DEMO_RUNBOOK.md): it includes the timed story, architecture, technical explanation, jury Q&A, and a checklist for a short fallback recording and screenshots.
