from django.apps import apps as django_apps
from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from apps.boards.models import Board, BoardColumn, SystemType


class ColumnSettingsService:
    @staticmethod
    def get_default_board() -> Board:
        return Board.get_default()

    @staticmethod
    def active_columns(board: Board):
        return BoardColumn.objects.filter(
            board=board,
            is_active=True,
        ).order_by("position")

    @staticmethod
    @transaction.atomic
    def create_column(
        board: Board,
        *,
        name: str,
        color: str = "slate",
        wip_limit: int | None = None,
    ) -> BoardColumn:
        next_position = BoardColumn.objects.filter(
            board=board, is_active=True
        ).aggregate(
            max_position=Max("position"),
        )["max_position"]
        position = 0 if next_position is None else next_position + 1
        return BoardColumn.objects.create(
            board=board,
            name=name,
            system_type=SystemType.BACKLOG,
            color=color,
            position=position,
            wip_limit=wip_limit,
        )

    @staticmethod
    def update_column(
        column: BoardColumn,
        *,
        name: str | None = None,
        color: str | None = None,
        wip_limit: int | None = None,
        clear_wip_limit: bool = False,
    ) -> BoardColumn:
        fields: list[str] = []
        if name is not None:
            column.name = name
            fields.append("name")
        if color is not None:
            column.color = color
            fields.append("color")
        if clear_wip_limit:
            column.wip_limit = None
            fields.append("wip_limit")
        elif wip_limit is not None:
            column.wip_limit = wip_limit
            fields.append("wip_limit")
        if fields:
            fields.append("updated_at")
            column.save(update_fields=fields)
        return column

    @staticmethod
    @transaction.atomic
    def reorder(board: Board, column_ids: list[int]) -> list[BoardColumn]:
        active_columns = list(
            BoardColumn.objects.select_for_update()
            .filter(
                board=board,
                is_active=True,
            )
            .order_by("position"),
        )
        if len(column_ids) != len(active_columns):
            raise ValidationError("Reorder must include all active columns.")

        column_map = {column.id: column for column in active_columns}
        try:
            ordered = [column_map[column_id] for column_id in column_ids]
        except KeyError as exc:
            raise ValidationError("Column list is invalid.") from exc

        offset = len(ordered) + 100

        for index, column in enumerate(ordered):
            column.position = offset + index
            column.save(update_fields=["position", "updated_at"])

        for index, column in enumerate(ordered):
            column.position = index
            column.save(update_fields=["position", "updated_at"])

        return ordered

    @staticmethod
    def deactivate(column: BoardColumn) -> BoardColumn:
        if column.system_type == SystemType.DONE:
            raise ValidationError("Done column cannot be deactivated.")

        active_count = BoardColumn.objects.filter(
            board=column.board,
            is_active=True,
        ).count()
        if active_count <= 1:
            raise ValidationError("At least one active column is required.")

        if ColumnSettingsService._column_has_active_tasks(column.id):
            raise ValidationError(
                "Column has active tasks. Move tasks before deactivation.",
                code="column_has_tasks",
            )

        column.is_active = False
        column.save(update_fields=["is_active", "updated_at"])
        return column

    @staticmethod
    def _column_has_active_tasks(column_id: int) -> bool:
        if not django_apps.is_installed("apps.tasks"):
            return False

        task_model = django_apps.get_model("tasks", "Task")
        return task_model.objects.filter(
            column_id=column_id,
            archived_at__isnull=True,
        ).exists()
