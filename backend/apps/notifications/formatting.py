from __future__ import annotations

import html

from django.utils import timezone

from apps.common.i18n import format_notification_due_at, t
from apps.notifications.models import NotificationReason
from apps.tasks.models import Task, TaskPriority


def _escape(value: str) -> str:
    return html.escape(value, quote=False)


def _priority_label(priority: str) -> str:
    key = f"notifications.priority.{priority}"
    label = t(key)
    return label if label != key else priority


def _status_label(task: Task) -> str:
    status = task.task_status
    if status is not None:
        slug_keys = {
            "open": "defaults.status.open",
            "ready_on_develop": "defaults.status.readyOnDevelop",
            "process": "defaults.status.process",
            "testing": "defaults.status.testing",
            "done": "defaults.status.done",
            "cancel": "defaults.status.cancel",
        }
        key = slug_keys.get(status.slug)
        if key is not None:
            return t(key)
        return status.name
    return t("notifications.statusUnknown")


def _column_label(task: Task) -> str:
    return task.column.name if task.column_id else "—"


def _tags_line(task: Task) -> str | None:
    tags = list(task.tags.all()[:5])
    if not tags:
        return None
    names = ", ".join(_escape(tag.name) for tag in tags)
    return t("notifications.tagsLine", tags=names)


def build_notification_message(task: Task, reason: NotificationReason) -> str:
    reason_key = {
        NotificationReason.OVERDUE: "notifications.reason.overdue",
        NotificationReason.STALE_IN_PROGRESS: "notifications.reason.staleInProgress",
        NotificationReason.STALE_PLANNED: "notifications.reason.stalePlanned",
        NotificationReason.REMINDER: "notifications.reason.reminder",
        NotificationReason.MANUAL: "notifications.reason.manual",
    }[reason]
    reason_label = t(reason_key)

    lines = [
        t("notifications.message.header", reason=reason_label),
        "",
        f"<b>{_escape(task.title)}</b>",
        t(
            "notifications.message.statusColumn",
            status=_escape(_status_label(task)),
            column=_escape(_column_label(task)),
        ),
    ]

    if task.priority != TaskPriority.NORMAL:
        priority_value = _escape(_priority_label(task.priority))
        lines.append(t("notifications.message.priority", value=priority_value))

    if task.story_points is not None:
        lines.append(
            t("notifications.message.storyPoints", points=task.story_points),
        )

    if task.due_at is not None:
        due_value = format_notification_due_at(task.due_at)
        overdue = reason == NotificationReason.OVERDUE
        due_key = (
            "notifications.message.dueOverdue"
            if overdue
            else "notifications.message.due"
        )
        lines.append(t(due_key, value=due_value))

    description = task.description.strip()
    if description:
        preview = description if len(description) <= 240 else f"{description[:237]}…"
        lines.append("")
        lines.append(t("notifications.message.description"))
        lines.append(f"<i>{_escape(preview)}</i>")

    tags_line = _tags_line(task)
    if tags_line:
        lines.append(tags_line)

    lines.append("")
    lines.append(
        t(
            "notifications.message.footer",
            time=format_notification_due_at(timezone.now()),
        ),
    )
    return "\n".join(lines)
