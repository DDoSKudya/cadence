from django.db import transaction
from django.utils import timezone

from apps.jobs.services import JobService
from apps.notifications.models import (
    NotificationJob,
    NotificationReason,
    NotificationStatus,
)
from apps.notifications.scheduling import on_notification_delivered
from apps.tasks.events import EventActor, record_task_event
from apps.tasks.models import ActorType, TaskEventType, TaskSource
from apps.telegram_bot.bot import build_task_keyboard, get_bot, run_telegram_async


class NotificationDispatchError(Exception):
    pass


class NotificationDispatchService:
    @staticmethod
    def send(notification_job_id: int, background_job_id: int | None = None) -> dict:
        notification = NotificationJob.objects.select_related("task").get(
            pk=notification_job_id,
        )
        if notification.status != NotificationStatus.PENDING:
            return {"skipped": notification.status}

        if background_job_id is not None:
            job = notification.background_job
            if job is not None and job.id == background_job_id:
                JobService.mark_processing(job)

        notification.status = NotificationStatus.PROCESSING
        notification.save(update_fields=["status"])

        try:
            message_id = NotificationDispatchService._deliver(notification)
        except Exception as exc:
            NotificationDispatchService._fail(notification, str(exc))
            raise NotificationDispatchError(str(exc)) from exc

        NotificationDispatchService._succeed(notification, message_id)
        return {"message_id": message_id}

    @staticmethod
    def _deliver(notification: NotificationJob) -> str:
        bot = get_bot()
        keyboard = build_task_keyboard(
            notification.task_id,
            notification.id,
        )

        async def _send():
            message = await bot.send_message(
                chat_id=notification.telegram_chat_id,
                text=notification.message_text,
                reply_markup=keyboard,
            )
            return str(message.message_id)

        return run_telegram_async(_send())

    @staticmethod
    @transaction.atomic
    def _succeed(notification: NotificationJob, message_id: str) -> None:
        now = timezone.now()
        notification.status = NotificationStatus.SUCCEEDED
        notification.message_id = message_id
        notification.sent_at = now
        notification.last_error = ""
        notification.save(
            update_fields=[
                "status",
                "message_id",
                "sent_at",
                "last_error",
            ],
        )

        task = notification.task
        task.last_notified_at = now
        task.save(update_fields=["last_notified_at", "updated_at"])

        on_notification_delivered(task, NotificationReason(notification.reason))

        actor = EventActor(ActorType.SYSTEM, "", TaskSource.SYSTEM)
        record_task_event(
            task,
            TaskEventType.NOTIFICATION_SENT,
            actor=actor,
            payload={
                "notification_job_id": notification.id,
                "reason": notification.reason,
                "message_id": message_id,
            },
        )

        background_job = notification.background_job
        if background_job is not None:
            JobService.succeed(
                background_job,
                {"notification_job_id": notification.id, "message_id": message_id},
            )

    @staticmethod
    def _fail(notification: NotificationJob, error_message: str) -> None:
        now = timezone.now()
        notification.status = NotificationStatus.FAILED
        notification.failed_at = now
        notification.last_error = error_message
        notification.save(
            update_fields=["status", "failed_at", "last_error"],
        )

        background_job = notification.background_job
        if background_job is not None:
            JobService.fail(background_job, error_message)
