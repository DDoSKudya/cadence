const PRIORITY_LABELS: Record<string, string> = {
  high: "Высокий",
  normal: "Обычный",
  low: "Низкий",
};

const SYSTEM_TYPE_LABELS: Record<string, string> = {
  backlog: "Бэклог",
  planned: "План",
  in_progress: "В работе",
  blocked: "Блокер",
  review: "Проверка",
  done: "Готово",
};

export function priorityLabel(value: string): string {
  return PRIORITY_LABELS[value] ?? value;
}

export function systemTypeLabel(value: string): string {
  return SYSTEM_TYPE_LABELS[value] ?? value;
}
