import type { SettingsColumn } from "@/features/settings/types";

export interface ColumnTransition {
  from_column_id: number;
  to_column_id: number;
}

export interface ColumnWorkflow {
  enforced: boolean;
  transitions: ColumnTransition[];
}

export function transitionKey(fromColumnId: number, toColumnId: number): string {
  return `${fromColumnId}->${toColumnId}`;
}

export function isTransitionAllowed(
  workflow: ColumnWorkflow,
  fromColumnId: number,
  toColumnId: number,
): boolean {
  if (fromColumnId === toColumnId) {
    return true;
  }
  if (!workflow.enforced) {
    return true;
  }
  return workflow.transitions.some(
    (transition) =>
      transition.from_column_id === fromColumnId &&
      transition.to_column_id === toColumnId,
  );
}

export function outgoingTargetIds(
  workflow: ColumnWorkflow,
  fromColumnId: number,
  columns: SettingsColumn[],
): number[] {
  const otherColumnIds = columns
    .filter((column) => column.id !== fromColumnId)
    .map((column) => column.id);

  if (!workflow.enforced) {
    return otherColumnIds;
  }

  return workflow.transitions
    .filter((transition) => transition.from_column_id === fromColumnId)
    .map((transition) => transition.to_column_id);
}

export function buildFullMeshTransitions(columns: SettingsColumn[]): ColumnTransition[] {
  const transitions: ColumnTransition[] = [];
  for (const fromColumn of columns) {
    for (const toColumn of columns) {
      if (fromColumn.id === toColumn.id) {
        continue;
      }
      transitions.push({
        from_column_id: fromColumn.id,
        to_column_id: toColumn.id,
      });
    }
  }
  return transitions;
}

export function mergeOutgoingTransitions(
  workflow: ColumnWorkflow,
  fromColumnId: number,
  targetColumnIds: number[],
  columns: SettingsColumn[],
): ColumnTransition[] {
  const otherColumnIds = columns
    .filter((column) => column.id !== fromColumnId)
    .map((column) => column.id);

  if (!workflow.enforced) {
    const allSelected =
      otherColumnIds.length === targetColumnIds.length &&
      otherColumnIds.every((columnId) => targetColumnIds.includes(columnId));
    if (allSelected) {
      return [];
    }

    return buildFullMeshTransitions(columns).filter((transition) => {
      if (transition.from_column_id !== fromColumnId) {
        return true;
      }
      return targetColumnIds.includes(transition.to_column_id);
    });
  }

  const retained = workflow.transitions.filter(
    (transition) => transition.from_column_id !== fromColumnId,
  );
  const next = targetColumnIds.map((toColumnId) => ({
    from_column_id: fromColumnId,
    to_column_id: toColumnId,
  }));
  return [...retained, ...next];
}

export function matrixFromWorkflow(
  workflow: ColumnWorkflow,
  columns: SettingsColumn[],
): Record<string, boolean> {
  const matrix: Record<string, boolean> = {};
  for (const fromColumn of columns) {
    for (const toColumn of columns) {
      if (fromColumn.id === toColumn.id) {
        continue;
      }
      const key = transitionKey(fromColumn.id, toColumn.id);
      matrix[key] = isTransitionAllowed(workflow, fromColumn.id, toColumn.id);
    }
  }
  return matrix;
}

export function transitionsFromMatrix(
  columns: SettingsColumn[],
  matrix: Record<string, boolean>,
): ColumnTransition[] {
  const transitions: ColumnTransition[] = [];
  for (const fromColumn of columns) {
    for (const toColumn of columns) {
      if (fromColumn.id === toColumn.id) {
        continue;
      }
      const key = transitionKey(fromColumn.id, toColumn.id);
      if (matrix[key]) {
        transitions.push({
          from_column_id: fromColumn.id,
          to_column_id: toColumn.id,
        });
      }
    }
  }
  return transitions;
}
