from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from apps.core.models import ProjectSettings
from apps.notifications.models import NotificationReason
from apps.tasks.models import Task


def resolve_reminder_interval_minutes(
    task: Task,
    settings: ProjectSettings | None = None,
) -> int:
    if task.reminder_interval_minutes is not None:
        return task.reminder_interval_minutes
    settings = settings or ProjectSettings.load()
    return settings.default_reminder_interval_minutes


def interval_for_reason(
    reason: NotificationReason,
    task: Task,
    settings: ProjectSettings,
) -> int:
    if reason == NotificationReason.REMINDER:
        return resolve_reminder_interval_minutes(task, settings)
    if reason == NotificationReason.STALE_IN_PROGRESS:
        return settings.stale_in_progress_minutes
    if reason == NotificationReason.STALE_PLANNED:
        return settings.stale_planned_minutes
    if reason == NotificationReason.OVERDUE:
        return resolve_reminder_interval_minutes(task, settings)
    return settings.default_reminder_interval_minutes


def dedup_bucket(now: datetime, interval_minutes: int) -> str:
    interval_minutes = max(interval_minutes, 1)
    slot = int(now.timestamp()) // (interval_minutes * 60)
    return str(slot)


def schedule_next_reminder(
    task: Task,
    *,
    settings: ProjectSettings | None = None,
    base_time: datetime | None = None,
) -> None:
    if not task.reminder_enabled:
        task.next_reminder_at = None
        task.save(update_fields=["next_reminder_at", "updated_at"])
        return

    interval = resolve_reminder_interval_minutes(task, settings)
    base = base_time or timezone.now()
    task.next_reminder_at = base + timedelta(minutes=interval)
    task.save(update_fields=["next_reminder_at", "updated_at"])


def refresh_default_reminder_schedules(settings: ProjectSettings) -> int:
    now = timezone.now()
    interval = settings.default_reminder_interval_minutes
    tasks = Task.objects.filter(
        archived_at__isnull=True,
        reminder_enabled=True,
        reminder_interval_minutes__isnull=True,
    )
    updated = 0
    for task in tasks:
        task.next_reminder_at = now + timedelta(minutes=interval)
        task.save(update_fields=["next_reminder_at", "updated_at"])
        updated += 1
    return updated


def on_notification_delivered(task: Task, reason: NotificationReason) -> None:
    settings = ProjectSettings.load()
    if reason in (NotificationReason.REMINDER, NotificationReason.OVERDUE):
        schedule_next_reminder(task, settings=settings)
        return

    stale_reasons = (
        NotificationReason.STALE_IN_PROGRESS,
        NotificationReason.STALE_PLANNED,
    )
    if reason in stale_reasons:
        task.column_entered_at = timezone.now()
        task.save(update_fields=["column_entered_at", "updated_at"])
