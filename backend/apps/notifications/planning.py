from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.boards.models import SystemType
from apps.common.i18n import format_notification_due_at, t
from apps.core.models import ProjectSettings
from apps.jobs.models import JobType
from apps.jobs.services import JobService
from apps.notifications.models import (
    NotificationJob,
    NotificationReason,
)
from apps.notifications.scheduling import (
    dedup_bucket,
    interval_for_reason,
    schedule_next_reminder,
)
from apps.tasks.models import Task


class ReminderPlanningService:
    @staticmethod
    def scan() -> dict[str, int | str]:
        project_settings = ProjectSettings.load()
        if not project_settings.telegram_enabled:
            return {"planned": 0, "skipped": "telegram_disabled"}

        chat_ids = project_settings.telegram_recipient_chat_ids()
        if not chat_ids:
            return {"planned": 0, "skipped": "no_recipients"}

        if ReminderPlanningService._in_quiet_hours(project_settings):
            return {"planned": 0, "skipped": "quiet_hours"}

        for task in Task.objects.filter(
            archived_at__isnull=True,
            reminder_enabled=True,
            next_reminder_at__isnull=True,
        ):
            schedule_next_reminder(task, settings=project_settings)

        now = timezone.now()
        planned = 0
        tasks = Task.objects.filter(
            archived_at__isnull=True,
            reminder_enabled=True,
        ).select_related("column")

        for task in tasks:
            reason = ReminderPlanningService._resolve_reason(
                task,
                project_settings,
                now,
            )
            if reason is None:
                continue
            for chat_id in chat_ids:
                if ReminderPlanningService._schedule(
                    task,
                    reason,
                    chat_id,
                    now,
                    project_settings,
                ):
                    planned += 1

        return {"planned": planned}

    @staticmethod
    def schedule_manual(task: Task) -> NotificationJob | None:
        project_settings = ProjectSettings.load()
        if not project_settings.telegram_enabled:
            return None

        chat_ids = project_settings.telegram_recipient_chat_ids()
        if not chat_ids:
            return None

        now = timezone.now()
        if ReminderPlanningService._in_quiet_hours(project_settings):
            return None

        created: NotificationJob | None = None
        for chat_id in chat_ids:
            dedup_key = f"manual:task:{task.id}:{chat_id}:{now.strftime('%Y%m%d%H%M')}"
            notification = ReminderPlanningService._create_notification(
                task=task,
                reason=NotificationReason.MANUAL,
                chat_id=chat_id,
                scheduled_at=now,
                dedup_key=dedup_key,
            )
            if notification is not None:
                created = notification
        return created

    @staticmethod
    def _resolve_reason(
        task: Task,
        project_settings: ProjectSettings,
        now: datetime,
    ) -> NotificationReason | None:
        if task.due_at is not None and task.due_at < now:
            return NotificationReason.OVERDUE

        if task.next_reminder_at is not None and task.next_reminder_at <= now:
            return NotificationReason.REMINDER

        stale_delta = now - task.column_entered_at
        if task.column.system_type == SystemType.IN_PROGRESS:
            threshold = timedelta(minutes=project_settings.stale_in_progress_minutes)
            if stale_delta >= threshold:
                return NotificationReason.STALE_IN_PROGRESS

        if task.column.system_type in (SystemType.PLANNED, SystemType.BACKLOG):
            threshold = timedelta(minutes=project_settings.stale_planned_minutes)
            if stale_delta >= threshold:
                return NotificationReason.STALE_PLANNED

        return None

    @staticmethod
    def _schedule(
        task: Task,
        reason: NotificationReason,
        chat_id: str,
        now: datetime,
        project_settings: ProjectSettings,
    ) -> bool:
        dedup_key = ReminderPlanningService._dedup_key(
            task,
            reason,
            chat_id,
            now,
            project_settings,
        )
        notification = ReminderPlanningService._create_notification(
            task=task,
            reason=reason,
            chat_id=chat_id,
            scheduled_at=now,
            dedup_key=dedup_key,
        )
        return notification is not None

    @staticmethod
    def _dedup_key(
        task: Task,
        reason: NotificationReason,
        chat_id: str,
        now: datetime,
        project_settings: ProjectSettings,
    ) -> str:
        interval = interval_for_reason(reason, task, project_settings)
        bucket = dedup_bucket(now, interval)
        return f"task:{task.id}:reason:{reason}:chat:{chat_id}:{bucket}"

    @staticmethod
    @transaction.atomic
    def _create_notification(
        *,
        task: Task,
        reason: NotificationReason,
        chat_id: str,
        scheduled_at: datetime,
        dedup_key: str,
    ) -> NotificationJob | None:
        if NotificationJob.objects.filter(dedup_key=dedup_key).exists():
            return None

        message_text = ReminderPlanningService._build_message(task, reason)
        background_job = JobService.create(
            JobType.TELEGRAM_SEND,
            {"task_id": task.id, "reason": reason, "chat_id": chat_id},
        )
        try:
            notification = NotificationJob.objects.create(
                task=task,
                background_job=background_job,
                telegram_chat_id=chat_id,
                message_text=message_text,
                reason=reason,
                scheduled_at=scheduled_at,
                dedup_key=dedup_key,
            )
        except IntegrityError:
            return None
        background_job.payload = {
            "task_id": task.id,
            "reason": reason,
            "chat_id": chat_id,
            "notification_job_id": notification.id,
        }
        background_job.save(update_fields=["payload", "updated_at"])

        from apps.notifications.tasks import send_telegram_notification

        send_telegram_notification.delay(notification.id, background_job.id)
        return notification

    @staticmethod
    def _build_message(task: Task, reason: NotificationReason) -> str:
        labels = {
            NotificationReason.OVERDUE: t("notifications.reason.overdue"),
            NotificationReason.STALE_IN_PROGRESS: t(
                "notifications.reason.staleInProgress",
            ),
            NotificationReason.STALE_PLANNED: t("notifications.reason.stalePlanned"),
            NotificationReason.REMINDER: t("notifications.reason.reminder"),
            NotificationReason.MANUAL: t("notifications.reason.reminder"),
        }
        lines = [labels[reason], task.title]
        if task.due_at is not None:
            due_value = format_notification_due_at(task.due_at)
            lines.append(t("notifications.dueAt", value=due_value))
        return "\n".join(lines)

    @staticmethod
    def _in_quiet_hours(project_settings: ProjectSettings) -> bool:
        start = project_settings.quiet_hours_start
        end = project_settings.quiet_hours_end
        if start is None or end is None:
            return False

        now_time = timezone.localtime().time()
        if start <= end:
            return start <= now_time < end
        return now_time >= start or now_time < end
