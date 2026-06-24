import type { TaskStatusGraph, TaskStatusNode } from "@/features/settings/task-status-graph";

export function findInitialStatus(graph: TaskStatusGraph): TaskStatusNode | null {
  return graph.statuses.find((status) => status.is_initial) ?? null;
}

export function allowedStatusTargets(
  graph: TaskStatusGraph,
  fromStatusId: number | null | undefined,
): TaskStatusNode[] {
  if (fromStatusId === null || fromStatusId === undefined) {
    return graph.statuses;
  }
  if (!graph.enforced) {
    return graph.statuses;
  }
  const targetIds = new Set(
    graph.transitions
      .filter((transition) => String(transition.from_status_id) === String(fromStatusId))
      .map((transition) => String(transition.to_status_id)),
  );
  return graph.statuses.filter(
    (status) => status.id !== null && targetIds.has(String(status.id)),
  );
}

export function statusesForColumn(
  graph: TaskStatusGraph,
  columnId: number | null | undefined,
): TaskStatusNode[] {
  if (columnId === null || columnId === undefined) {
    return graph.statuses;
  }
  return graph.statuses.filter((status) => status.column_id === columnId);
}
