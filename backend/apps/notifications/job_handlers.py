from apps.jobs.handlers import register_handler
from apps.jobs.models import JobType
from apps.notifications.tasks import scan_reminders, send_telegram_notification


class NotificationScanHandler:
    def dispatch(self, job) -> None:
        scan_reminders.delay(job.id)


class TelegramSendHandler:
    def dispatch(self, job) -> None:
        notification_job_id = job.payload.get("notification_job_id")
        if notification_job_id is None:
            from apps.notifications.models import NotificationJob

            notification = (
                NotificationJob.objects.filter(background_job=job)
                .order_by("-created_at")
                .first()
            )
            if notification is None:
                raise ValueError("notification job not found for background job")
            notification_job_id = notification.id

        send_telegram_notification.delay(notification_job_id, job.id)


def register() -> None:
    register_handler(JobType.NOTIFICATION_SCAN, NotificationScanHandler())
    register_handler(JobType.TELEGRAM_SEND, TelegramSendHandler())
