from celery import shared_task
from django.db.utils import DatabaseError, OperationalError

from apps.analytics.services import AnalyticsExportService
from apps.jobs.models import BackgroundJob
from apps.jobs.services import JobService


@shared_task(
    name="apps.analytics.tasks.run_analytics_export",
    bind=True,
    queue="reports",
    autoretry_for=(OperationalError, DatabaseError),
    retry_backoff=True,
    max_retries=3,
)
def run_analytics_export(self, job_id: int) -> dict:
    job = BackgroundJob.objects.get(pk=job_id)
    JobService.mark_processing(job, celery_task_id=self.request.id)

    export_id = job.payload.get("export_id")
    if export_id is None:
        JobService.fail(job, "export_id is missing from payload")
        raise ValueError("export_id is missing from payload")

    try:
        result = AnalyticsExportService.run_export(int(export_id))
    except Exception as exc:
        JobService.fail(job, str(exc))
        raise

    JobService.succeed(job, result)
    return result
