# CampusPulse

CampusPulse is a semester-planning application. The repository currently contains Phases 1–10: infrastructure, the academic schema, synthetic Semester 5 data, direct academic APIs, deterministic decision/planning engines, a unified dashboard API, an academic frontend, a typed backend tool layer, and a read-only local LangGraph/Ollama agent.

## Local agent orchestration (Phase 10)

Phase 10 adds a read-only LangGraph loop between FastAPI, Ollama, the local `gemma4:e4b` model, and the Phase 9 tool layer. `POST /agent/query` accepts a question and a development `student_id`, then returns the model answer, model name, and tools used. The agent can read courses, attendance, assessments, assignments, calendar, preparation, and dashboard data. It deliberately cannot modify topic progress, events, availability, or plans. There is no frontend chat interface, tool-write approval flow, history, or autonomous replanning yet.

With Ollama running on your Mac, Docker Compose reaches it through `host.docker.internal`. Copy the `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and optional `OLLAMA_TIMEOUT_SECONDS` values from `.env.example` into `.env` if you want to override the defaults. Requests have a 120-second model timeout and a bounded tool-call loop. A quick backend check after rebuilding is:

```bash
curl -X POST http://localhost:8000/agent/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is my attendance situation?"}'
```

## Tool layer (Phase 9)

`backend/app/tools/campuspulse.py` exposes typed, framework-independent operations over the existing services. It provides student-scoped reads for courses, attendance and impact, assessments, assignments, calendar, preparation, and dashboard data; plus validated writes for topic progress, personal events, and availability. It has no HTTP route, LLM, LangGraph, or agent-framework dependency. A later orchestration phase can adapt this stable boundary without duplicating academic logic.

## Frontend workspace (Phases 7–8)

React, TypeScript, Vite, and Tailwind provide responsive navigation, Dashboard, Calendar, Academics, Course Detail, Preparation, and Plan screens. Phase 8 adds the academic workspace: attendance outlook, upcoming assessments and pending assignments, topic-level preparation updates, and forms to add personal events and dated availability blocks. These use the existing FastAPI endpoints; the browser does not recalculate academic scores or decision-engine outputs. Announcements and CampusPulse AI remain explicitly labelled placeholders for later phases.

Start Docker/backend below, apply migrations, and seed the database. Then in another terminal:

```bash
cd "/Users/bhurguakshith/Documents/ChatGPT/campus pulse/frontend"
cp .env.example .env
npm ci
npm run dev
```

Open the local URL printed by Vite (normally <http://127.0.0.1:5173>). The Vite development proxy forwards `/api` to `BACKEND_URL` (default `http://127.0.0.1:8000`), avoiding browser CORS issues. `VITE_API_BASE_URL` defaults to `/api`; do not place secrets in `VITE_` variables. All screens currently use synthetic student #1; this is not authentication. Calendar views use the current campus timezone, Asia/Kolkata; dashboard timestamps use the timezone returned by the backend.

```bash
npm run build
```

This checks TypeScript and creates `frontend/dist`. Production hosting/proxy setup and frontend Docker integration remain later phases; `vite preview` does not provide the development backend proxy. The frontend intentionally has no agent tools, LLM calls, or persistent study-plan actions.

Phase 8 verification: production build and formatting checks passed. Browser checks covered course navigation, attendance outlook, topic-progress save, assessment/assignment workspace, and the calendar forms using the live Docker/FastAPI stack. The complete Phase 1–7 debugging pass also verified PostgreSQL migrations, seed idempotency, all live API routes, and all 29 backend tests.

## Included in Phases 1–6

- FastAPI backend with `GET /health`
- PostgreSQL 16 via Docker Compose
- SQLAlchemy database configuration
- Alembic migration setup, ready for Phase 2 models
- Environment configuration through `.env`
- Academic-state schema with 20 PostgreSQL tables and relationships
- An initial Alembic migration that creates the academic schema
- A safe, idempotent Phase 3 seed command for a synthetic Semester 5 scenario
- Phase 4 direct APIs for the academic state
- Deterministic attendance, risk, priority, conflict, availability, planning, and replanning engines
- Unit tests covering normal behavior and important planning edge cases
- A read-only dashboard combining the academic services and deterministic engines

