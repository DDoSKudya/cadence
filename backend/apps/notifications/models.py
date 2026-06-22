from django.db import models


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class NotificationReason(models.TextChoices):
    OVERDUE = "overdue", "Overdue"
    STALE_IN_PROGRESS = "stale_in_progress", "Stale in progress"
    STALE_PLANNED = "stale_planned", "Stale planned"
    REMINDER = "reminder", "Reminder"
    MANUAL = "manual", "Manual"


class CallbackAction(models.TextChoices):
    TASK_DONE = "task_done", "Task done"
    TASK_IN_PROGRESS = "task_in_progress", "Task in progress"
    TASK_SNOOZE = "task_snooze", "Task snooze"
    TASK_CANCEL_REMINDERS = "task_cancel_reminders", "Cancel reminders"


class NotificationJob(models.Model):
    id: int
    task_id: int
    background_job_id: int | None

    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="notification_jobs",
    )
    background_job = models.ForeignKey(
        "jobs.BackgroundJob",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_jobs",
    )
    telegram_chat_id = models.CharField(max_length=80)
    message_text = models.TextField()
    message_id = models.CharField(max_length=80, blank=True, default="")
    status = models.CharField(
        max_length=40,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    reason = models.CharField(max_length=60, choices=NotificationReason.choices)
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    dedup_key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = (
            models.Index(
                fields=["status", "scheduled_at"],
                name="idx_notif_status_scheduled",
            ),
            models.Index(
                fields=["task", "-created_at"],
                name="idx_notif_task_created",
            ),
        )

    def __str__(self) -> str:
        return f"notification:{self.task_id}:{self.reason}"


class TelegramCallbackLog(models.Model):
    id: int
    task_id: int | None

    telegram_user_id = models.CharField(max_length=80)
    chat_id = models.CharField(max_length=80)
    callback_query_id = models.CharField(max_length=120, unique=True)
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_callbacks",
    )
    action = models.CharField(max_length=60, choices=CallbackAction.choices)
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.action}:{self.callback_query_id}"
