from celery import shared_task
from django.db.utils import DatabaseError, OperationalError

from apps.imports.services import JsonImportService
from apps.jobs.models import BackgroundJob, JobType
from apps.jobs.services import JobService


@shared_task(
    name="apps.imports.tasks.scan_json_inbox",
    bind=True,
    queue="imports",
    autoretry_for=(OperationalError, DatabaseError),
    retry_backoff=True,
    max_retries=3,
)
def scan_json_inbox(self, job_id: int | None = None) -> int:
    if job_id is not None:
        job = BackgroundJob.objects.get(pk=job_id)
    else:
        job = JobService.create(JobType.JSON_INBOX_SCAN, {})

    JobService.mark_processing(job, celery_task_id=self.request.id)

    try:
        processed = JsonImportService.scan_inbox()
    except Exception as exc:
        JobService.fail(job, str(exc))
        raise

    JobService.succeed(job, {"processed": processed})
    return processed
