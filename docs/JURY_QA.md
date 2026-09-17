# CampusPulse jury Q&A

## What problem does CampusPulse solve?

It reduces academic overload from disconnected attendance portals, notices, calendars, and personal planning. It makes risk and study decisions visible in one place and explains the reason for each change.

## Is this just a chatbot?

No. The core product is a database-backed academic dashboard and deterministic decision engines. The local LLM is limited to interpreting unstructured notices and explaining data the backend provides. It cannot silently alter records.

## Why use an LLM if rules are safer?

Rules are safer for calculations, so the engines use rules. An LLM is useful where formats vary: an email may say “DL test preponed” in many ways. It converts that language into a reviewable proposal; the student must approve it before the backend writes anything.

## What happens after an announcement is applied?

FastAPI creates the approved academic record, refreshes the computed dashboard signals, stores a change-history entry, and exposes the updated data to the planner/replanner. The UI shows both the change and its reason.

## How does the attendance recommendation work?

It is calculated from conducted and attended classes plus the configured attendance target. The impact endpoint shows how a skip or recovery class would affect the current position. Invalid counts are rejected rather than silently producing misleading results.

## How does the study plan remain trustworthy?

The planner only uses stored availability, academic priorities, and conflict checks. Locked study sessions are protected during selective replanning. When available time is insufficient, the product reports that constraint instead of pretending a complete plan exists.

## How is Gmail handled safely?

Gmail access is optional, read-only, and authorised with the student’s OAuth account. Messages are converted into previews, not applied records. OAuth credentials/tokens are local-only and excluded from version control and Docker images.

## Why Docker?

Docker runs the frontend, backend, and PostgreSQL together with the same configuration every time. The backend entrypoint applies migrations and idempotent demo seed data. This reduces “works on my machine” issues during the presentation. Ollama stays host-side and is reached through `host.docker.internal`.

## What happens if Ollama or Gmail is unavailable?

The main dashboard, direct APIs, plans, and deterministic engines still work. AI chat and extraction return a safe unavailable error; the demo falls back to the preloaded data and a prepared paste notice once Ollama returns.

## How is the system explainable?

Each material change is surfaced in the Updates view with a before/after summary and reason. The agent response also grounds itself in backend facts rather than making an unsourced recommendation.

## What remains outside the current scope?

Production authentication, push notifications, cloud deployment, institution-wide multi-user administration, and automatic background Gmail polling are intentionally out of scope for the prototype.
