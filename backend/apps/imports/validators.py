import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class ImportValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


SUPPORTED_SCHEMA_VERSION = "1.0"
VALID_PRIORITIES = frozenset({"low", "normal", "high"})
WEEK_PATTERN = re.compile(r"^\d{4}-W\d{2}$")
ISO_WEEK_MIN = 1
ISO_WEEK_MAX = 53
IDEMPOTENCY_KEY_MAX_LENGTH = 180
TASK_TITLE_MAX_LENGTH = 240


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
    if len(idempotency_key) > IDEMPOTENCY_KEY_MAX_LENGTH:
        raise ImportValidationError("idempotency_key is too long")

    tasks_raw = data.get("tasks")
    if not isinstance(tasks_raw, list) or not tasks_raw:
        raise ImportValidationError("tasks must contain at least one item")

    source_label = data.get("source", "json_import")
    if source_label is not None and not isinstance(source_label, str):
        raise ImportValidationError("source must be a string")
    source_label = (source_label or "json_import").strip() or "json_import"

    week = _validate_week(data.get("week"))

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

    return ImportTaskPayload(
        title=_validate_title(raw.get("title"), index),
        description=_optional_string(raw, "description", index, default=""),
        column=_validate_column(raw.get("column"), index),
        tags=_validate_tags(raw.get("tags"), index),
        priority=_validate_priority(raw.get("priority")),
        due_at=_parse_due_at(raw.get("due_at"), index),
        evidence_url=_optional_string(raw, "evidence_url", index, default=""),
        reminder_enabled=_validate_reminder_enabled(raw.get("reminder_enabled"), index),
        external_ref=_optional_string(raw, "external_ref", index, default="").strip(),
    )


def _validate_title(raw: Any, index: int) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ImportValidationError(f"tasks[{index}].title is required")
    title = raw.strip()
    if len(title) > TASK_TITLE_MAX_LENGTH:
        raise ImportValidationError(f"tasks[{index}].title is too long")
    return title


def _validate_column(raw: Any, index: int) -> str:
    if raw is None:
        raw = "backlog"
    if not isinstance(raw, str) or not raw.strip():
        raise ImportValidationError(f"tasks[{index}].column must be a string")
    return raw.strip()


def _validate_tags(raw: Any, index: int) -> list[str]:
    if raw is None:
        raw = []
    if not isinstance(raw, list) or any(not isinstance(tag, str) for tag in raw):
        raise ImportValidationError(f"tasks[{index}].tags must be a string array")
    return [tag.strip() for tag in raw if tag.strip()]


def _validate_priority(raw: Any) -> str:
    if raw is None:
        raw = "normal"
    if not isinstance(raw, str) or raw not in VALID_PRIORITIES:
        raise ImportValidationError(f"invalid priority: {raw!r}")
    return raw


def _validate_reminder_enabled(raw: Any, index: int) -> bool:
    if raw is None:
        return True
    if not isinstance(raw, bool):
        raise ImportValidationError(
            f"tasks[{index}].reminder_enabled must be a boolean",
        )
    return raw


def _optional_string(
    data: dict[str, Any],
    field: str,
    index: int,
    *,
    default: str,
) -> str:
    value = data.get(field, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ImportValidationError(f"tasks[{index}].{field} must be a string")
    return value


def _validate_week(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ImportValidationError("week must be a string")

    value = raw.strip()
    if not WEEK_PATTERN.match(value):
        raise ImportValidationError("invalid week format")

    iso_week = int(value.split("-W", 1)[1])
    if iso_week < ISO_WEEK_MIN or iso_week > ISO_WEEK_MAX:
        raise ImportValidationError("invalid week format")

    return value


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
