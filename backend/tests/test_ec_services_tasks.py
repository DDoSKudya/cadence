from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from apps.analytics.models import (
    AnalyticsExportJob,
    ExportStatus,
    ExportType,
    FileFormat,
)
from apps.analytics.services import AnalyticsExportService
from apps.analytics.tasks import run_analytics_export
from apps.imports.job_handlers import JsonImportFileHandler, JsonInboxScanHandler
from apps.imports.models import ImportLog, ImportStatus
from apps.imports.services import ImportProcessResult
from apps.imports.tasks import scan_json_inbox
from apps.jobs.models import BackgroundJob, JobStatus, JobType
from apps.jobs.services import JobService
from apps.notifications.job_handlers import NotificationScanHandler, TelegramSendHandler


@pytest.mark.django_db
def test_analytics_ec_export_service_run_export_succeeds(
    media_root, planned_column, api_client
):
    from conftest import create_task_via_api

    create_task_via_api(api_client, title="Export svc", column_id=planned_column.id)
    export_job = AnalyticsExportJob.objects.create(
        export_type=ExportType.TASKS,
        file_format=FileFormat.CSV,
        filters={},
    )
    result = AnalyticsExportService.run_export(export_job.id)
    export_job.refresh_from_db()
    assert export_job.status == ExportStatus.SUCCEEDED
    assert result["rows_count"] >= 1
    path = AnalyticsExportService.resolve_download_path(export_job)
    assert path.exists()


@pytest.mark.django_db
def test_analytics_ec_export_service_run_export_failure_marks_failed(media_root):
    export_job = AnalyticsExportJob.objects.create(
        export_type=ExportType.TASKS,
        file_format=FileFormat.CSV,
        filters={},
    )
    with (
        patch(
            "apps.analytics.services.export_report",
            side_effect=RuntimeError("export failed"),
        ),
        pytest.raises(RuntimeError),
    ):
        AnalyticsExportService.run_export(export_job.id)
    export_job.refresh_from_db()
    assert export_job.status == ExportStatus.FAILED
    assert "export failed" in export_job.error_message


@pytest.mark.django_db
def test_analytics_ec_export_service_invalid_format_rejected():
    with pytest.raises(ValueError, match="file format"):
        AnalyticsExportService.create(
            export_type=ExportType.TASKS,
            file_format="pdf",
            filters={},
        )


@pytest.mark.django_db
def test_analytics_ec_export_service_create_dispatches_job(media_root):
    with patch("apps.analytics.job_handlers.run_analytics_export.delay"):
        export_job = AnalyticsExportService.create(
            export_type=ExportType.TASKS,
            file_format=FileFormat.CSV,
            filters={},
        )
    assert export_job.background_job is not None
    assert export_job.background_job.job_type == JobType.ANALYTICS_EXPORT


@pytest.mark.django_db
def test_analytics_ec_export_resolve_download_missing_file_raises(media_root):
    export_job = AnalyticsExportJob.objects.create(
        export_type=ExportType.TASKS,
        file_format=FileFormat.CSV,
        status=ExportStatus.SUCCEEDED,
        file_path="exports/analytics/missing.csv",
        filters={},
    )
    with pytest.raises(FileNotFoundError):
        AnalyticsExportService.resolve_download_path(export_job)


@pytest.mark.django_db
def test_analytics_ec_run_export_task_happy_path(
    media_root, planned_column, api_client
):
    from conftest import create_task_via_api

    create_task_via_api(api_client, title="Celery export", column_id=planned_column.id)
    export_job = AnalyticsExportJob.objects.create(
        export_type=ExportType.TASKS,
        file_format=FileFormat.CSV,
        filters={},
    )
    job = JobService.create(JobType.ANALYTICS_EXPORT, {"export_id": export_job.id})
    result = run_analytics_export.run(job.id)
    job.refresh_from_db()
    assert job.status == JobStatus.SUCCEEDED
    assert result["export_id"] == export_job.id


