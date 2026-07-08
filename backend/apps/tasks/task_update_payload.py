from collections.abc import Mapping
from datetime import datetime
from typing import cast

from rest_framework.request import Request

from apps.tasks.services import TaskUpdateInput, parse_task_link_inputs
from apps.weeks.services import WeekService


def _optional_str(data: Mapping[str, object], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def _optional_int(data: Mapping[str, object], key: str) -> int | None:
    value = data.get(key)
    return value if isinstance(value, int) else None


def _optional_bool(data: Mapping[str, object], key: str) -> bool | None:
    value = data.get(key)
    return value if isinstance(value, bool) else None


def _optional_datetime(data: Mapping[str, object], key: str) -> datetime | None:
    value = data.get(key)
    return value if isinstance(value, datetime) else None


def _optional_tag_list(data: Mapping[str, object], key: str) -> list[str] | None:
    value = data.get(key)
    if not isinstance(value, list):
        return None
    return cast(list[str], value)


def build_task_update_input(
    request: Request, data: Mapping[str, object]
) -> TaskUpdateInput:
    week = None
    week_provided = False
    clear_week = False
    if "week" in data:
        week_provided = True
        if data["week"] is None:
            clear_week = True
        else:
            week = WeekService.resolve_week(_optional_str(data, "week"))

    clear_due_at = "due_at" in data and data["due_at"] is None
    clear_reminder_interval = (
        "reminder_interval_minutes" in data
        and data["reminder_interval_minutes"] is None
    )
    clear_story_points = "story_points" in data and data["story_points"] is None

    return TaskUpdateInput(
        request=request,
        title=_optional_str(data, "title"),
        description=_optional_str(data, "description"),
        task_type=_optional_str(data, "task_type"),
        priority=_optional_str(data, "priority"),
        week=week,
        week_provided=week_provided,
        clear_week=clear_week,
        due_at=_optional_datetime(data, "due_at"),
        clear_due_at=clear_due_at,
        reminder_enabled=_optional_bool(data, "reminder_enabled"),
        reminder_interval_minutes=_optional_int(data, "reminder_interval_minutes"),
        clear_reminder_interval=clear_reminder_interval,
        tag_slugs=_optional_tag_list(data, "tags"),
        task_status_id=_optional_int(data, "task_status_id"),
        task_status_provided="task_status_id" in data,
        story_points=_optional_int(data, "story_points"),
        clear_story_points=clear_story_points,
        external_ref=_optional_str(data, "external_ref"),
        links=parse_task_link_inputs(data.get("links")) if "links" in data else None,
        links_provided="links" in data,
    )
