from dataclasses import dataclass
from datetime import datetime
from typing import Any


class ImportValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


SUPPORTED_SCHEMA_VERSION = "1.0"
VALID_PRIORITIES = frozenset({"low", "normal", "high"})


@dataclass(frozen=True)
class ImportTaskPayload:
    title: str
    description: str
    column: str
    tags: list[str]
    priority: str
    due_at: datetime | None
    evidence_url: str
    reminder_enabled: bool
    external_ref: str


@dataclass(frozen=True)
class ImportFilePayload:
    schema_version: str
    idempotency_key: str
    source_label: str
    week: str | None
    tasks: list[ImportTaskPayload]


def validate_import_payload(data: Any) -> ImportFilePayload:
    if not isinstance(data, dict):
        raise ImportValidationError("root value must be an object")

    schema_version = data.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ImportValidationError(f"unsupported schema_version: {schema_version!r}")

    idempotency_key = data.get("idempotency_key")
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise ImportValidationError("missing required field: idempotency_key")
    idempotency_key = idempotency_key.strip()
    if len(idempotency_key) > 180:
        raise ImportValidationError("idempotency_key is too long")

    tasks_raw = data.get("tasks")
    if not isinstance(tasks_raw, list) or not tasks_raw:
        raise ImportValidationError("tasks must contain at least one item")

    source_label = data.get("source", "json_import")
    if source_label is not None and not isinstance(source_label, str):
        raise ImportValidationError("source must be a string")
    source_label = (source_label or "json_import").strip() or "json_import"

    week = data.get("week")
    if week is not None and not isinstance(week, str):
        raise ImportValidationError("week must be a string")

    tasks = [_validate_task(item, index) for index, item in enumerate(tasks_raw)]
    return ImportFilePayload(
        schema_version=schema_version,
        idempotency_key=idempotency_key,
        source_label=source_label,
        week=week,
        tasks=tasks,
    )


def _validate_task(raw: Any, index: int) -> ImportTaskPayload:
    if not isinstance(raw, dict):
        raise ImportValidationError(f"tasks[{index}] must be an object")

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ImportValidationError(f"tasks[{index}].title is required")
    title = title.strip()
    if len(title) > 240:
        raise ImportValidationError(f"tasks[{index}].title is too long")

    description = raw.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str):
        raise ImportValidationError(f"tasks[{index}].description must be a string")

    column = raw.get("column", "backlog")
    if column is None:
        column = "backlog"
    if not isinstance(column, str) or not column.strip():
        raise ImportValidationError(f"tasks[{index}].column must be a string")
    column = column.strip()

    tags_raw = raw.get("tags", [])
    if tags_raw is None:
        tags_raw = []
    if not isinstance(tags_raw, list) or any(
        not isinstance(tag, str) for tag in tags_raw
    ):
        raise ImportValidationError(f"tasks[{index}].tags must be a string array")
    tags = [tag.strip() for tag in tags_raw if tag.strip()]

    priority = raw.get("priority", "normal")
    if priority is None:
        priority = "normal"
    if not isinstance(priority, str) or priority not in VALID_PRIORITIES:
        raise ImportValidationError(f"invalid priority: {priority!r}")

    due_at = _parse_due_at(raw.get("due_at"), index)

    evidence_url = raw.get("evidence_url", "")
    if evidence_url is None:
        evidence_url = ""
    if not isinstance(evidence_url, str):
        raise ImportValidationError(f"tasks[{index}].evidence_url must be a string")

    reminder_enabled = raw.get("reminder_enabled", True)
    if reminder_enabled is None:
        reminder_enabled = True
    if not isinstance(reminder_enabled, bool):
        raise ImportValidationError(
            f"tasks[{index}].reminder_enabled must be a boolean",
        )

    external_ref = raw.get("external_ref", "")
    if external_ref is None:
        external_ref = ""
    if not isinstance(external_ref, str):
        raise ImportValidationError(f"tasks[{index}].external_ref must be a string")

    return ImportTaskPayload(
        title=title,
        description=description,
        column=column,
        tags=tags,
        priority=priority,
        due_at=due_at,
        evidence_url=evidence_url,
        reminder_enabled=reminder_enabled,
        external_ref=external_ref.strip(),
    )


def _parse_due_at(raw: Any, index: int) -> datetime | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        return None

    value = raw.strip()
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"

    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ImportValidationError(f"tasks[{index}].due_at is invalid") from exc
