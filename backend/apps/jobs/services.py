from django.utils import timezone

from apps.jobs.exceptions import JobCancelError, JobRetryError
from apps.jobs.handlers import get_handler
from apps.jobs.models import BackgroundJob, JobStatus


class JobService:
    @staticmethod
    def create(job_type: str, payload: dict | None = None) -> BackgroundJob:
        return BackgroundJob.objects.create(
            job_type=job_type,
            payload=payload or {},
        )

    @staticmethod
    def mark_processing(
        job: BackgroundJob,
        *,
        celery_task_id: str = "",
    ) -> BackgroundJob:
        now = timezone.now()
        job.status = JobStatus.PROCESSING
        job.started_at = now
        job.finished_at = None
        job.attempts += 1
        if celery_task_id:
            job.celery_task_id = celery_task_id
        job.save(
            update_fields=[
                "status",
                "started_at",
                "finished_at",
                "attempts",
                "celery_task_id",
                "updated_at",
            ],
        )
        return job

    @staticmethod
    def succeed(job: BackgroundJob, result: dict | None = None) -> BackgroundJob:
        job.status = JobStatus.SUCCEEDED
        job.result = result or {}
        job.last_error = ""
        job.finished_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "result",
                "last_error",
                "finished_at",
                "updated_at",
            ],
        )
        return job

    @staticmethod
    def fail(job: BackgroundJob, error_message: str) -> BackgroundJob:
        job.status = JobStatus.FAILED
        job.last_error = error_message
        job.finished_at = timezone.now()
        job.save(
            update_fields=["status", "last_error", "finished_at", "updated_at"],
        )
        return job

    @staticmethod
    def cancel(job: BackgroundJob) -> BackgroundJob:
        if job.status != JobStatus.PENDING:
            raise JobCancelError("Only pending jobs can be cancelled.")

        job.status = JobStatus.CANCELLED
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at", "updated_at"])
        return job


class JobRetryService:
    @staticmethod
    def retry(job: BackgroundJob) -> BackgroundJob:
        if job.status != JobStatus.FAILED:
            raise JobRetryError("Only failed jobs can be retried.")

        if job.attempts >= job.max_attempts:
            raise JobRetryError("Maximum retry attempts reached.")

        job.status = JobStatus.PENDING
        job.last_error = ""
        job.finished_at = None
        job.save(
            update_fields=["status", "last_error", "finished_at", "updated_at"],
        )

        handler = get_handler(job.job_type)
        handler.dispatch(job)
        job.refresh_from_db()
        return job
