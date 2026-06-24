from django.db import models
from django.db.models import Q

from apps.common.i18n import t


class Board(models.Model):
    id: int
    active_scheme_id: int | None

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)
    active_scheme = models.ForeignKey(
        "BoardScheme",
        on_delete=models.PROTECT,
        related_name="boards",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = (
            models.UniqueConstraint(
                fields=["is_default"],
                condition=Q(is_default=True),
                name="uq_boards_single_default",
            ),
        )

    def __str__(self) -> str:
        return self.name

    @classmethod
    def get_default(cls) -> "Board":
        board, _created = cls.objects.get_or_create(
            slug="main",
            defaults={"name": t("defaults.boardName"), "is_default": True},
        )
        if not board.is_default:
            board.is_default = True
            board.save(update_fields=["is_default"])
        return board


class SystemType(models.TextChoices):
    BACKLOG = "backlog", "Backlog"
    PLANNED = "planned", "Planned"
    IN_PROGRESS = "in_progress", "In Progress"
    BLOCKED = "blocked", "Blocked"
    REVIEW = "review", "Review"
    READY = "ready", "Ready"
    DONE = "done", "Done"


class BoardScheme(models.Model):
    id: int

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class BoardSchemeColumn(models.Model):
    id: int
    scheme_id: int

    scheme = models.ForeignKey(
        BoardScheme,
        on_delete=models.CASCADE,
        related_name="columns",
    )
    name = models.CharField(max_length=100)
    system_type = models.CharField(max_length=20, choices=SystemType.choices)
    color = models.CharField(max_length=20, default="slate")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("position",)
        constraints = (
            models.UniqueConstraint(
                fields=["scheme", "position"],
                name="uq_board_scheme_column_position",
            ),
        )

    def __str__(self) -> str:
        return self.name


class BoardSchemeTransition(models.Model):
    id: int
    scheme_id: int

    scheme = models.ForeignKey(
        BoardScheme,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_position = models.PositiveIntegerField()
    to_position = models.PositiveIntegerField()

    class Meta:
        ordering = ("from_position", "to_position")
        constraints = (
            models.UniqueConstraint(
                fields=["scheme", "from_position", "to_position"],
                name="uq_board_scheme_transition_pair",
            ),
            models.CheckConstraint(
                condition=~Q(from_position=models.F("to_position")),
                name="chk_board_scheme_transition_distinct",
            ),
        )

    def __str__(self) -> str:
        return f"{self.from_position} -> {self.to_position}"


class BoardSchemeTaskStatus(models.Model):
    id: int
    scheme_id: int

    scheme = models.ForeignKey(
        BoardScheme,
        on_delete=models.CASCADE,
        related_name="task_statuses",
    )
    slug = models.SlugField(max_length=60)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default="slate")
    layout_x = models.FloatField(default=0)
    layout_y = models.FloatField(default=0)
    on_flow = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    is_initial = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)
    column_position = models.PositiveIntegerField(null=True, blank=True)
    rules = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("position", "name")
        constraints = (
            models.UniqueConstraint(
                fields=["scheme", "slug"],
                name="uq_board_scheme_task_status_slug",
            ),
        )

    def __str__(self) -> str:
        return self.name


class BoardSchemeTaskStatusTransition(models.Model):
    id: int
    scheme_id: int

    scheme = models.ForeignKey(
        BoardScheme,
        on_delete=models.CASCADE,
        related_name="task_status_transitions",
    )
    from_status_slug = models.SlugField(max_length=60)
    to_status_slug = models.SlugField(max_length=60)
    rules = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("from_status_slug", "to_status_slug")
        constraints = (
            models.UniqueConstraint(
                fields=["scheme", "from_status_slug", "to_status_slug"],
                name="uq_board_scheme_task_status_transition_pair",
            ),
            models.CheckConstraint(
                condition=~Q(from_status_slug=models.F("to_status_slug")),
                name="chk_board_scheme_task_status_transition_distinct",
            ),
        )

    def __str__(self) -> str:
        return f"{self.from_status_slug} -> {self.to_status_slug}"


