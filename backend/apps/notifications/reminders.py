from __future__ import annotations

from apps.notifications.actions import TelegramActionService
from apps.notifications.models import NotificationJob
from apps.notifications.planning import ReminderPlanningService
from apps.tasks.events import resolve_request_context
from apps.tasks.models import Task


class TaskReminderService:
    @staticmethod
    def snooze(task: Task, *, request, minutes: int | None = None) -> Task:
        actor = resolve_request_context(request)
        if minutes is not None:
            task.reminder_interval_minutes = minutes
            task.save(update_fields=["reminder_interval_minutes", "updated_at"])

        TelegramActionService.schedule_next_reminder_with_event(task, actor)
        return task

    @staticmethod
    def cancel(task: Task, *, request) -> Task:
        actor = resolve_request_context(request)
        TelegramActionService.cancel_reminders(task, actor)
        return task

    @staticmethod
    def notify(task: Task) -> NotificationJob | None:
        return ReminderPlanningService.schedule_manual(task)
