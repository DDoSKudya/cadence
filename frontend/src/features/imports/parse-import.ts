const SCHEMA_VERSION = "1.0";
const VALID_PRIORITIES = new Set(["low", "normal", "high"]);
const WEEK_PATTERN = /^\d{4}-W\d{2}$/;

export interface ImportTaskPreview {
  title: string;
  column: string;
  priority: string;
  tags: string[];
}

export interface ValidImportPreview {
  status: "valid";
  id: string;
  file: File;
  idempotencyKey: string;
  sourceLabel: string;
  week: string | null;
  tasks: ImportTaskPreview[];
}

export interface InvalidImportPreview {
  status: "invalid";
  id: string;
  file: File;
  error: string;
}

export type ImportPreview = ValidImportPreview | InvalidImportPreview;

class ImportParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ImportParseError";
  }
}

export async function parseImportFile(file: File): Promise<ImportPreview> {
  const id = crypto.randomUUID();

  try {
    const text = await readFileText(file);
    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      throw new ImportParseError("Некорректный JSON");
    }

    const payload = validateImportPayload(data);
    return {
      status: "valid",
      id,
      file,
      idempotencyKey: payload.idempotencyKey,
      sourceLabel: payload.sourceLabel,
      week: payload.week,
      tasks: payload.tasks,
    };
  } catch (error) {
    return {
      status: "invalid",
      id,
      file,
      error: error instanceof Error ? error.message : "Не удалось разобрать файл",
    };
  }
}

function validateImportPayload(data: unknown): {
  idempotencyKey: string;
  sourceLabel: string;
  week: string | null;
  tasks: ImportTaskPreview[];
} {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new ImportParseError("Корень файла должен быть объектом");
  }

  const root = data as Record<string, unknown>;

  if (root.schema_version !== SCHEMA_VERSION) {
    throw new ImportParseError(`Неподдерживаемая версия схемы: ${String(root.schema_version)}`);
  }

  const idempotencyKey = root.idempotency_key;
  if (typeof idempotencyKey !== "string" || !idempotencyKey.trim()) {
    throw new ImportParseError("Не указан idempotency_key");
  }
  if (idempotencyKey.trim().length > 180) {
    throw new ImportParseError("idempotency_key слишком длинный");
  }

  const tasksRaw = root.tasks;
  if (!Array.isArray(tasksRaw) || tasksRaw.length === 0) {
    throw new ImportParseError("Список tasks пуст");
  }

  const sourceRaw = root.source ?? "json_import";
  if (sourceRaw !== null && typeof sourceRaw !== "string") {
    throw new ImportParseError("Поле source должно быть строкой");
  }
  const sourceLabel = (String(sourceRaw || "json_import").trim() || "json_import");

  const week = validateWeek(root.week);
  const tasks = tasksRaw.map((item, index) => validateTask(item, index));

  return {
    idempotencyKey: idempotencyKey.trim(),
    sourceLabel,
    week,
    tasks,
  };
}

function validateWeek(raw: unknown): string | null {
  if (raw === null || raw === undefined) {
    return null;
  }
  if (typeof raw !== "string") {
    throw new ImportParseError("Поле week должно быть строкой");
  }

  const value = raw.trim();
  if (!WEEK_PATTERN.test(value)) {
    throw new ImportParseError("Неверный формат week");
  }

  const isoWeek = Number(value.split("-W")[1]);
  if (isoWeek < 1 || isoWeek > 53) {
    throw new ImportParseError("Неверный формат week");
  }

  return value;
}

function validateTask(raw: unknown, index: number): ImportTaskPreview {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new ImportParseError(`tasks[${index}] должен быть объектом`);
  }

  const task = raw as Record<string, unknown>;
  const title = task.title;
  if (typeof title !== "string" || !title.trim()) {
    throw new ImportParseError(`tasks[${index}]: не указан title`);
  }
  if (title.trim().length > 240) {
    throw new ImportParseError(`tasks[${index}]: title слишком длинный`);
  }

  let column = task.column ?? "backlog";
  if (column === null) {
    column = "backlog";
  }
  if (typeof column !== "string" || !column.trim()) {
    throw new ImportParseError(`tasks[${index}]: column должен быть строкой`);
  }

  const tagsRaw = task.tags ?? [];
  if (tagsRaw === null) {
    throw new ImportParseError(`tasks[${index}]: tags должен быть массивом строк`);
  }
  if (!Array.isArray(tagsRaw) || tagsRaw.some((tag) => typeof tag !== "string")) {
    throw new ImportParseError(`tasks[${index}]: tags должен быть массивом строк`);
  }
  const tags = tagsRaw.map((tag) => tag.trim()).filter(Boolean);

  let priority = task.priority ?? "normal";
  if (priority === null) {
    priority = "normal";
  }
  if (typeof priority !== "string" || !VALID_PRIORITIES.has(priority)) {
    throw new ImportParseError(`tasks[${index}]: неверный priority`);
  }

  validateDueAt(task.due_at, index);

  return {
    title: title.trim(),
    column: column.trim(),
    priority,
    tags,
  };
}

function validateDueAt(raw: unknown, index: number): void {
  if (raw === null || raw === undefined || raw === "") {
    return;
  }
  if (typeof raw !== "string" || !raw.trim()) {
    return;
  }

  const value = raw.trim().endsWith("Z") ? `${raw.trim().slice(0, -1)}+00:00` : raw.trim();
  if (Number.isNaN(Date.parse(value))) {
    throw new ImportParseError(`tasks[${index}]: неверный due_at`);
  }
}

export function priorityLabel(priority: string): string {
  const labels: Record<string, string> = {
    low: "Низкий",
    normal: "Обычный",
    high: "Высокий",
  };
  return labels[priority] ?? priority;
}

async function readFileText(file: File): Promise<string> {
  if (typeof file.text === "function") {
    return file.text();
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error ?? new Error("Не удалось прочитать файл"));
    reader.readAsText(file);
  });
}
