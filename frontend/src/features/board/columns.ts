export function isTerminalBoardColumn(
  columnId: number | null | undefined,
  columns: ReadonlyArray<{ id: number; position: number; system_type?: string | null }>,
): boolean {
  if (columnId === null || columnId === undefined || columns.length === 0) {
    return false;
  }

  const semanticTerminal = columns.find((column) => column.system_type === "done");
  if (semanticTerminal) {
    return semanticTerminal.id === columnId;
  }

  const lastColumn = [...columns].sort((left, right) => left.position - right.position).at(-1);
  return lastColumn?.id === columnId;
}
