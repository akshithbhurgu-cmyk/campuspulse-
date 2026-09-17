# CampusPulse hackathon demo runbook

## One-line problem statement

Students receive timetables, attendance pressure, assessments, and academic notices across disconnected tools. CampusPulse turns those signals into one explainable academic workspace that shows what matters now and why a plan changed.

## Before the jury arrives

From the project root, run:

```bash
sh scripts/demo-start.sh --build
sh scripts/demo-healthcheck.sh
```

Open <http://localhost:5173>. Keep a second tab open at <http://localhost:8000/docs> as a technical fallback. For the AI and announcement-extraction parts, make sure Ollama is running on the Mac and the configured Gemma model is available. Gmail is optional: use Paste Notice if OAuth is unavailable.

The normal start command preserves the existing local database. For a completely clean synthetic demo only, deliberately run `sh scripts/demo-reset.sh --fresh`; it destroys the local PostgreSQL volume and recreates the seeded Semester 5 data.

## Recommended 6–7 minute story

| Time | Screen and action | What to say |
| --- | --- | --- |
| 0:00 | Dashboard | “CampusPulse brings attendance, assessments, readiness, deadlines, and study availability into one decision view.” |
| 0:40 | Attendance / FOS | “FOS is risky: the impact view shows current attendance and the consequence of another skip, rather than giving a vague warning.” |
| 1:20 | Academics / Deep Learning preparation | “Deep Learning has low topic readiness. The system can point to the exact topics rather than treating every course equally.” |
| 2:00 | Announcements → Paste Notice | Paste a prepared academic notice, for example: `Deep Learning slip test has been preponed to Wednesday. It covers VGGNet and ResNet.` |
| 2:30 | Announcement preview | “Gemma reads unstructured text but produces a proposal only. Nothing changes until the student reviews and applies it.” |
| 3:00 | Apply | “Apply writes the approved record. CampusPulse then recalculates its deterministic academic engines.” |
| 3:30 | Dashboard, Updates, then Plan | “Here are the changed risk/priority signals and the timeline reason. The plan can be saved, previewed, and selectively replanned while preserving locked sessions.” |
| 4:50 | CampusPulse AI | Ask: `Can I skip FOS tomorrow to prepare for DL?` |
| 5:40 | AI answer and source context | “The agent consults real CampusPulse data and explains trade-offs. It does not invent or directly change data.” |
| 6:20 | Close | “The key distinction is: AI interprets language and explains; deterministic rules make the academic calculations and all changes remain reviewable.” |

## Demo guardrails

- Do not press **Apply** until the preview clearly identifies the intended course and assessment/date.
- Keep one prepared notice in a text file or clipboard. It is a better fallback than Gmail because it is deterministic and demonstrates the same review-first flow.
- Let a local-model answer finish before speaking over it; local inference can take longer than cloud chat.
- If the database already contains a previous applied version of the notice, use a differently worded notice or reset before the demo.
- Never show `credentials.json`, `gmail_token.json`, `.env`, or Google Cloud screens to the jury.

## Technical explanation in 30 seconds

The React app is served by Nginx and sends `/api` calls to FastAPI. FastAPI stores academic data in PostgreSQL. Its attendance, risk, priority, conflict, planning, and replanning engines are deterministic Python services. Gemma through Ollama is local to the Mac and only interprets notices or answers questions over backend-provided data. Docker packages the frontend, backend, and database so the demo starts consistently; Ollama intentionally stays outside Docker because it uses the host model runtime.

For the complete technical picture, see [ARCHITECTURE.md](ARCHITECTURE.md) and [JURY_QA.md](JURY_QA.md).