## Run with Docker

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Start the backend and database:

   ```bash
   docker compose up --build
   ```

3. In another terminal, verify the service:

   ```bash
   curl http://localhost:8000/health
   ```

   Expected response:

   ```json
   {"status":"ok"}
   ```

The interactive API documentation is available at <http://localhost:8000/docs>.

## Direct academic APIs

After applying the migration and seed data, Swagger exposes the Phase 4 endpoints:

```text
GET   /courses
GET   /dashboard
GET   /courses/{course_id}
GET   /attendance
GET   /attendance/{course_id}
GET   /attendance/{course_id}/impact
GET   /assessments?upcoming_only=true
GET   /assignments?pending_only=true
GET   /calendar
GET   /preparation
PATCH /topics/{topic_id}/progress
POST  /personal-events
POST  /availability
```

All endpoints default to the seeded student (`student_id=1`). The `student_id` query parameter is present so the service layer is ready to support additional students later.

## Deterministic engines

Phase 5 contains pure Python engines for attendance impact, academic risk percentages, weighted priorities, schedule conflicts, free-slot calculation, study-plan generation, and affected-session-only replanning. They do not call an LLM.

Run the engine tests with:

```bash
docker compose run --rm backend python -m unittest discover -s tests -v
```

## Dashboard API (Phase 6)

After rebuilding the backend, applying migrations, and seeding the database:

```bash
curl http://localhost:8000/dashboard
```

`GET /dashboard?student_id=1` returns:

- `next_class`: the next not-yet-started class within 14 days, respecting semester dates and holidays; `null` when none exists.
- `today_plan`: the stored non-archived plan for the local date, or a non-persisted planning preview when no stored plan exists.
- `plan_source`: `saved` or `preview`, including empty saved plans.
- `top_priorities`: up to five pending assessments/assignments ranked by the Phase 5 engine. Overdue work stays visible; completed, cancelled, and submitted work is excluded. Future dated work is limited to 14 days.
- `risks`: up to ten current attendance/task/conflict signals scoring at least 45. Scores are heuristic urgency indicators, not calibrated probabilities.
- `recent_changes`: up to ten real change-history records, newest first. This remains empty until actual history records are created; announcements are not fabricated history.
- `unscheduled_minutes`: work that does not fit in today's preview; overdue work is not scheduled. For saved plans this is empty because the dashboard does not rebuild them.
- `generated_at` and `timezone`: the time and campus timezone used for the snapshot.

The endpoint never inserts or updates risks, priorities, study plans, sessions, or history. Generating and applying persistent plans and automatic replanning remain later workflow work.

Preparation uses exact linked assessment topics where provided, otherwise the course average. Missing marks are not treated as poor performance. Effort estimates use each topic's estimated minutes (60-minute fallback), 120 minutes per assignment, or a 240-minute unlinked-assessment estimate scaled by preparation; these assumptions are exposed in each priority's `estimate_source`.

Study previews use only explicitly declared availability and subtract college classes, personal events, timed exams, unavailable/locked blocks, and existing planned sessions. Overlapping availability is merged; no available time is invented.

`CAMPUS_TIMEZONE` defaults to `Asia/Kolkata`. Recurring timetable and availability times are campus-local; timestamped events preserve their absolute instant. The existing synthetic seed uses UTC timestamps, so its event clock times may differ when displayed locally. This endpoint's student selector is not authentication; keep the development stack local.

## Apply the academic schema

After the containers are running, apply the Phase 2 migration:

```bash
docker compose run --rm backend alembic upgrade head
```

## Load the synthetic Semester 5 scenario

Phase 3 adds a clearly synthetic but internally consistent Semester 5 student: nine courses, syllabus units and topics, timetable, academic calendar, attendance, marks, upcoming assessments and assignments, announcements, availability, and topic-level preparation.

```bash
docker compose run --rm backend python -m app.seed
```

The command is idempotent: after creating the scenario once, later runs leave it unchanged.

To create a future migration:

```bash
docker compose run --rm backend alembic revision --autogenerate -m "describe change"
docker compose run --rm backend alembic upgrade head
```

The initial migration creates the student, semester, course, syllabus, attendance, assessment, calendar, preparation, planning, risk, priority, and change-history tables. The Phase 3 seed command populates that schema with the synthetic Semester 5 scenario.
