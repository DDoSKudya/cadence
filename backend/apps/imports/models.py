from django.db import models


class ImportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    SKIPPED_DUPLICATE = "skipped_duplicate", "Skipped duplicate"


class ImportLog(models.Model):
    id: int

    filename = models.CharField(max_length=255)
    original_path = models.TextField()
    checksum = models.CharField(max_length=128)
    idempotency_key = models.CharField(max_length=180, null=True, blank=True)
    schema_version = models.CharField(max_length=20, default="")
    source_label = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=40,
        choices=ImportStatus.choices,
        default=ImportStatus.PENDING,
    )
    tasks_created = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = (
            models.CheckConstraint(
                condition=models.Q(tasks_created__gte=0),
                name="chk_import_logs_tasks_created",
            ),
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="uq_import_logs_idempotency_key",
            ),
            models.UniqueConstraint(
                fields=["checksum"],
                condition=models.Q(
                    status__in=[
                        ImportStatus.SUCCEEDED,
                        ImportStatus.SKIPPED_DUPLICATE,
                    ],
                ),
                name="uq_import_logs_success_checksum",
            ),
        )
        indexes = (
            models.Index(
                fields=["status", "-created_at"],
                name="idx_import_logs_status_created",
            ),
        )

    def __str__(self) -> str:
        return f"{self.filename} ({self.status})"
