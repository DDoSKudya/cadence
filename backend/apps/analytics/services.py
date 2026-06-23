from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.analytics.constants import EXPORT_RETENTION_DAYS
from apps.analytics.exporters import export_report
from apps.analytics.filters import parse_filters_payload
from apps.analytics.models import (
    AnalyticsExportJob,
    ExportStatus,
    ExportType,
    FileFormat,
)
from apps.jobs.handlers import get_handler
from apps.jobs.models import JobType
from apps.jobs.services import JobService


class AnalyticsExportService:
    @staticmethod
    def create(
        *,
        export_type: str,
        file_format: str,
        filters: dict | None = None,
        requested_by=None,
    ) -> AnalyticsExportJob:
        export_type = str(export_type)
        file_format = str(file_format)
        valid_types = {choice for choice, _label in ExportType.choices}
        valid_formats = {choice for choice, _label in FileFormat.choices}
        if export_type not in valid_types:
            raise ValueError("Unsupported export type.")
        if file_format not in valid_formats:
            raise ValueError("Unsupported file format.")

        export_job = AnalyticsExportJob.objects.create(
            export_type=export_type,
            file_format=file_format,
            filters=filters or {},
            requested_by=requested_by,
        )
        background_job = JobService.create(
            JobType.ANALYTICS_EXPORT,
            {"export_id": export_job.id},
        )
        export_job.background_job = background_job
        export_job.save(update_fields=["background_job"])

        handler = get_handler(JobType.ANALYTICS_EXPORT)
        handler.dispatch(background_job)
        return export_job

    @staticmethod
    def run_export(export_id: int) -> dict:
        export_job = AnalyticsExportJob.objects.get(pk=export_id)
        export_job.status = ExportStatus.PROCESSING
        export_job.started_at = timezone.now()
        export_job.error_message = ""
        export_job.save(update_fields=["status", "started_at", "error_message"])

        try:
            relative_path, rows_count = export_report(export_job)
            absolute_path = Path(settings.MEDIA_ROOT) / relative_path
            file_size = absolute_path.stat().st_size if absolute_path.exists() else 0
            expires_at = timezone.now() + timedelta(days=EXPORT_RETENTION_DAYS)

            export_job.status = ExportStatus.SUCCEEDED
            export_job.file_path = str(relative_path)
            export_job.file_size_bytes = file_size
            export_job.rows_count = rows_count
            export_job.expires_at = expires_at
            export_job.finished_at = timezone.now()
            export_job.save(
                update_fields=[
                    "status",
                    "file_path",
                    "file_size_bytes",
                    "rows_count",
                    "expires_at",
                    "finished_at",
                ],
            )
        except Exception as exc:
            export_job.status = ExportStatus.FAILED
            export_job.error_message = str(exc)
            export_job.finished_at = timezone.now()
            export_job.save(
                update_fields=["status", "error_message", "finished_at"],
            )
            raise

        return {
            "export_id": export_job.id,
            "file_path": export_job.file_path,
            "rows_count": export_job.rows_count,
            "file_size_bytes": export_job.file_size_bytes,
        }

    @staticmethod
    def resolve_download_path(export_job: AnalyticsExportJob) -> Path:
        if not export_job.file_path:
            raise FileNotFoundError("Export file is not ready.")
        path = Path(settings.MEDIA_ROOT) / export_job.file_path
        if not path.exists():
            raise FileNotFoundError("Export file is missing.")
        return path

    @staticmethod
    def validate_filters_payload(filters: dict | None) -> dict:
        parse_filters_payload(filters)
        return filters or {}
