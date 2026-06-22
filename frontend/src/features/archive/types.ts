import type { Tag } from "@/features/board/types";

export interface WeekRef {
  id: number;
  iso_year: number;
  iso_week: number;
  starts_on: string;
  ends_on: string;
  review_notes: string;
  closed_at: string | null;
}

export interface ArchiveTaskSummary {
  id: number;
  title: string;
  column_id: number;
  column_name: string;
  column_system_type: string;
  week: WeekRef | null;
  week_id: number | null;
  priority: string;
  source: string;
  completion_note: string;
  evidence_url: string;
  closed_at: string | null;
  archived_at: string | null;
  tags: Tag[];
}

export interface TaskEventItem {
  id: number;
  event_type: string;
  actor_type: string;
  actor_id: string;
  source: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ArchiveTaskDetail extends ArchiveTaskSummary {
  description: string;
  board_id: number;
  position: number;
  due_at: string | null;
  reminder_enabled: boolean;
  events: TaskEventItem[];
}

export interface ArchiveFilters {
  week?: string;
  tag?: string;
  source?: string;
  search?: string;
  closed_from?: string;
  closed_to?: string;
  page?: number;
  page_size?: number;
}

export interface ArchiveListResponse {
  count: number;
  page: number;
  page_size: number;
  results: ArchiveTaskSummary[];
}