class BoardColumn(models.Model):
    id: int
    board_id: int

    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=100)
    system_type = models.CharField(max_length=20, choices=SystemType.choices)
    task_status = models.ForeignKey(
        "TaskStatus",
        on_delete=models.SET_NULL,
        related_name="columns",
        null=True,
        blank=True,
    )
    color = models.CharField(max_length=20, default="slate")
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
    wip_limit = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position",)
        constraints = (
            models.CheckConstraint(
                condition=Q(position__gte=0),
                name="chk_board_columns_position_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(wip_limit__isnull=True) | Q(wip_limit__gt=0),
                name="chk_board_columns_wip_positive",
            ),
            models.UniqueConstraint(
                fields=["board", "position"],
                condition=Q(is_active=True),
                name="uq_board_columns_board_position_active",
            ),
        )
        indexes = (
            models.Index(
                fields=["board", "is_active", "position"],
                name="idx_bcol_board_act_pos",
            ),
            models.Index(
                fields=["system_type"],
                name="idx_board_columns_system_type",
            ),
        )

    def __str__(self) -> str:
        return self.name


class ColumnTransition(models.Model):
    id: int
    board_id: int
    from_column_id: int
    to_column_id: int

    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="column_transitions",
    )
    from_column = models.ForeignKey(
        BoardColumn,
        on_delete=models.CASCADE,
        related_name="outgoing_transitions",
    )
    to_column = models.ForeignKey(
        BoardColumn,
        on_delete=models.CASCADE,
        related_name="incoming_transitions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["from_column", "to_column"],
                name="uq_column_transition_pair",
            ),
            models.CheckConstraint(
                condition=~Q(from_column=models.F("to_column")),
                name="chk_column_transition_distinct",
            ),
        )
        indexes = (
            models.Index(
                fields=["board", "from_column"],
                name="idx_col_trans_board_from",
            ),
        )

    def __str__(self) -> str:
        return f"{self.from_column_id} -> {self.to_column_id}"


class TaskStatus(models.Model):
    id: int
    board_id: int

    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="task_statuses",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=60)
    color = models.CharField(max_length=20, default="slate")
    layout_x = models.FloatField(default=0)
    layout_y = models.FloatField(default=0)
    on_flow = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    is_initial = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)
    column = models.ForeignKey(
        BoardColumn,
        on_delete=models.SET_NULL,
        related_name="bound_statuses",
        null=True,
        blank=True,
    )
    rules = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "name")
        constraints = (
            models.UniqueConstraint(
                fields=["board", "slug"],
                name="uq_task_status_board_slug",
            ),
        )
        indexes = (
            models.Index(
                fields=["board", "position"], name="idx_task_status_board_pos"
            ),
        )

    def __str__(self) -> str:
        return self.name


class TaskStatusTransition(models.Model):
    id: int
    board_id: int
    from_status_id: int
    to_status_id: int

    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="task_status_transitions",
    )
    from_status = models.ForeignKey(
        TaskStatus,
        on_delete=models.CASCADE,
        related_name="outgoing_transitions",
    )
    to_status = models.ForeignKey(
        TaskStatus,
        on_delete=models.CASCADE,
        related_name="incoming_transitions",
    )
    rules = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["from_status", "to_status"],
                name="uq_task_status_transition_pair",
            ),
            models.CheckConstraint(
                condition=~Q(from_status=models.F("to_status")),
                name="chk_task_status_transition_distinct",
            ),
        )
        indexes = (
            models.Index(
                fields=["board", "from_status"],
                name="idx_task_stat_trans_board_from",
            ),
        )

    def __str__(self) -> str:
        return f"{self.from_status_id} -> {self.to_status_id}"
