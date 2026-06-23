from django.conf import settings
from django.db import models


class ExportType(models.TextChoices):
    TASKS = "tasks", "Tasks"
    ARCHIVE = "archive", "Archive"
    WEEKLY_SUMMARY = "weekly_summary", "Weekly summary"
    TAG_SUMMARY = "tag_summary", "Tag summary"
    NOTIFICATION_REPORT = "notification_report", "Notification report"
    JOBS_REPORT = "jobs_report", "Jobs report"
    IMPORTS_REPORT = "imports_report", "Imports report"


class FileFormat(models.TextChoices):
    CSV = "csv", "CSV"
    XLSX = "xlsx", "XLSX"


class ExportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class AnalyticsExportJob(models.Model):
    id: int
    background_job_id: int | None
    requested_by_id: int | None

    background_job = models.ForeignKey(
        "jobs.BackgroundJob",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_exports",
    )
    export_type = models.CharField(max_length=80, choices=ExportType.choices)
    file_format = models.CharField(max_length=20, choices=FileFormat.choices)
    status = models.CharField(
        max_length=40,
        choices=ExportStatus.choices,
        default=ExportStatus.PENDING,
    )
    filters = models.JSONField(default=dict, blank=True)
    file_path = models.TextField(blank=True, default="")
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    rows_count = models.PositiveIntegerField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_exports",
    )
    error_message = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = (
            models.Index(
                fields=["status", "-created_at"],
                name="idx_analytics_export_status",
            ),
            models.Index(
                fields=["expires_at"],
                name="idx_analytics_export_expires",
                condition=models.Q(expires_at__isnull=False),
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=models.Q(rows_count__isnull=True)
                | models.Q(rows_count__gte=0),
                name="chk_analytics_export_rows",
            ),
            models.CheckConstraint(
                condition=models.Q(file_size_bytes__isnull=True)
                | models.Q(file_size_bytes__gte=0),
                name="chk_analytics_export_size",
            ),
        )

    def __str__(self) -> str:
        return f"{self.export_type}:{self.status}"
