from celery import shared_task
from django.db.utils import DatabaseError, OperationalError

from apps.jobs.models import BackgroundJob, JobType
from apps.jobs.services import JobService
from apps.notifications.dispatch import (
    NotificationDispatchError,
    NotificationDispatchService,
)
from apps.notifications.planning import ReminderPlanningService


@shared_task(
    name="apps.notifications.tasks.scan_reminders",
    bind=True,
    queue="maintenance",
    autoretry_for=(OperationalError, DatabaseError),
    retry_backoff=True,
    max_retries=3,
)
def scan_reminders(self, job_id: int | None = None) -> dict:
    if job_id is not None:
        job = BackgroundJob.objects.get(pk=job_id)
    else:
        job = JobService.create(JobType.NOTIFICATION_SCAN, {})

    JobService.mark_processing(job, celery_task_id=self.request.id)

    try:
        result = ReminderPlanningService.scan()
    except Exception as exc:
        JobService.fail(job, str(exc))
        raise

    JobService.succeed(job, result)
    return result


@shared_task(
    name="apps.notifications.tasks.send_telegram_notification",
    bind=True,
    queue="notifications",
    autoretry_for=(OperationalError, DatabaseError, NotificationDispatchError),
    retry_backoff=True,
    max_retries=3,
)
def send_telegram_notification(
    self,
    notification_job_id: int,
    background_job_id: int | None = None,
) -> dict:
    return NotificationDispatchService.send(
        notification_job_id,
        background_job_id,
    )
