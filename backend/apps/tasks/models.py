from django.conf import settings
from django.db import models
from django.db.models import Q


class TaskSource(models.TextChoices):
    UI = "ui", "UI"
    API = "api", "API"
    JSON_IMPORT = "json_import", "JSON import"
    TELEGRAM = "telegram", "Telegram"
    SYSTEM = "system", "System"


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"


class TaskEventType(models.TextChoices):
    CREATED = "created", "Created"
    UPDATED = "updated", "Updated"
    MOVED = "moved", "Moved"
    CLOSED = "closed", "Closed"
    ARCHIVED = "archived", "Archived"
    REOPENED = "reopened", "Reopened"
    REMINDER_SCHEDULED = "reminder_scheduled", "Reminder scheduled"
    NOTIFICATION_SENT = "notification_sent", "Notification sent"
    TELEGRAM_ACTION = "telegram_action", "Telegram action"
    IMPORTED = "imported", "Imported"


class ActorType(models.TextChoices):
    USER = "user", "User"
    API = "api", "API"
    IMPORT = "import", "Import"
    TELEGRAM = "telegram", "Telegram"
    SYSTEM = "system", "System"


class Task(models.Model):
    id: int
    board_id: int
    column_id: int
    week_id: int | None

    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    board = models.ForeignKey(
        "boards.Board",
        on_delete=models.RESTRICT,
        related_name="tasks",
    )
    column = models.ForeignKey(
        "boards.BoardColumn",
        on_delete=models.RESTRICT,
        related_name="tasks",
    )
    week = models.ForeignKey(
        "weeks.Week",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    position = models.PositiveIntegerField(default=0)
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.NORMAL,
    )
    column_entered_at = models.DateTimeField()
    due_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(
        max_length=40,
        choices=TaskSource.choices,
        default=TaskSource.UI,
    )
    external_ref = models.CharField(max_length=240, blank=True, default="")
    evidence_url = models.TextField(blank=True, default="")
    completion_note = models.TextField(blank=True, default="")
    reminder_enabled = models.BooleanField(default=True)
    next_reminder_at = models.DateTimeField(null=True, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    reminder_interval_minutes = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    tags: models.ManyToManyField = models.ManyToManyField(
        "core.Tag",
        through="TaskTag",
        related_name="tasks",
    )

    class Meta:
        ordering = ("column_id", "position")
        constraints = (
            models.CheckConstraint(
                condition=~Q(title=""),
                name="chk_tasks_title_not_blank",
            ),
            models.CheckConstraint(
                condition=Q(position__gte=0),
                name="chk_tasks_position_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(reminder_interval_minutes__isnull=True)
                | Q(reminder_interval_minutes__gt=0),
                name="chk_tasks_reminder_interval_positive",
            ),
            models.CheckConstraint(
                condition=Q(archived_at__isnull=True) | Q(closed_at__isnull=False),
                name="chk_tasks_archive_after_close",
            ),
        )
        indexes = (
            models.Index(
                fields=["board", "column", "position"],
                condition=Q(archived_at__isnull=True),
                name="idx_task_brd_col_pos_act",
            ),
            models.Index(
                fields=["week", "archived_at", "column", "position"],
                name="idx_tasks_week_active",
            ),
            models.Index(
                fields=["archived_at", "-closed_at"],
                condition=Q(archived_at__isnull=False),
                name="idx_tasks_archived_closed",
            ),
            models.Index(
                fields=["due_at"],
                condition=Q(archived_at__isnull=True, due_at__isnull=False),
                name="idx_tasks_due_active",
            ),
            models.Index(
                fields=["next_reminder_at"],
                condition=Q(
                    archived_at__isnull=True,
                    reminder_enabled=True,
                    next_reminder_at__isnull=False,
                ),
                name="idx_tasks_next_reminder",
            ),
            models.Index(
                fields=["source", "created_at"],
                name="idx_tasks_source_created",
            ),
            models.Index(
                fields=["column", "column_entered_at"],
                condition=Q(archived_at__isnull=True),
                name="idx_task_col_entered_act",
            ),
        )

    def __str__(self) -> str:
        return self.title


class TaskTag(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    tag = models.ForeignKey("core.Tag", on_delete=models.CASCADE)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["task", "tag"],
                name="uq_task_tags_task_tag",
            ),
        )
        indexes = (models.Index(fields=["tag", "task"], name="idx_task_tags_tag_task"),)


class TaskEvent(models.Model):
    task_id: int

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=60, choices=TaskEventType.choices)
    actor_type = models.CharField(max_length=40, choices=ActorType.choices)
    actor_id = models.CharField(max_length=120, blank=True, default="")
    source = models.CharField(max_length=40, choices=TaskSource.choices)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = (
            models.Index(
                fields=["task", "-created_at"],
                name="idx_task_events_task_created",
            ),
            models.Index(
                fields=["event_type", "-created_at"],
                name="idx_task_events_type_created",
            ),
        )

    def __str__(self) -> str:
        return f"{self.task_id}:{self.event_type}"
