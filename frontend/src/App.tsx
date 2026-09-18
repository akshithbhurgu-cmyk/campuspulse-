import { useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from "react";
import { Link, NavLink, Route, Routes, useParams } from "react-router-dom";
import { send, useApi } from "./api";
import type {
  Assignment,
  AgentResponse,
  Assessment,
  AttendanceImpact,
  Calendar,
  Change,
  Course,
  CourseDetail,
  Dashboard,
  IngestionApplyResult,
  IngestionItem,
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
const localDateTimeValue = (value: string) => {
  const date = new Date(value);
  const part = (number: number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${part(date.getMonth() + 1)}-${part(date.getDate())}T${part(date.getHours())}:${part(date.getMinutes())}`;
};
const percent = (value: number | null) =>
  value === null ? "Not recorded" : `${value.toFixed(1)}%`;
const pages = [
  ["/", "◈  Dashboard"],
  ["/calendar", "▣  Calendar"],
  ["/academics", "▤  Academics"],
  ["/preparation", "◒  Preparation"],
  ["/announcements", "✦  Announcements"],
  ["/updates", "◌  Updates"],
  ["/plan", "⌁  Plan"],
  ["/ai", "✧  CampusPulse AI"],
];

function Card({
  title,
  children,
  className = "",
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}
function DataView<T>({
  path,
  children,
  refreshOnMutation = false,
}: {
  path: string;
  children: (data: T, refresh: () => void) => ReactNode;
  refreshOnMutation?: boolean;
}) {
  const { data, loading, error, retry } = useApi<T>(path, refreshOnMutation);
  if (loading)
    return (
      <div className="card loading-card" role="status">
        <span className="skeleton skeleton-title" />
        <span className="skeleton" />
        <span className="skeleton skeleton-short" />
        <span className="sr-only">Loading your semester…</span>
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
function PlanContent({
  data,
  refresh,
}: {
  data: Dashboard;
  refresh?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editStartsAt, setEditStartsAt] = useState("");
  const [editEndsAt, setEditEndsAt] = useState("");
  async function save() {
    setBusy(true);
    try {
      await send("/plans/today/save", "POST", null);
      setMessage("Plan saved.");
      refresh?.();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not save plan.");
    } finally {
      setBusy(false);
    }
  }
  async function toggle(id: number, locked: boolean) {
    setBusy(true);
    setMessage(null);
    try {
      await send(`/study-sessions/${id}/lock?locked=${!locked}`, "POST", null);
      refresh?.();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update this session.");
    } finally {
      setBusy(false);
    }
  }
  async function remove(session: Dashboard["today_plan"][number]) {
    if (!session.id) return;
    const protectedBlock = session.management_kind === "availability_block";
    const prompt = protectedBlock
      ? `Remove the protected block “${session.title}”? This will make that time available to planning again.`
      : `Remove “${session.title}” from today’s study plan?`;
    if (!window.confirm(prompt)) return;
    setBusy(true);
    setMessage(null);
    try {
      await send(
        protectedBlock ? `/availability/${session.id}` : `/study-sessions/${session.id}`,
        "DELETE",
        null,
      );
      if (editingId === session.id) setEditingId(null);
      setMessage(protectedBlock ? "Protected availability block removed." : "Study session removed from today’s plan.");
      refresh?.();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not remove this session.");
    } finally {
      setBusy(false);
    }
  }
  function beginEdit(session: Dashboard["today_plan"][number]) {
    if (!session.id) return;
    setEditingId(session.id);
    setEditTitle(session.title);
    setEditStartsAt(localDateTimeValue(session.starts_at));
    setEditEndsAt(localDateTimeValue(session.ends_at));
    setMessage(null);
  }
  async function saveEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingId) return;
    setBusy(true);
    setMessage(null);
    try {
      await send(`/study-sessions/${editingId}`, "PATCH", {
        title: editTitle,
        starts_at: new Date(editStartsAt).toISOString(),
        ends_at: new Date(editEndsAt).toISOString(),
      });
      setEditingId(null);
      setMessage("Study session updated.");
      refresh?.();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update this session.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="plan-overview">
        <div>
          <span className={`plan-source ${data.plan_source}`}>
            {data.plan_source === "preview" ? "Draft plan" : "Saved plan"}
          </span>
          <p>
            {data.today_plan.length
              ? `${data.today_plan.length} block${data.today_plan.length === 1 ? "" : "s"} scheduled for today`
              : "Your day is currently open"}
          </p>
        </div>
        {data.plan_source === "saved" && (
          <span className="plan-overview-hint">Edit or lock a session below</span>
        )}
      </div>
      {data.plan_source === "preview" && (
        <p className="notice">
          This is a planning preview. Save it when the suggested time blocks look right.
        </p>
      )}
      <ul className="plan-sessions">
        {data.today_plan.map((session, index) => (
          <li className="plan-session" key={session.id ?? `${session.starts_at}-${index}`}>
            <div className="plan-session-time">
              <strong>{new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit", timeZone: data.timezone }).format(new Date(session.starts_at))}</strong>
              <span>{new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit", timeZone: data.timezone }).format(new Date(session.ends_at))}</span>
            </div>
            <div className="plan-session-main">
              <strong>{session.title}</strong>
              <small>
                {session.is_locked
                  ? "Protected time — CampusPulse will not move it automatically."
                  : session.source === "preview"
                    ? "Suggested from your priorities and available time."
                    : "Scheduled study session."}
              </small>
            </div>
            <div className="plan-session-actions">
              <span className={`plan-status ${session.is_locked ? "locked" : ""}`}>
                {session.is_locked ? "Locked" : session.status}
              </span>
              {session.id && session.management_kind === "study_session" && data.plan_source === "saved" && (
                <>
                  <button
                    className="small-button"
                    disabled={busy}
                    onClick={() => toggle(session.id!, session.is_locked)}
                  >
                    {session.is_locked ? "Unlock" : "Lock time"}
                  </button>
                  <button
                    className="small-button secondary-button"
                    disabled={busy}
                    onClick={() => beginEdit(session)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="small-button danger-button"
                    disabled={busy}
                    onClick={() => remove(session)}
                  >
                    Delete
                  </button>
                </>
              )}
              {session.id && session.management_kind === "availability_block" && (
                <button
                  type="button"
                  className="small-button danger-button"
                  disabled={busy}
                  onClick={() => remove(session)}
                >
                  Remove block
                </button>
              )}
            </div>
            {editingId === session.id && (
              <div className="plan-editor">
                <form className="plan-editor-form" onSubmit={saveEdit}>
                  <label className="plan-editor-task">
                    Task
                    <input value={editTitle} onChange={(event) => setEditTitle(event.target.value)} required maxLength={180} />
                  </label>
                  <label>
                    Starts
                    <input value={editStartsAt} onChange={(event) => setEditStartsAt(event.target.value)} required type="datetime-local" />
                  </label>
                  <label>
                    Ends
                    <input value={editEndsAt} onChange={(event) => setEditEndsAt(event.target.value)} required type="datetime-local" />
                  </label>
                  <div className="plan-editor-actions">
                    <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save changes"}</button>
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={busy}
                      onClick={() => {
                        setEditingId(null);
                        setMessage(null);
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            )}
          </li>
        ))}
      </ul>
      {data.plan_source === "preview" && data.today_plan.length > 0 && (
        <button className="plan-save-button" disabled={busy} onClick={save}>
          {busy ? "Saving…" : "Save today’s plan"}
        </button>
      )}
      {message && <p className="success">{message}</p>}
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
function ReplanPanel({ refresh }: { refresh: () => void }) {
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [preview, setPreview] = useState<{
    kept_session_ids: number[];
    rescheduled: { session_id: number; starts_at: string; ends_at: string }[];
    locked_conflict_ids: number[];
    unresolved_session_ids: number[];
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  async function previewReplan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const result = await send<typeof preview>(
        `/plans/replan/preview?starts_at=${encodeURIComponent(new Date(startsAt).toISOString())}&ends_at=${encodeURIComponent(new Date(endsAt).toISOString())}`,
        "POST",
        null,
      );
      setPreview(result);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not create a replan preview.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function confirm() {
    if (!preview) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await send<{ moved_sessions: number }>(
        "/plans/replan/confirm",
        "POST",
        preview.rescheduled,
      );
      setMessage(
        `Replan confirmed. ${result.moved_sessions} session${result.moved_sessions === 1 ? "" : "s"} moved.`,
      );
      setPreview(null);
      refresh();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Could not confirm replan.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card title="Replan saved sessions">
      <p className="muted">
        Enter a new unavoidable time block. CampusPulse previews changes first;
        locked sessions are never moved.
      </p>
      <form className="form-grid" onSubmit={previewReplan}>
        <label>
          Starts
          <input
            required
            type="datetime-local"
            value={startsAt}
            onChange={(e) => setStartsAt(e.target.value)}
          />
        </label>
        <label>
          Ends
          <input
            required
            type="datetime-local"
            value={endsAt}
            onChange={(e) => setEndsAt(e.target.value)}
          />
        </label>
        <button disabled={busy}>
          {busy ? "Calculating…" : "Preview replan"}
        </button>
      </form>
      {preview && (
        <div className="replan-preview">
          <p>
            <strong>{preview.kept_session_ids.length}</strong> session(s)
            unchanged · <strong>{preview.rescheduled.length}</strong> proposed
            move(s)
          </p>
          {!!preview.locked_conflict_ids.length && (
            <p className="form-error">
              Locked conflicts: sessions{" "}
              {preview.locked_conflict_ids.join(", ")}. They were kept
              unchanged.
            </p>
          )}
          {!!preview.unresolved_session_ids.length && (
            <p className="form-error">
              Could not fit sessions:{" "}
              {preview.unresolved_session_ids.join(", ")}.
            </p>
          )}
          <ul className="rows">
            {preview.rescheduled.map((item) => (
              <li key={item.session_id}>
                <span>Session #{item.session_id}</span>
                <span>
                  {stamp(item.starts_at)} → {stamp(item.ends_at)}
                </span>
              </li>
            ))}
          </ul>
          <div className="review-actions">
            <button
              disabled={busy || !!preview.locked_conflict_ids.length}
              onClick={confirm}
            >
              Confirm replan
            </button>
            <button
              className="secondary-button"
              disabled={busy}
              onClick={() => setPreview(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      {message && (
        <p className={message.startsWith("Replan") ? "success" : "form-error"}>
          {message}
        </p>
      )}
    </Card>
  );
}
function UpdatesPage() {
  return (
    <DataView<Change[]> path="/changes">
      {(changes) => (
        <Card title="Updates and notifications">
          <p className="muted">
            A transparent timeline explaining every academic update and plan
            change.
          </p>
          {!changes.length && <p>No updates yet.</p>}
          <div className="change-timeline">
            {changes.map((change) => (
              <article key={change.id} className="change-item">
                <div className="change-dot" />
                <div>
                  <div className="change-title">
                    <h3>{change.title}</h3>
                    <small>{stamp(change.created_at)}</small>
                  </div>
                  <p>{change.reason}</p>
                </div>
              </article>
            ))}
          </div>
        </Card>
      )}
    </DataView>
  );
}
function DashboardPage() {
  return (
    <DataView<Dashboard> path="/dashboard" refreshOnMutation>
      {(data, refresh) => (
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
            <Card title="Today’s study plan" className="plan-card">
              <PlanContent data={data} refresh={refresh} />
            </Card>
            <Card title="Top priorities">
              <ul className="priority-list">
                {data.top_priorities.map((item) => (
                  <li className="priority-item" key={item.task_key}>
                    <div className="priority-item-main">
                      <strong>{item.title}</strong>
                      <small>
                        {stamp(item.deadline_at, data.timezone)} ·{" "}
                        {item.required_minutes} estimated minutes
                      </small>
                      <small>
                        {item.estimate_source} · Preparation{" "}
                        {percent(item.preparation_percentage)}
                      </small>
                      <div className="factor-strip">
                        <span>Prep gap {item.factors.preparation_gap.toFixed(0)}</span>
                        <span>Deadline {item.factors.deadline_urgency.toFixed(0)}</span>
                        <span>Workload {item.factors.workload_risk.toFixed(0)}</span>
                      </div>
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
              <ul className="risk-list">
                {data.risks.map((risk, index) => (
                  <li className="risk-item" key={`${risk.risk_type}-${index}`}>
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
      {(data, refresh) => {
        const todayName = new Intl.DateTimeFormat("en-US", { weekday: "long", timeZone: timezone }).format(new Date());
        const todayIndex = days.indexOf(todayName);
        const todayLabel = new Intl.DateTimeFormat("en-IN", { dateStyle: "full", timeZone: timezone }).format(new Date());
        const todayEntries = [...data.timetable_entries]
          .filter((entry) => entry.day_of_week === todayIndex)
          .sort((a, b) => a.start_time.localeCompare(b.start_time));
        return (
          <div className="stack">
          <CalendarForms onSaved={refresh} />
          <Card title={`Today's timetable · ${todayLabel}`}>
            <p className="muted">
              Live view for the current campus day ({timezone}).
            </p>
            <ul className="rows">
              {todayEntries.map((entry) => (
                  <li key={entry.id}>
                    <div>
                      <strong>{entry.course_name || entry.session_kind}</strong>
                      <small>{entry.location || "Location not recorded"}</small>
                    </div>
                    <span>
                      {entry.start_time.slice(0, 5)}
                      –{entry.end_time.slice(0, 5)}
                    </span>
                  </li>
                ))}
            </ul>
            {!todayEntries.length && (
              <p>No scheduled classes today.</p>
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
          <Card title="Availability blocks">
            <p className="muted">
              Time protected from, or reserved for, study planning.
            </p>
            <ul className="rows">
              {data.availability_blocks.map((block) => (
                <li key={block.id}>
                  <div>
                    <strong>{block.label || "Unnamed availability block"}</strong>
                    <small>{block.block_type}</small>
                  </div>
                  <span>
                    {block.is_recurring && block.day_of_week !== null
                      ? `Every ${days[block.day_of_week]}`
                      : block.block_date || "Date not recorded"}
                    {" · "}
                    {block.start_time.slice(0, 5)}–{block.end_time.slice(0, 5)}
                  </span>
                </li>
              ))}
            </ul>
            {!data.availability_blocks.length && (
              <p>No availability blocks recorded.</p>
            )}
          </Card>
          </div>
        );
      }}
    </DataView>
  );
}
function CalendarForms({ onSaved }: { onSaved: () => void }) {
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function createEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // `currentTarget` is cleared after an awaited browser event handler.
    // Keep the form element before starting the asynchronous request.
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
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
      formElement.reset();
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
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
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
      formElement.reset();
      setStatus("Availability block added.");
      onSaved();
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

function ReviewItem({
  item,
  onChanged,
}: {
  item: IngestionItem;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState<"apply" | "ignore" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const extraction = item.extraction;
  const showConfidence =
    extraction?.event_type !== "ANNOUNCEMENT" &&
    typeof extraction?.confidence === "number";

  async function act(action: "apply" | "ignore") {
    setBusy(action);
    setMessage(null);
    try {
      if (action === "apply") {
        const result = await send<IngestionApplyResult>(
          `/ingestion/${item.id}/apply`,
          "POST",
          null,
        );
        setMessage(
          result.created_record_type
            ? `Applied. Created ${result.created_record_type.replaceAll("_", " ").toLowerCase()}.${result.replan_required ? " Your dashboard priorities have been recalculated; a replan preview is required before any saved study session can move." : ""}`
            : "Applied as an announcement. The original email remains available in Gmail.",
        );
      } else {
        await send<IngestionItem>(`/ingestion/${item.id}/ignore`, "POST", null);
        setMessage("Ignored. No academic record was created.");
      }
      onChanged();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not update this preview.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="review-item">
      <div className="review-heading">
        <div>
          <p className="eyebrow">{item.source} · REVIEW REQUIRED</p>
          <h3>{extraction?.title || "Untitled item"}</h3>
        </div>
        <span className="badge">
          {extraction?.event_type || "UNCLASSIFIED"}
        </span>
      </div>
      <dl className="review-details">
        <div>
          <dt>Course</dt>
          <dd>
            {item.course_code ||
              extraction?.course_name ||
              "Not confidently matched"}
          </dd>
        </div>
        <div>
          <dt>Scheduled</dt>
          <dd>{stamp(extraction?.scheduled_at || null)}</dd>
        </div>
        {showConfidence && (
          <div>
            <dt>Confidence</dt>
            <dd>{`${Math.round(extraction.confidence! * 100)}%`}</dd>
          </div>
        )}
      </dl>
      {extraction?.summary && <p>{extraction.summary}</p>}
      {!!extraction?.topics?.length && (
        <p className="muted">Topics: {extraction.topics.join(", ")}</p>
      )}
      <details>
        <summary>View original imported text</summary>
        <pre>{item.normalized_text}</pre>
      </details>
      <div className="review-actions">
        <button
          type="button"
          onClick={() => act("apply")}
          disabled={busy !== null}
        >
          {busy === "apply" ? "Applying…" : "Apply"}
        </button>
        <button
          type="button"
          className="secondary-button"
          onClick={() => act("ignore")}
          disabled={busy !== null}
        >
          {busy === "ignore" ? "Ignoring…" : "Ignore"}
        </button>
      </div>
      {message && (
        <p className={message.startsWith("Could") ? "form-error" : "success"}>
          {message}
        </p>
      )}
    </article>
  );
}

function ReviewInboxPage() {
  const { data, loading, error, retry } = useApi<IngestionItem[]>(
    "/ingestion?status=PREVIEW",
  );
  const [gmailQuery, setGmailQuery] = useState("");
  const [gmailMaxResults, setGmailMaxResults] = useState(10);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);

  async function importGmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setImporting(true);
    setImportMessage(null);
    try {
      const path = `/ingestion/gmail/import?max_results=${gmailMaxResults}&query=${encodeURIComponent(gmailQuery)}`;
      const imported = await send<IngestionItem[]>(path, "POST", null);
      setImportMessage(
        `${imported.length} Gmail message${imported.length === 1 ? "" : "s"} checked. New items are review-only.`,
      );
      retry();
    } catch (error) {
      setImportMessage(
        error instanceof Error
          ? error.message
          : "Gmail import could not start.",
      );
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="stack">
      <Card title="Import from Gmail">
        <p className="muted">
          CampusPulse reads only the search results you request. Imported
          messages are previews; they never update your semester until you press
          Apply.
        </p>
        <form className="inline-form" onSubmit={importGmail}>
          <label>
            Gmail search (optional)
            <input
              value={gmailQuery}
              onChange={(event) => setGmailQuery(event.target.value)}
              placeholder="e.g. from:faculty@college.edu newer_than:30d"
            />
          </label>
          <label>
            Messages
            <select
              value={gmailMaxResults}
              onChange={(event) => setGmailMaxResults(Number(event.target.value))}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={30}>30</option>
            </select>
          </label>
          <button disabled={importing}>
            {importing ? "Reading Gmail…" : "Check Gmail"}
          </button>
        </form>
        {importMessage && (
          <p
            className={
              importMessage.includes("could") ? "form-error" : "success"
            }
          >
            {importMessage}
          </p>
        )}
      </Card>
      <section className="section-heading">
        <h2>Items awaiting your decision</h2>
        <p className="muted">
          Review the extraction against the original text. Apply currently
          records a reviewed announcement; Ignore creates no academic record.
        </p>
      </section>
      {loading && (
        <div className="card" role="status">
          Loading review items…
        </div>
      )}
      {error && (
        <div className="card" role="alert">
          <p>{error}</p>
          <button onClick={retry}>Try again</button>
        </div>
      )}
      {data?.map((item) => (
        <ReviewItem key={item.id} item={item} onChanged={retry} />
      ))}
      {data && !data.length && (
        <Card title="Inbox clear">
          <p>No imported items need review right now.</p>
        </Card>
      )}
    </div>
  );
}

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  tools?: string[];
  model?: string;
};

const starterQuestions = [
  "What should I study tonight?",
  "Can I skip my next FOS class?",
  "How prepared am I for Deep Learning?",
  "What are my biggest academic risks?",
];

const initialChatMessages: ChatMessage[] = [
    {
      id: 0,
      role: "assistant",
      text: "Ask me about your attendance, assessments, preparation, risks, priorities, or study schedule. I use your CampusPulse data and deterministic backend tools to answer.",
    },
  ];

function AiChatPage({
  messages,
  setMessages,
  busy,
  setBusy,
}: {
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  busy: boolean;
  setBusy: Dispatch<SetStateAction<boolean>>;
}) {
  const [question, setQuestion] = useState("");

  async function ask(rawQuestion?: string) {
    const text = (rawQuestion ?? question).trim();
    if (!text || busy) return;
    const requestId = Date.now();
    setMessages((current) => [
      ...current,
      { id: requestId, role: "user", text },
    ]);
    setQuestion("");
    setBusy(true);
    try {
      const result = await send<AgentResponse>("/agent/query", "POST", {
        question: text,
      });
      setMessages((current) => [
        ...current,
        {
          id: requestId + 1,
          role: "assistant",
          text: result.answer,
          tools: result.tools_used,
          model: result.model,
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: requestId + 1,
          role: "assistant",
          text:
            error instanceof Error
              ? `I could not answer that: ${error.message}`
              : "I could not answer that right now.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask();
  }

  return (
    <div className="chat-layout">
      <Card title="CampusPulse AI">
        <p className="notice">
          The AI explains real CampusPulse data. Attendance, risks, priorities,
          and plans are calculated by backend engines—not invented by the model.
        </p>
        <div className="chat-messages" aria-live="polite">
          {messages.map((message) => (
            <article
              key={message.id}
              className={`chat-message ${message.role}`}
            >
              <strong>{message.role === "user" ? "You" : "CampusPulse"}</strong>
              <p>{message.text}</p>
              {message.role === "assistant" && message.tools && (
                <small>
                  Tools used:{" "}
                  {message.tools.length
                    ? message.tools.join(", ")
                    : "No backend tool was needed"}
                  {message.model ? ` · ${message.model}` : ""}
                </small>
              )}
            </article>
          ))}
          {busy && (
            <article className="chat-message assistant">
              <strong>CampusPulse</strong>
              <p>Checking your academic context…</p>
            </article>
          )}
        </div>
        <form className="chat-form" onSubmit={submit}>
          <label htmlFor="agent-question" className="sr-only">
            Ask CampusPulse AI
          </label>
          <textarea
            id="agent-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                event.preventDefault();
                void ask();
              }
            }}
            maxLength={2000}
            rows={3}
            placeholder="Ask about your semester…"
            disabled={busy}
          />
          <button disabled={busy || !question.trim()}>
            {busy ? "Thinking…" : "Ask CampusPulse"}
          </button>
        </form>
      </Card>
      <Card title="Try a question">
        <div className="suggestions">
          {starterQuestions.map((item) => (
            <button
              key={item}
              type="button"
              className="secondary-button"
              onClick={() => void ask(item)}
              disabled={busy}
            >
              {item}
            </button>
          ))}
        </div>
        <p className="muted">
          This chat is read-only. It cannot apply inbox items, modify
          attendance, or create a plan without a separate confirmed action.
        </p>
      </Card>
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
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(initialChatMessages);
  const [chatBusy, setChatBusy] = useState(false);
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
          <span className="live-dot" /> Local workspace
          <br />
          Synthetic student #1
          <br />
          Local development
        </p>
      </aside>
      <main>
        <header>
          <p className="eyebrow">SEMESTER 5 / WORKSPACE</p>
          <div className="header-line">
            <h1>Your academic pulse</h1>
            <span className="status-chip">
              <span className="live-dot" /> Systems ready
            </span>
          </div>
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
                {(data, refresh) => (
                  <div className="stack">
                    <Card title="Today’s plan" className="plan-card plan-page-card">
                      <PlanContent data={data} refresh={refresh} />
                    </Card>
                    {data.plan_source === "saved" && (
                      <ReplanPanel refresh={refresh} />
                    )}
                  </div>
                )}
              </DataView>
            }
          />
          <Route path="/announcements" element={<ReviewInboxPage />} />
          <Route path="/updates" element={<UpdatesPage />} />
          <Route
            path="/ai"
            element={
              <AiChatPage
                messages={chatMessages}
                setMessages={setChatMessages}
                busy={chatBusy}
                setBusy={setChatBusy}
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
