/**
 * Shared TypeScript types for PermitAI LA.
 * These mirror the Python enums in backend/app/schemas/common.py.
 * Used by both dashboard (Next.js) and mobile (React Native).
 */

// ── Project ──────────────────────────────────────────────────────────────────

export type ProjectPathway = "eo1_like_for_like" | "eo8_expanded" | "standard";

export type ProjectStatus =
  | "intake"
  | "in_review"
  | "approved"
  | "issued"
  | "inspection"
  | "final"
  | "closed";

export interface Project {
  id: string;
  address: string;
  apn: string | null;
  owner_id: string;
  pathway: ProjectPathway | null;
  status: ProjectStatus;
  original_sqft: number | null;
  proposed_sqft: number | null;
  stories: number | null;
  is_coastal_zone: boolean;
  is_hillside: boolean;
  is_very_high_fire_severity: boolean;
  is_historic: boolean;
  is_flood_zone: boolean;
  ai_pathway_confidence: number | null;
  ai_reasoning: string | null;
  predicted_total_days: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  clearances: Clearance[];
  inspections: Inspection[];
  documents: Document[];
}

// ── Clearance ────────────────────────────────────────────────────────────────

export type ClearanceDepartment =
  | "ladbs"
  | "dcp"
  | "boe"
  | "lafd"
  | "ladwp"
  | "lasan"
  | "lahd"
  | "dot"
  | "cultural_affairs"
  | "urban_forestry";

export type ClearanceStatus =
  | "not_started"
  | "in_review"
  | "approved"
  | "conditional"
  | "denied";

export interface Clearance {
  id: string;
  project_id: string;
  department: ClearanceDepartment;
  clearance_type: string;
  status: ClearanceStatus;
  is_bottleneck: boolean;
  predicted_days: number | null;
  submitted_date: string | null;
  completed_date: string | null;
  conflict_with_id: string | null;
  conflict_description: string | null;
  created_at: string;
  updated_at: string;
}

// ── Inspection ───────────────────────────────────────────────────────────────

export type InspectionStatus = "scheduled" | "passed" | "failed" | "cancelled";

export interface Inspection {
  id: string;
  project_id: string;
  inspection_type: string;
  status: InspectionStatus;
  scheduled_date: string | null;
  completed_date: string | null;
  inspector_name: string | null;
  failure_reasons: string[];
  notes: string | null;
  created_at: string;
}

// ── Document ─────────────────────────────────────────────────────────────────

export type DocumentType =
  | "plans"
  | "permit_application"
  | "insurance"
  | "photos"
  | "soils_report"
  | "structural_calc"
  | "title_report"
  | "other";

export interface Document {
  id: string;
  project_id: string;
  s3_key: string;
  filename: string;
  document_type: DocumentType;
  file_size_bytes: number | null;
  uploaded_by: string | null;
  created_at: string;
}

// ── User ─────────────────────────────────────────────────────────────────────

export type UserRole = "homeowner" | "contractor" | "architect" | "staff" | "admin";
export type Language = "en" | "es" | "ko" | "zh" | "tl";

export interface User {
  id: string;
  angeleno_id: string | null;
  email: string;
  full_name: string | null;
  role: UserRole;
  language: Language;
  phone: string | null;
  notification_push: boolean;
  notification_sms: boolean;
  notification_email: boolean;
}

// ── Pathfinder ───────────────────────────────────────────────────────────────

export interface PathfinderResult {
  pathway: ProjectPathway;
  confidence: number;
  reasoning: string;
  required_clearances: string[];
  estimated_days: number;
  standard_plans: StandardPlan[];
  conflicts: ConflictResult[];
  timeline: TimelineResult;
}

export interface StandardPlan {
  plan_id: string;
  name: string;
  compatibility_score: number;
  plan_check_days_saved: number;
  max_sqft: number;
  max_stories: number;
}

export interface ConflictResult {
  id: string;
  dept_a: string;
  dept_b: string;
  description: string;
  severity: "low" | "medium" | "high";
  resolution: string;
}

export interface TimelineResult {
  total_predicted_days: number;
  critical_path_days: number;
  critical_department: string | null;
  bottleneck_count: number;
  bottlenecks: TimelineBottleneck[];
  clearance_predictions: ClearancePrediction[];
}

export interface TimelineBottleneck {
  department: string;
  clearance_type: string;
  predicted_days: number;
  reason: string;
}

export interface ClearancePrediction {
  department: string;
  clearance_type: string;
  predicted_days: number;
  confidence: number;
  is_bottleneck: boolean;
}

// ── Analytics ────────────────────────────────────────────────────────────────

export interface PipelineMetrics {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  avg_days_to_issue: number;
  completion_rate: number;
  bottleneck_count: number;
  department_breakdown: DepartmentMetric[];
}

export interface DepartmentMetric {
  department: ClearanceDepartment;
  avg_days: number;
  approval_rate: number;
  bottleneck_frequency: number;
  pending_count: number;
}

export interface TrendDataPoint {
  date: string;
  value: number;
}

// ── Staff Dashboard ──────────────────────────────────────────────────────────

export interface DashboardStats {
  active_projects: number;
  pending_clearances: number;
  avg_days_to_issue: number;
  bottlenecks_detected: number;
}

export interface BottleneckItem {
  project_id: string;
  address: string;
  department: string;
  clearance_type: string;
  days_stuck: number;
  predicted_days: number;
}

// ── Notifications ────────────────────────────────────────────────────────────

export type NotificationType =
  | "clearance_status_changed"
  | "inspection_scheduled"
  | "inspection_result"
  | "document_required"
  | "permit_status_changed"
  | "bottleneck_detected";

export interface NotificationPreferences {
  push: boolean;
  sms: boolean;
  email: boolean;
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  response: string;
  sources: string[];
}

// ── Pagination ───────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