@pytest.mark.django_db
def test_analytics_ec_run_export_task_missing_export_id_fails():
    job = JobService.create(JobType.ANALYTICS_EXPORT, {})
    with pytest.raises(ValueError):
        run_analytics_export.run(job.id)
    job.refresh_from_db()
    assert job.status == JobStatus.FAILED


@pytest.mark.django_db
def test_imports_ec_scan_json_inbox_task_succeeds(inbox_dirs):
    job = JobService.create(JobType.JSON_INBOX_SCAN, {})
    processed = scan_json_inbox.run(job.id)
    job.refresh_from_db()
    assert job.status == JobStatus.SUCCEEDED
    assert processed >= 0


@pytest.mark.django_db
def test_imports_ec_scan_json_inbox_task_without_job_id_creates_job(inbox_dirs):
    scan_json_inbox.run()
    assert BackgroundJob.objects.filter(job_type=JobType.JSON_INBOX_SCAN).exists()


@pytest.mark.django_db
def test_imports_ec_job_handlers_dispatch_with_patch():
    inbox_job = JobService.create(JobType.JSON_INBOX_SCAN, {})
    file_job = JobService.create(JobType.JSON_IMPORT_FILE, {"filename": "x.json"})
    import_log = ImportLog.objects.create(
        filename="x.json",
        status=ImportStatus.SUCCEEDED,
        idempotency_key="handler-key",
    )
    result = ImportProcessResult(import_log=import_log)
    with (
        patch("apps.imports.tasks.scan_json_inbox.delay") as scan_delay,
        patch.object(
            JsonImportFileHandler,
            "_execute",
            return_value=result,
        ),
    ):
        JsonInboxScanHandler().dispatch(inbox_job)
        JsonImportFileHandler().dispatch(file_job)
    scan_delay.assert_called_once()
    file_job.refresh_from_db()
    assert file_job.status == JobStatus.SUCCEEDED


@pytest.mark.django_db
def test_notifications_ec_job_handlers_dispatch_with_patch():
    scan_job = JobService.create(JobType.NOTIFICATION_SCAN, {})
    send_job = JobService.create(
        JobType.TELEGRAM_SEND,
        {"notification_job_id": 1},
    )
    with (
        patch("apps.notifications.tasks.scan_reminders.delay") as scan_delay,
        patch(
            "apps.notifications.tasks.send_telegram_notification.delay"
        ) as send_delay,
    ):
        NotificationScanHandler().dispatch(scan_job)
        TelegramSendHandler().dispatch(send_job)
    scan_delay.assert_called_once()
    send_delay.assert_called_once()


@pytest.mark.django_db
def test_jobs_ec_detail_retry_cancel_api(api_client):
    job = JobService.create(JobType.JSON_INBOX_SCAN, {})
    JobService.mark_processing(job, celery_task_id="x")
    JobService.fail(job, "boom")

    detail = api_client.get(reverse("job-detail", args=[job.id]))
    assert detail.status_code == 200

    with patch("apps.jobs.services.get_handler") as get_handler:
        handler = MagicMock()
        get_handler.return_value = handler
        retried = api_client.post(reverse("job-retry", args=[job.id]))
    assert retried.status_code == 200

    pending = JobService.create(JobType.JSON_INBOX_SCAN, {})
    cancelled = api_client.post(reverse("job-cancel", args=[pending.id]))
    assert cancelled.status_code == 200
    pending.refresh_from_db()
    assert pending.status == JobStatus.CANCELLED


@pytest.mark.django_db
def test_analytics_ec_export_api_create(media_root, api_client):
    with patch("apps.analytics.job_handlers.run_analytics_export.delay"):
        response = api_client.post(
            reverse("analytics-export-list"),
            {
                "export_type": ExportType.TASKS,
                "file_format": FileFormat.CSV,
                "filters": {},
            },
            content_type="application/json",
        )
    assert response.status_code == 201
    assert AnalyticsExportJob.objects.filter(export_type=ExportType.TASKS).exists()
