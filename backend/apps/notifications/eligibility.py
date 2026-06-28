from __future__ import annotations

from apps.notifications.models import NotificationStatus
from apps.tasks.models import Task

NON_NOTIFIABLE_STATUS_SLUGS = frozenset({"done", "cancel"})


def task_accepts_notifications(task: Task) -> bool:
    if task.archived_at is not None or not task.reminder_enabled:
        return False

    status = task.task_status
    if status is None:
        return True
    return not (status.is_terminal or status.slug in NON_NOTIFIABLE_STATUS_SLUGS)


def cancel_pending_notifications(task_id: int) -> None:
    from django.apps import apps as django_apps

    if not django_apps.is_installed("apps.notifications"):
        return

    notification_job = django_apps.get_model("notifications", "NotificationJob")
    notification_job.objects.filter(
        task_id=task_id,
        status=NotificationStatus.PENDING,
    ).update(status=NotificationStatus.CANCELLED)


def suppress_task_notifications(task: Task) -> None:
    task.reminder_enabled = False
    task.next_reminder_at = None
    task.save(update_fields=["reminder_enabled", "next_reminder_at", "updated_at"])
    cancel_pending_notifications(task.id)
