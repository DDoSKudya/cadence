export interface TaskStatusRules {
  creation_only?: boolean;
  auto_move_column?: boolean;
  required_fields?: string[];
  [key: string]: unknown;
}

export interface TaskStatusNode {
  id: number | null;
  client_key?: string;
  name: string;
  slug?: string;
  color: string;
  layout_x: number;
  layout_y: number;
  on_flow: boolean;
  position?: number;
  is_initial: boolean;
  is_terminal: boolean;
  column_id?: number | null;
  column_name?: string | null;
  rules: TaskStatusRules;
}

export interface TaskStatusTransition {
  from_status_id: number | string;
  to_status_id: number | string;
  rules?: TaskStatusRules;
}

export interface TaskStatusGraph {
  enforced: boolean;
  statuses: TaskStatusNode[];
  transitions: TaskStatusTransition[];
  limits?: {
    max_task_statuses: number;
  };
}

export function statusNodeKey(status: Pick<TaskStatusNode, "id" | "client_key">): string {
  if (status.id !== null && status.id !== undefined) {
    return String(status.id);
  }
  return status.client_key ?? "";
}
