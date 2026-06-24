from django.apps import apps as django_apps
from django.db import transaction
from django.db.models import Max, Q
from rest_framework.exceptions import ValidationError

from apps.boards.constants import MAX_BOARD_COLUMNS
from apps.boards.models import Board, BoardColumn, ColumnTransition, SystemType
from apps.boards.scheme_services import BoardSchemeService


class ColumnSettingsService:
    @staticmethod
    def get_default_board() -> Board:
        board = Board.get_default()
        BoardSchemeService.ensure_board_columns(board)
        return board

    @staticmethod
    def active_columns(board: Board):
        return BoardColumn.objects.filter(
            board=board,
            is_active=True,
        ).order_by("position")

    @staticmethod
    def assert_can_create_column(board: Board) -> None:
        active_count = BoardColumn.objects.filter(board=board, is_active=True).count()
        if active_count >= MAX_BOARD_COLUMNS:
            raise ValidationError(
                "Column limit reached.",
                code="column_limit",
            )

    @staticmethod
    @transaction.atomic
    def create_column(
        board: Board,
        *,
        name: str,
        color: str = "slate",
        wip_limit: int | None = None,
        system_type: str = SystemType.BACKLOG,
    ) -> BoardColumn:
        BoardSchemeService.assert_board_mutable(board)
        ColumnSettingsService.assert_can_create_column(board)
        next_position = BoardColumn.objects.filter(
            board=board, is_active=True
        ).aggregate(
            max_position=Max("position"),
        )["max_position"]
        position = 0 if next_position is None else next_position + 1
        column = BoardColumn.objects.create(
            board=board,
            name=name,
            system_type=system_type,
            color=color,
            position=position,
            wip_limit=wip_limit,
        )
        BoardSchemeService.sync_templates_from_board(board)
        return column

    @staticmethod
    def update_column(
        column: BoardColumn,
        *,
        name: str | None = None,
        color: str | None = None,
        wip_limit: int | None = None,
        clear_wip_limit: bool = False,
        system_type: str | None = None,
        task_status_ids: list[int] | None = None,
    ) -> BoardColumn:
        BoardSchemeService.assert_column_mutable(column)
        fields: list[str] = []
        if name is not None:
            column.name = name
            fields.append("name")
        if color is not None:
            column.color = color
            fields.append("color")
        if system_type is not None:
            if column.system_type == SystemType.DONE and system_type != SystemType.DONE:
                raise ValidationError("Done column status cannot be changed.")
            column.system_type = system_type
            fields.append("system_type")
        if clear_wip_limit:
            column.wip_limit = None
            fields.append("wip_limit")
        elif wip_limit is not None:
            column.wip_limit = wip_limit
            fields.append("wip_limit")
        if fields:
            fields.append("updated_at")
            column.save(update_fields=fields)
        if task_status_ids is not None:
            from apps.boards.task_status_services import TaskStatusService

            TaskStatusService.sync_column_bindings(column, task_status_ids)
            TaskStatusService.sync_graph_to_scheme(column.board)
        BoardSchemeService.sync_templates_from_board(column.board)
        return column

    @staticmethod
    @transaction.atomic
    def reorder(board: Board, column_ids: list[int]) -> list[BoardColumn]:
        BoardSchemeService.assert_board_mutable(board)
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

        BoardSchemeService.sync_templates_from_board(board)
        BoardSchemeService.sync_transitions_from_board(board)
        from apps.boards.task_status_services import TaskStatusService

        TaskStatusService.sync_graph_to_scheme(board)
        return ordered

    @staticmethod
    def deactivate(column: BoardColumn) -> BoardColumn:
        BoardSchemeService.assert_column_mutable(column)
        if column.system_type == SystemType.DONE:
            raise ValidationError("Done column cannot be deactivated.")

        active_count = BoardColumn.objects.filter(
            board=column.board,
            is_active=True,
        ).count()
        if active_count <= 1 and BoardSchemeService.is_board_locked(column.board):
            raise ValidationError("At least one active column is required.")

        if ColumnSettingsService._column_has_active_tasks(column.id):
            raise ValidationError(
                "Column has active tasks. Move tasks before deactivation.",
                code="column_has_tasks",
            )

        column.is_active = False
        column.save(update_fields=["is_active", "updated_at"])
        ColumnWorkflowService.remove_transitions_for_column(column)
        BoardSchemeService.sync_templates_from_board(column.board)
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


class ColumnWorkflowService:
    @staticmethod
    def is_enforced(board: Board) -> bool:
        return ColumnTransition.objects.filter(board=board).exists()

    @staticmethod
    def get_transitions(board: Board) -> list[dict[str, int]]:
        return [
            {
                "from_column_id": transition.from_column_id,
                "to_column_id": transition.to_column_id,
            }
            for transition in ColumnTransition.objects.filter(board=board).order_by(
                "from_column_id",
                "to_column_id",
            )
        ]

    @staticmethod
    def get_workflow(board: Board) -> dict[str, object]:
        return {
            "enforced": ColumnWorkflowService.is_enforced(board),
            "transitions": ColumnWorkflowService.get_transitions(board),
        }

    @staticmethod
    @transaction.atomic
    def set_transitions(
        board: Board,
        transitions: list[dict[str, int]],
    ) -> dict[str, object]:
        BoardSchemeService.assert_board_mutable(board)
        active_ids = set(
            BoardColumn.objects.filter(board=board, is_active=True).values_list(
                "id",
                flat=True,
            ),
        )
        normalized: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()

        for item in transitions:
            from_id = item["from_column_id"]
            to_id = item["to_column_id"]
            if from_id == to_id:
                raise ValidationError("Column cannot transition to itself.")
            if from_id not in active_ids or to_id not in active_ids:
                raise ValidationError("Transition references an invalid column.")

            pair = (from_id, to_id)
            if pair in seen:
                continue
            seen.add(pair)
            normalized.append(pair)

        ColumnTransition.objects.filter(board=board).delete()
        ColumnTransition.objects.bulk_create(
            [
                ColumnTransition(
                    board=board,
                    from_column_id=from_id,
                    to_column_id=to_id,
                )
                for from_id, to_id in normalized
            ],
        )
        BoardSchemeService.sync_transitions_from_board(board)
        return ColumnWorkflowService.get_workflow(board)

    @staticmethod
    def remove_transitions_for_column(column: BoardColumn) -> None:
        ColumnTransition.objects.filter(
            board=column.board,
        ).filter(
            Q(from_column=column) | Q(to_column=column),
        ).delete()

    @staticmethod
    def is_move_allowed(
        *,
        board: Board,
        from_column_id: int,
        to_column_id: int,
    ) -> bool:
        if from_column_id == to_column_id:
            return True
        if not ColumnWorkflowService.is_enforced(board):
            return True
        return ColumnTransition.objects.filter(
            board=board,
            from_column_id=from_column_id,
            to_column_id=to_column_id,
        ).exists()
