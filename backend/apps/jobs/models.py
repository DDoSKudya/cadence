from django.db import models


class JobType(models.TextChoices):
    JSON_INBOX_SCAN = "json_inbox_scan", "JSON inbox scan"
    JSON_IMPORT_FILE = "json_import_file", "JSON import file"
    NOTIFICATION_SCAN = "notification_scan", "Notification scan"
    TELEGRAM_SEND = "telegram_send", "Telegram send"
    TELEGRAM_CALLBACK = "telegram_callback", "Telegram callback"


class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class BackgroundJob(models.Model):
    id: int

    job_type = models.CharField(max_length=80, choices=JobType.choices)
    status = models.CharField(
        max_length=40,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
    )
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = (
            models.CheckConstraint(
                condition=models.Q(attempts__gte=0),
                name="chk_background_jobs_attempts",
            ),
            models.CheckConstraint(
                condition=models.Q(max_attempts__gt=0),
                name="chk_background_jobs_max_attempts",
            ),
        )
        indexes = (
            models.Index(
                fields=["status", "scheduled_at"],
                name="idx_jobs_status_scheduled",
            ),
            models.Index(
                fields=["job_type", "-created_at"],
                name="idx_jobs_type_created",
            ),
            models.Index(
                fields=["celery_task_id"],
                name="idx_jobs_celery_task_id",
            ),
        )

    def __str__(self) -> str:
        return f"{self.job_type} ({self.status})"
