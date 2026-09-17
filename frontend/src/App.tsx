import { useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Route, Routes, useParams } from "react-router-dom";
import { send, useApi } from "./api";
import type {
  Assignment,
  Assessment,
  AttendanceImpact,
  Calendar,
  Course,
  CourseDetail,
  Dashboard,
  Preparation,
  Topic,
  Unit,
} from "./types";

const timezone = "Asia/Kolkata";
const stamp = (value: string | null, zone = timezone) =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: zone,
      }).format(new Date(value))
    : "Not scheduled";
const percent = (value: number | null) =>
  value === null ? "Not recorded" : `${value.toFixed(1)}%`;
const pages = [
  ["/", "Dashboard"],
  ["/calendar", "Calendar"],
  ["/academics", "Academics"],
  ["/preparation", "Preparation"],
  ["/announcements", "Announcements"],
  ["/plan", "Plan"],
  ["/ai", "CampusPulse AI"],
];

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="card">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
function DataView<T>({
  path,
  children,
}: {
  path: string;
  children: (data: T, refresh: () => void) => ReactNode;
}) {
  const { data, loading, error, retry } = useApi<T>(path);
  if (loading)
    return (
      <div className="card" role="status">
        Loading your semester…
      </div>
    );
  if (error)
    return (
      <div className="card" role="alert">
        <h2>Couldn’t load semester data</h2>
        <p>{error}</p>
        <p>
          Check that the backend is running and the database has been migrated
          and seeded. This is a local development app, not an authenticated
          student portal.
        </p>
        <button onClick={retry}>Try again</button>
      </div>
    );
  return data !== null ? children(data, retry) : null;
}
function TopicProgress({ topic }: { topic: Topic }) {
  const [value, setValue] = useState(topic.completion_percentage);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  async function save() {
    setSaving(true);
    setMessage(null);
    try {
      const saved = await send<Topic>(`/topics/${topic.id}/progress`, "PATCH", {
        completion_percentage: value,
      });
      setValue(saved.completion_percentage);
      setMessage("Saved");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Could not save progress.",
      );
    } finally {
      setSaving(false);
    }
  }
  return (
    <li className="topic-row">
      <label htmlFor={`topic-${topic.id}`}>{topic.title}</label>
      <div className="topic-control">
        <input
          id={`topic-${topic.id}`}
          type="range"
          min="0"
          max="100"
          step="5"
          value={value}
          onChange={(event) => setValue(Number(event.target.value))}
          aria-label={`${topic.title} preparation`}
        />
        <output>{value.toFixed(0)}%</output>
        <button
          type="button"
          className="small-button"
          onClick={save}
          disabled={saving}
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
      {message && (
        <small className={message === "Saved" ? "success" : "form-error"}>
          {message}
        </small>
      )}
    </li>
  );
}
function Units({
  units,
  editable = false,
}: {
  units: Unit[];
  editable?: boolean;
}) {
  return (
    <div className="stack">
      {units.map((unit) => (
        <Card key={unit.id} title={`Unit ${unit.sequence} · ${unit.title}`}>
          <ul className="rows">
            {unit.topics.map((topic) =>
              editable ? (
                <TopicProgress key={topic.id} topic={topic} />
              ) : (
                <li key={topic.id}>
                  <span>{topic.title}</span>
                  <span>{percent(topic.completion_percentage)}</span>
                </li>
              ),
            )}
          </ul>
        </Card>
      ))}
      {!units.length && <p>No syllabus units recorded.</p>}
    </div>
  );
}
function AttendanceInsight({ courseId }: { courseId: number }) {
  return (
    <DataView<AttendanceImpact> path={`/attendance/${courseId}/impact`}>
      {(impact) => (
        <Card title="Attendance outlook">
          <div className="metric-grid">
            <div>
              <small>Current</small>
              <strong>{percent(impact.attendance_percentage)}</strong>
            </div>
            <div>
              <small>Target</small>
              <strong>{percent(impact.target_percentage)}</strong>
            </div>
            <div>
              <small>Attend next</small>
              <strong>{percent(impact.if_next_attended_percentage)}</strong>
            </div>
            <div>
              <small>Miss next</small>
              <strong>{percent(impact.if_next_missed_percentage)}</strong>
            </div>
          </div>
          <p className="muted">
            {impact.safe_skips > 0
              ? `${impact.safe_skips} class${impact.safe_skips === 1 ? "" : "es"} can be missed while staying at the target.`
              : impact.recovery_classes
                ? `${impact.recovery_classes} consecutive attended class${impact.recovery_classes === 1 ? "" : "es"} needed to reach the target.`
                : "You are at the attendance target."}
          </p>
        </Card>
      )}
    </DataView>
  );
}
function AcademicWork() {
  return (
    <div className="stack">
      <DataView<Assessment[]> path="/assessments?upcoming_only=true">
        {(items) => (
          <Card title="Upcoming assessments">
            <ul className="rows">
              {items.map((item) => (
                <li key={item.id}>
                  <div>
                    <strong>{item.title}</strong>
                    <small>
                      {item.course_code} · {item.assessment_type} ·{" "}
                      {item.topics.join(", ") || "Topics not linked"}
                    </small>
                  </div>
                  <span>{stamp(item.scheduled_at)}</span>
                </li>
              ))}
            </ul>
            {!items.length && <p>No upcoming assessments.</p>}
          </Card>
        )}
      </DataView>
      <DataView<Assignment[]> path="/assignments?pending_only=true">
        {(items) => (
          <Card title="Pending assignments">
            <ul className="rows">
              {items.map((item) => (
                <li key={item.id}>
                  <div>
                    <strong>{item.title}</strong>
                    <small>
                      {item.course_code} ·{" "}
                      {item.description || "No description"}
                    </small>
                  </div>
                  <span>{stamp(item.due_at)}</span>
                </li>
              ))}
            </ul>
            {!items.length && <p>No pending assignments.</p>}
          </Card>
        )}
      </DataView>
    </div>
  );
}
function PlanContent({ data }: { data: Dashboard }) {
  return (
    <>
      <p className="notice">
        {data.plan_source === "preview"
          ? "Planning preview — not saved. No database changes are made by this screen."
          : "Saved plan — displayed without modifying sessions."}
      </p>
      <ul className="rows">
        {data.today_plan.map((session, index) => (
          <li key={session.id ?? `${session.starts_at}-${index}`}>
            <div>
              <strong>{session.title}</strong>
              <small>
                {stamp(session.starts_at, data.timezone)} →{" "}
                {stamp(session.ends_at, data.timezone)}
              </small>
            </div>
            <span className="badge">
              {session.is_locked ? "Locked · " : ""}
              {session.status}
            </span>
          </li>
        ))}
      </ul>
      {!data.today_plan.length && (
        <p>
          No study sessions for today. Previews require declared free
          availability.
        </p>
      )}
      {Object.entries(data.unscheduled_minutes).map(([task, minutes]) => (
        <p key={task} className="muted">
          {task}: {minutes} minutes did not fit in today’s preview.
        </p>
      ))}
    </>
  );
}
function DashboardPage() {
  return (
    <DataView<Dashboard> path="/dashboard">
      {(data) => (
        <>
          <p className="muted">
            Snapshot {stamp(data.generated_at, data.timezone)} · {data.timezone}
          </p>
          <div className="grid">
            <Card title="Next class">
              {data.next_class ? (
                <>
                  <h3>
                    {data.next_class.course_name ||
                      data.next_class.session_kind}
                  </h3>
                  <p>{stamp(data.next_class.starts_at, data.timezone)}</p>
                  <p className="muted">
                    {data.next_class.location || "Location not recorded"}
                  </p>
                </>
              ) : (
                <p>No upcoming class in the next 14 days.</p>
              )}
            </Card>
            <Card title="Today’s study plan">
              <PlanContent data={data} />
            </Card>
            <Card title="Top priorities">
              <ul className="rows">
                {data.top_priorities.map((item) => (
                  <li key={item.task_key}>
                    <div>
                      <strong>{item.title}</strong>
                      <small>
                        {stamp(item.deadline_at, data.timezone)} ·{" "}
                        {item.required_minutes} estimated minutes
                      </small>
                      <small>
                        {item.estimate_source} · Preparation{" "}
                        {percent(item.preparation_percentage)}
                      </small>
                    </div>
                    <span className="badge">
                      {item.level} · {item.score.toFixed(0)}
                    </span>
                  </li>
                ))}
              </ul>
              {!data.top_priorities.length && (
                <p>No pending priorities in this snapshot.</p>
              )}
            </Card>
            <Card title="Risk signals">
              <p className="muted">
                Heuristic urgency scores, not probabilities.
              </p>
              <ul className="rows">
                {data.risks.map((risk, index) => (
                  <li key={`${risk.risk_type}-${index}`}>
                    <span>{risk.summary}</span>
                    <span className="badge">
                      {risk.severity} · {risk.score.toFixed(0)}
                    </span>
                  </li>
                ))}
              </ul>
              {!data.risks.length && (
                <p>No risk signals above the dashboard threshold.</p>
              )}
            </Card>
          </div>
          <Card title="Recent changes">
            <ul className="rows">
              {data.recent_changes.map((change) => (
                <li key={change.id}>
                  <span>
                    {change.entity_type} · {change.action}
                  </span>
                  <small>{stamp(change.created_at, data.timezone)}</small>
                </li>
              ))}
            </ul>
            {!data.recent_changes.length && <p>No recorded changes yet.</p>}
          </Card>
        </>
      )}
    </DataView>
  );
}
function AcademicsPage() {
  return (
    <>
      <div className="page-actions">
        <Link className="action-link" to="/academics/work">
          View assessments & assignments →
        </Link>
      </div>
      <DataView<Course[]> path="/courses">
        {(courses) => (
          <div className="grid">
            {courses.map((course) => (
              <Card key={course.id} title={course.code}>
                <h3>
                  <Link to={`/academics/${course.id}`}>{course.name}</Link>
                </h3>
                <p className="muted">
                  {course.kind} · {course.credits ?? "—"} credits
                </p>
                <p>Attendance: {percent(course.attendance_percentage)}</p>
                <p>Preparation: {percent(course.preparation_percentage)}</p>
                <Link to={`/academics/${course.id}`}>View syllabus →</Link>
              </Card>
            ))}
            {!courses.length && <p>No courses recorded.</p>}
          </div>
        )}
      </DataView>
    </>
  );
}
function CoursePage() {
  const { courseId } = useParams();
  if (!courseId || !/^\d+$/.test(courseId))
    return (
      <p>
        Invalid course. <Link to="/academics">Return to academics</Link>
      </p>
    );
  return (
    <DataView<CourseDetail> path={`/courses/${courseId}`}>
      {(course) => (
        <>
          <Link to="/academics">← All courses</Link>
          <h2>
            {course.code} · {course.name}
          </h2>
          <p>
            {course.faculty_name || "Faculty not recorded"} · Attendance{" "}
            {percent(course.attendance_percentage)} · Preparation{" "}
            {percent(course.preparation_percentage)}
          </p>
          <AttendanceInsight courseId={course.id} />
          <div className="section-heading">
            <h2>Syllabus and topic preparation</h2>
            <p className="muted">
              Adjust a topic, then save it to your semester record.
            </p>
          </div>
          <Units units={course.units} editable />
        </>
      )}
    </DataView>
  );
}
function PreparationPage() {
  return (
    <DataView<Preparation[]> path="/preparation">
      {(courses) => (
        <div className="stack">
          {courses.map((course) => (
            <Card key={course.course_id} title={course.course_name}>
              <p>{percent(course.completion_percentage)} prepared</p>
              <progress
                max={100}
                value={course.completion_percentage}
                aria-label={`${course.course_name} preparation`}
              />
              <p>
                <Link to={`/academics/${course.course_id}`}>
                  View topic-level progress →
                </Link>
              </p>
            </Card>
          ))}
          {!courses.length && <p>No preparation data recorded.</p>}
        </div>
      )}
    </DataView>
  );
}
function CalendarPage() {
  const days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];
  return (
    <DataView<Calendar> path="/calendar">
      {(data, refresh) => (
        <div className="stack">
          <CalendarForms onSaved={refresh} />
          <Card title="Weekly timetable">
            <p className="muted">
              Recurring class times are campus-local ({timezone}).
            </p>
            <ul className="rows">
              {[...data.timetable_entries]
                .sort(
                  (a, b) =>
                    a.day_of_week - b.day_of_week ||
                    a.start_time.localeCompare(b.start_time),
                )
                .map((entry) => (
                  <li key={entry.id}>
                    <div>
                      <strong>{entry.course_name || entry.session_kind}</strong>
                      <small>{entry.location || "Location not recorded"}</small>
                    </div>
                    <span>
                      {days[entry.day_of_week]} · {entry.start_time.slice(0, 5)}
                      –{entry.end_time.slice(0, 5)}
                    </span>
                  </li>
                ))}
            </ul>
            {!data.timetable_entries.length && (
              <p>No timetable entries recorded.</p>
            )}
          </Card>
          {(["academic_events", "personal_events"] as const).map((key) => (
            <Card
              key={key}
              title={
                key === "academic_events"
                  ? "Academic calendar"
                  : "Personal events"
              }
            >
              <ul className="rows">
                {data[key].map((event) => (
                  <li key={event.id}>
                    <div>
                      <strong>{event.title}</strong>
                      <small>{event.event_type}</small>
                    </div>
                    <span>
                      {stamp(event.starts_at)} → {stamp(event.ends_at)}
                    </span>
                  </li>
                ))}
              </ul>
              {!data[key].length && <p>No events recorded.</p>}
            </Card>
          ))}
        </div>
      )}
    </DataView>
  );
}
function CalendarForms({ onSaved }: { onSaved: () => void }) {
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function createEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setStatus(null);
    try {
      await send("/personal-events", "POST", {
        title: form.get("title"),
        event_type: form.get("event_type"),
        starts_at: new Date(String(form.get("starts_at"))).toISOString(),
        ends_at: new Date(String(form.get("ends_at"))).toISOString(),
        notes: form.get("notes") || null,
      });
      event.currentTarget.reset();
      setStatus("Personal event added.");
      onSaved();
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Could not add the event.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function createAvailability(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setStatus(null);
    try {
      await send("/availability", "POST", {
        block_type: form.get("block_type"),
        block_date: form.get("block_date") || null,
        start_time: form.get("start_time"),
        end_time: form.get("end_time"),
        is_recurring: false,
        label: form.get("label") || null,
      });
      event.currentTarget.reset();
      setStatus("Availability block added.");
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Could not add availability.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="grid">
      <Card title="Add personal event">
        <form className="form-grid" onSubmit={createEvent}>
          <label>
            Title
            <input name="title" required maxLength={180} />
          </label>
          <label>
            Type
            <select name="event_type" defaultValue="PERSONAL">
              <option>PERSONAL</option>
              <option>FIXED</option>
              <option>TRAVEL</option>
              <option>HEALTH</option>
              <option>OTHER</option>
            </select>
          </label>
          <label>
            Starts
            <input name="starts_at" type="datetime-local" required />
          </label>
          <label>
            Ends
            <input name="ends_at" type="datetime-local" required />
          </label>
          <label className="full">
            Notes
            <textarea name="notes" rows={2} />
          </label>
          <button disabled={busy}>{busy ? "Saving…" : "Add event"}</button>
        </form>
      </Card>
      <Card title="Declare availability">
        <form className="form-grid" onSubmit={createAvailability}>
          <label>
            Kind
            <select name="block_type" defaultValue="AVAILABLE">
              <option>AVAILABLE</option>
              <option>UNAVAILABLE</option>
              <option>LOCKED</option>
            </select>
          </label>
          <label>
            Date
            <input name="block_date" type="date" required />
          </label>
          <label>
            Starts
            <input name="start_time" type="time" required />
          </label>
          <label>
            Ends
            <input name="end_time" type="time" required />
          </label>
          <label className="full">
            Label
            <input
              name="label"
              maxLength={120}
              placeholder="e.g. Library study time"
            />
          </label>
          <button disabled={busy}>{busy ? "Saving…" : "Add block"}</button>
        </form>
      </Card>
      {status && (
        <p
          className={
            status.endsWith("added.")
              ? "success form-status"
              : "form-error form-status"
          }
        >
          {status}
        </p>
      )}
    </div>
  );
}
function Placeholder({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card title={title}>
      <p>{description}</p>
      <p className="muted">
        Page foundation only. No simulated content or AI requests.
      </p>
    </Card>
  );
}

export default function App() {
  return (
    <div className="shell">
      <aside>
        <Link to="/" className="brand">
          CampusPulse<span>YOUR SEMESTER, IN FOCUS</span>
        </Link>
        <nav aria-label="Main navigation">
          {pages.map(([path, label]) => (
            <NavLink key={path} to={path} end={path === "/"}>
              {label}
            </NavLink>
          ))}
        </nav>
        <p className="sidebar-note">
          Phase 8 · Academic workspace
          <br />
          Synthetic student #1
          <br />
          Local development
        </p>
      </aside>
      <main>
        <header>
          <p className="eyebrow">SEMESTER 5 / WORKSPACE</p>
          <h1>Your academic pulse</h1>
          <p className="muted">
            Your CampusPulse academic workspace. One clear view of what’s next.
          </p>
        </header>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/academics" element={<AcademicsPage />} />
          <Route path="/academics/work" element={<AcademicWork />} />
          <Route path="/academics/:courseId" element={<CoursePage />} />
          <Route path="/preparation" element={<PreparationPage />} />
          <Route
            path="/plan"
            element={
              <DataView<Dashboard> path="/dashboard">
                {(data) => (
                  <Card title="Today’s plan">
                    <PlanContent data={data} />
                  </Card>
                )}
              </DataView>
            }
          />
          <Route
            path="/announcements"
            element={
              <Placeholder
                title="Announcements"
                description="Announcement ingestion and its API/UI workflow will be connected in later phases."
              />
            }
          />
          <Route
            path="/ai"
            element={
              <Placeholder
                title="CampusPulse AI"
                description="Agent tools, LangGraph, and LLM integration are intentionally not enabled yet."
              />
            }
          />
          <Route
            path="*"
            element={
              <Card title="Page not found">
                <Link to="/">Return to dashboard</Link>
              </Card>
            }
          />
        </Routes>
        <footer>
          CampusPulse · Foundation build · No frontend calculations replace
          backend decisions.
        </footer>
      </main>
    </div>
  );
}
