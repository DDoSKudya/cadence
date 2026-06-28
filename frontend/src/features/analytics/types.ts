export interface AnalyticsFilters {
  week?: string;
  from?: string;
  to?: string;
  tag?: string;
  source?: string;
}

export interface AnalyticsSummary {
  period: Record<string, string>;
  scheme?: { slug: string; name: string };
  tasks_created: number;
  tasks_closed: number;
  tasks_archived: number;
  active_tasks: number;
  overdue_tasks: number;
  stale_tasks: number;
  evidence_rate: number;
  stale_items: StaleTaskItem[];
}

export interface StaleTaskItem {
  id: number;
  title: string;
  column: string;
  column_system_type?: string;
  days_in_column: number;
}

export interface WeeklyTrendItem {
  week: string;
  created: number;
  closed: number;
  carried_over: number;
}

export interface BreakdownItem {
  key: string;
  count: number;
  name?: string;
  system_type?: string;
}

export interface CycleTimeData {
  avg_hours: number;
  count: number;
  distribution: { bucket: string; count: number }[];
}

export interface TelegramActionMetric {
  slug: string;
  count: number;
}

export interface NotificationMetrics {
  notifications_sent: number;
  notification_failures: number;
  telegram_actions: TelegramActionMetric[];
  telegram_done_actions: number;
  telegram_in_progress_actions: number;
  tasks_closed_after_notification: number;
}

export interface TaskFlowData {
  reopened_count: number;
  avg_open_age_hours: number;
  carry_over_count: number;
  items: WeeklyTrendItem[];
}

export interface ArchiveAnalytics {
  closed_total: number;
  evidence_coverage: number;
  completion_notes_coverage: number;
  closed_by_week: { week: string; count: number }[];
  closed_by_tag: { tag: string; count: number }[];
}

export type ExportType =
  | "tasks"
  | "archive"
  | "weekly_summary"
  | "tag_summary"
  | "notification_report"
  | "jobs_report"
  | "imports_report";

export type ExportFormat = "csv" | "xlsx" | "pdf";

export interface ExportPreviewSheetData {
  rows: string[][];
  total: number;
  kpis?: Record<"created" | "closed" | "active" | "overdue" | "stale", number>;
}

export type ExportPreviewSheetsMap = Record<string, ExportPreviewSheetData>;

export interface ExportPreviewResponse {
  export_type: ExportType;
  sheets: Array<ExportPreviewSheetData & { id: string }>;
}

export interface ExportSnapshot {
  schemeName?: string;
  summary: AnalyticsSummary | null;
  weeklyTrend: WeeklyTrendItem[];
  columnBreakdown: BreakdownItem[];
  tagBreakdown: BreakdownItem[];
  notifications: NotificationMetrics | null;
  archiveStats: ArchiveAnalytics | null;
}

export interface AnalyticsExportJob {
  id: number;
  export_type: ExportType;
  file_format: ExportFormat;
  status: string;
  filters: Record<string, unknown>;
  file_path: string;
  file_size_bytes: number | null;
  rows_count: number | null;
  error_message: string;
  expires_at: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  background_job_id: number | null;
}
