import type { ColumnMeta } from "@/shared/types/column";

export interface Tag {
  id: number;
  name: string;
  slug: string;
  color: string;
}

export interface WeekInfo {
  iso_year: number;
  iso_week: number;
}

export interface BoardTask {
  id: number;
  title: string;
  priority: "low" | "normal" | "high" | string;
  position: number;
  column_id: number;
  week_id: number | null;
  due_at: string | null;
  source: string;
  tags: Tag[];
}

export interface BoardColumn extends ColumnMeta {
  tasks: BoardTask[];
}

export interface BoardResponse {
  board: { id: number; name: string };
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
  priority: string;
  due_at: string | null;
  evidence_url: string;
  completion_note: string;
  reminder_enabled: boolean;
  tags: Tag[];
  closed_at: string | null;
  archived_at: string | null;
}

export interface TaskCreatePayload {
  title: string;
  column_id: number;
  week?: string;
  description?: string;
  priority?: string;
  tags?: string[];
  due_at?: string | null;
  evidence_url?: string;
  reminder_enabled?: boolean;
}

export interface TaskUpdatePayload {
  title?: string;
  description?: string;
  priority?: string;
  tags?: string[];
  due_at?: string | null;
  evidence_url?: string;
  reminder_enabled?: boolean;
}
