export interface Topic {
  id: number;
  title: string;
  completion_percentage: number;
}
export interface Unit {
  id: number;
  sequence: number;
  title: string;
  topics: Topic[];
}
export interface Course {
  id: number;
  code: string;
  name: string;
  kind: string;
  credits: number | null;
  faculty_name: string | null;
  attendance_percentage: number | null;
  preparation_percentage: number;
}
export interface CourseDetail extends Course {
  units: Unit[];
}
export interface Preparation {
  course_id: number;
  course_code: string;
  course_name: string;
  completion_percentage: number;
  units: Unit[];
}
export interface CalendarEvent {
  id: number;
  title: string;
  event_type: string;
  starts_at: string;
  ends_at: string;
}
export interface Calendar {
  academic_events: CalendarEvent[];
  personal_events: CalendarEvent[];
  availability_blocks: Availability[];
  timetable_entries: {
    id: number;
    course_name: string | null;
    title: string | null;
    day_of_week: number;
    start_time: string;
    end_time: string;
    location: string | null;
    session_kind: string;
  }[];
}
export interface Attendance {
  course_id: number;
  course_code: string;
  course_name: string;
  attended_classes: number;
  conducted_classes: number;
  target_percentage: number;
  attendance_percentage: number;
}
export interface AttendanceImpact extends Attendance {
  if_next_attended_percentage: number;
  if_next_missed_percentage: number;
  safe_skips: number;
  recovery_classes: number | null;
}
export interface Assessment {
  id: number;
  course_id: number;
  course_code: string;
  course_name: string;
  title: string;
  assessment_type: string;
  status: string;
  scheduled_at: string | null;
  maximum_marks: number | null;
  earned_marks: number | null;
  weightage: number | null;
  topics: string[];
}
export interface Assignment {
  id: number;
  course_id: number;
  course_code: string;
  course_name: string;
  title: string;
  description: string | null;
  due_at: string | null;
  submitted_at: string | null;
  maximum_marks: number | null;
  earned_marks: number | null;
  is_submitted: boolean;
}
export interface Availability {
  id: number;
  student_id: number;
  block_type: "AVAILABLE" | "UNAVAILABLE" | "LOCKED";
  block_date: string | null;
  day_of_week: number | null;
  start_time: string;
  end_time: string;
  is_recurring: boolean;
  label: string | null;
}
export interface Dashboard {
  student_id: number;
  generated_at: string;
  timezone: string;
  next_class: {
    course_name: string | null;
    starts_at: string;
    ends_at: string;
    location: string | null;
    session_kind: string;
  } | null;
  today_plan: {
    id: number | null;
    title: string;
    starts_at: string;
    ends_at: string;
    status: string;
    is_locked: boolean;
    source: "saved" | "preview";
    management_kind: "study_session" | "availability_block" | "preview";
  }[];
  plan_source: "saved" | "preview";
  top_priorities: {
    task_key: string;
    title: string;
    deadline_at: string | null;
    score: number;
    level: string;
    required_minutes: number;
    estimate_source: string;
    preparation_percentage: number | null;
    factors: {
      deadline_urgency: number;
      assessment_importance: number;
      preparation_gap: number;
      performance_gap: number;
      attendance_risk: number;
      workload_risk: number;
      conflict_risk: number;
    };
  }[];
  risks: {
    risk_type: string;
    summary: string;
    severity: string;
    score: number;
  }[];
  recent_changes: {
    id: number;
    entity_type: string;
    action: string;
    created_at: string;
  }[];
  unscheduled_minutes: Record<string, number>;
}

export interface IngestionItem {
  id: number;
  source: "PASTE" | "PDF" | "GMAIL";
  filename: string | null;
  raw_text: string;
  normalized_text: string;
  extraction: {
    title?: string;
    event_type?: string;
    course_name?: string | null;
    scheduled_at?: string | null;
    topics?: string[];
    summary?: string;
    confidence?: number;
    course_match?: string | null;
    requires_review?: boolean;
  } | null;
  course_id: number | null;
  course_code: string | null;
  status: "PREVIEW" | "APPLIED" | "IGNORED" | "FAILED";
  error: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface IngestionApplyResult {
  item: IngestionItem;
  announcement_id: number;
  created_record_type: string | null;
  created_record_id: number | null;
  replan_required: boolean;
  dashboard_recalculated: boolean;
}

export interface AgentResponse {
  answer: string;
  tools_used: string[];
  model: string;
}
export interface Change {
  id: number;
  title: string;
  reason: string;
  entity_type: string;
  entity_id: string;
  action: string;
  changes: { field: string; before: unknown | null; after: unknown | null }[];
  created_at: string;
}
