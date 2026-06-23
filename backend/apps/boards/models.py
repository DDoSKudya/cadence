from django.db import models
from django.db.models import Q

from apps.common.i18n import t


class Board(models.Model):
    id: int

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)
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
    DONE = "done", "Done"


class BoardColumn(models.Model):
    id: int
    board_id: int

    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=100)
    system_type = models.CharField(max_length=20, choices=SystemType.choices)
    color = models.CharField(max_length=20, default="slate")
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
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
