import type { ColumnMeta } from "@/shared/types/column";

export type TaskType = "epic" | "story" | "task" | "bug";
export type TaskLinkType = "relates" | "blocks" | "duplicates";

export interface TaskLinkItem {
  id?: number;
  task_id: number;
  title: string;
  task_type: TaskType;
  link_type: TaskLinkType;
  direction: "outgoing" | "incoming";
}

export interface TaskLinkWrite {
  target_task_id: number;
  link_type: TaskLinkType;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
  color: string;
}

export interface WeekInfo {
  id: number;
  iso_year: number;
  iso_week: number;
}

export interface BoardTask {
  id: number;
  title: string;
  description?: string;
  task_type: TaskType;
  priority: "low" | "normal" | "high" | string;
  position: number;
  column_id: number;
  week_id: number | null;
  due_at: string | null;
  source: string;
  story_points?: number | null;
  tags: Tag[];
  task_status_id?: number | null;
  task_status_name?: string | null;
  links_count?: number;
}

export interface TaskStatusInfo {
  id: number;
  name: string;
  slug: string;
  color: string;
}

export interface BoardColumn extends ColumnMeta {
  tasks: BoardTask[];
}

export interface BoardResponse {
  board: { id: number; name: string; is_default?: boolean };
  week: WeekInfo;
  columns: BoardColumn[];
}

export interface TaskDetail {
  id: number;
  title: string;
  description: string;
  board_id: number;
  column_id: number;
  week: WeekInfo | null;
  week_id: number | null;
  position: number;
  task_type: TaskType;
  priority: string;
  due_at: string | null;
  completion_note: string;
  story_points: number | null;
  external_ref: string;
  reminder_enabled: boolean;
  tags: Tag[];
  closed_at: string | null;
  archived_at: string | null;
  task_status_id: number | null;
  task_status: TaskStatusInfo | null;
  links: TaskLinkItem[];
}

export interface TaskCreatePayload {
  title: string;
  column_id: number;
  task_type: TaskType;
  week?: string;
  description?: string;
  priority?: string;
  tags?: string[];
  due_at?: string | null;
  reminder_enabled?: boolean;
  story_points?: number | null;
  external_ref?: string;
  links?: TaskLinkWrite[];
}

export interface TaskUpdatePayload {
  title?: string;
  description?: string;
  task_type?: TaskType;
  priority?: string;
  tags?: string[];
  due_at?: string | null;
  reminder_enabled?: boolean;
  story_points?: number | null;
  external_ref?: string;
  task_status_id?: number | null;
  links?: TaskLinkWrite[];
}
