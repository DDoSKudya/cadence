export function isTerminalBoardColumn(
  columnId: number | null | undefined,
  columns: ReadonlyArray<{ id: number; position: number }>,
): boolean {
  if (columnId === null || columnId === undefined || columns.length === 0) {
    return false;
  }

  const lastColumn = [...columns].sort((left, right) => left.position - right.position).at(-1);
  return lastColumn?.id === columnId;
}
