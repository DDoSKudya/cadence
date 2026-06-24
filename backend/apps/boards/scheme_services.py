from typing import TypedDict

from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.boards.constants import MAX_BOARD_SCHEMES
from apps.boards.models import (
    Board,
    BoardColumn,
    BoardScheme,
    BoardSchemeColumn,
    BoardSchemeTransition,
    ColumnTransition,
    SystemType,
)
from apps.common.i18n import t

DEFAULT_SCHEME_SLUG = "default"


class SchemeColumnDef(TypedDict):
    position: int
    name: str
    system_type: SystemType
    color: str


def _task_status_service():
    from apps.boards.task_status_services import TaskStatusService

    return TaskStatusService


def default_scheme_column_defs() -> tuple[SchemeColumnDef, ...]:
    return (
        {
            "position": 0,
            "name": t("defaults.column.backlog"),
            "system_type": SystemType.BACKLOG,
            "color": "slate",
        },
        {
            "position": 1,
            "name": t("defaults.column.inProgress"),
            "system_type": SystemType.IN_PROGRESS,
            "color": "amber",
        },
        {
            "position": 2,
            "name": t("defaults.column.ready"),
            "system_type": SystemType.READY,
            "color": "green",
        },
    )


DEFAULT_SCHEME_TRANSITIONS: tuple[tuple[str, str], ...] = (
    (SystemType.BACKLOG, SystemType.IN_PROGRESS),
    (SystemType.IN_PROGRESS, SystemType.READY),
)


class BoardSchemeService:
    @staticmethod
    def list_schemes() -> list[BoardScheme]:
        return list(BoardScheme.objects.order_by("name"))

    @staticmethod
    def get_scheme(slug: str) -> BoardScheme:
        scheme = BoardScheme.objects.filter(slug=slug).first()
        if scheme is None:
            raise ValidationError("Board scheme is invalid.")
        return scheme

    @staticmethod
    def get_active_scheme(board: Board) -> BoardScheme | None:
        if board.active_scheme_id is None:
            return None
        return board.active_scheme

    @staticmethod
    def is_board_locked(board: Board) -> bool:
        scheme = BoardSchemeService.get_active_scheme(board)
        return bool(scheme and scheme.is_locked)

    @staticmethod
    def _unique_slug(name: str) -> str:
        base = slugify(name) or "scheme"
        slug = base[:50]
        if not BoardScheme.objects.filter(slug=slug).exists():
            return slug

        index = 2
        while True:
            candidate = f"{base[:45]}-{index}"
            if not BoardScheme.objects.filter(slug=candidate).exists():
                return candidate
            index += 1

    @staticmethod
    def assert_can_create_scheme() -> None:
        if BoardScheme.objects.count() >= MAX_BOARD_SCHEMES:
            raise ValidationError(
                "Board scheme limit reached.",
                code="scheme_limit",
            )

    @staticmethod
    @transaction.atomic
    def create_custom_scheme(*, name: str, description: str = "") -> BoardScheme:
        trimmed = name.strip()
        if not trimmed:
            raise ValidationError("Scheme name is required.")

        BoardSchemeService.assert_can_create_scheme()

        return BoardScheme.objects.create(
            slug=BoardSchemeService._unique_slug(trimmed),
            name=trimmed,
            description=description.strip(),
            is_locked=False,
        )

    @staticmethod
    def sync_templates_from_board(board: Board) -> None:
        scheme = BoardSchemeService.get_active_scheme(board)
        if scheme is None or scheme.is_locked:
            return

        BoardSchemeColumn.objects.filter(scheme=scheme).delete()
        active_columns = BoardColumn.objects.filter(
            board=board,
            is_active=True,
        ).order_by("position")
        BoardSchemeColumn.objects.bulk_create(
            [
                BoardSchemeColumn(
                    scheme=scheme,
                    name=column.name,
                    system_type=column.system_type,
                    color=column.color,
                    position=column.position,
                )
                for column in active_columns
            ],
        )

    @staticmethod
    def sync_transitions_from_board(
        board: Board,
        *,
        scheme: BoardScheme | None = None,
    ) -> None:
        scheme = scheme or BoardSchemeService.get_active_scheme(board)
        if scheme is None or scheme.is_locked:
            return

        positions = {
            column.id: column.position
            for column in BoardColumn.objects.filter(board=board, is_active=True)
        }

        BoardSchemeTransition.objects.filter(scheme=scheme).delete()

        pairs: set[tuple[int, int]] = set()
        for transition in ColumnTransition.objects.filter(board=board).order_by(
            "from_column_id",
            "to_column_id",
        ):
            from_position = positions.get(transition.from_column_id)
            to_position = positions.get(transition.to_column_id)
            if (
                from_position is None
                or to_position is None
                or from_position == to_position
            ):
                continue
            pairs.add((from_position, to_position))

        if not pairs:
            return

        BoardSchemeTransition.objects.bulk_create(
            [
                BoardSchemeTransition(
                    scheme=scheme,
                    from_position=from_position,
                    to_position=to_position,
                )
                for from_position, to_position in sorted(pairs)
            ],
        )

    @staticmethod
    def ensure_default_scheme() -> BoardScheme:
        scheme, created = BoardScheme.objects.get_or_create(
            slug=DEFAULT_SCHEME_SLUG,
            defaults={
                "name": t("defaults.scheme.defaultName"),
                "description": t("defaults.scheme.defaultDescription"),
                "is_locked": True,
            },
        )
        if created or not scheme.columns.exists():
            BoardSchemeService._seed_scheme_columns(scheme)
        return scheme

    @staticmethod
    def _seed_scheme_columns(scheme: BoardScheme) -> None:
        for column in default_scheme_column_defs():
            BoardSchemeColumn.objects.update_or_create(
                scheme=scheme,
                system_type=column["system_type"],
                defaults={
                    "name": column["name"],
                    "color": column["color"],
                    "position": column["position"],
                },
            )

    @staticmethod
    @transaction.atomic
    def apply_scheme(
        board: Board,
        scheme: BoardScheme,
        *,
        delete_tasks: bool = False,
    ) -> list[BoardColumn]:
        if delete_tasks:
            BoardSchemeService._delete_board_tasks(board)

        old_scheme = board.active_scheme
        if old_scheme and not old_scheme.is_locked:
            BoardSchemeService.sync_templates_from_board(board)
            BoardSchemeService.sync_transitions_from_board(board, scheme=old_scheme)
            TaskStatusService = _task_status_service()
            TaskStatusService.sync_graph_to_scheme(board, scheme=old_scheme)

        ColumnTransition.objects.filter(board=board).delete()
        TaskStatusService = _task_status_service()

        TaskStatusService.clear_board_graph(board)
        BoardColumn.objects.filter(board=board).delete()

        templates = list(scheme.columns.order_by("position"))
        if not templates:
            if scheme.is_locked:
                raise ValidationError("Board scheme has no columns.")
            board.active_scheme = scheme
            board.save(update_fields=["active_scheme", "updated_at"])
            TaskStatusService.seed_starter_graph(board)
            return []

        columns_by_type: dict[str, BoardColumn] = {}
        created_columns: list[BoardColumn] = []
        for template in templates:
            column = BoardColumn.objects.create(
                board=board,
                name=template.name,
                system_type=template.system_type,
                color=template.color,
                position=template.position,
                is_locked=scheme.is_locked,
            )
            columns_by_type[column.system_type] = column
            created_columns.append(column)

        board.active_scheme = scheme
        board.save(update_fields=["active_scheme", "updated_at"])

        BoardSchemeService._apply_scheme_transitions(board, created_columns, scheme)
        return created_columns

    @staticmethod
    def _apply_scheme_transitions(
        board: Board,
        created_columns: list[BoardColumn],
        scheme: BoardScheme,
    ) -> None:
        TaskStatusService = _task_status_service()

        columns_by_type = {column.system_type: column for column in created_columns}
        position_to_column = {column.position: column for column in created_columns}

        template_pairs = list(
            BoardSchemeTransition.objects.filter(scheme=scheme)
            .values_list("from_position", "to_position")
            .order_by("from_position", "to_position"),
        )
        if scheme.slug == DEFAULT_SCHEME_SLUG and not template_pairs:
            template_pairs = [
                (from_column.position, to_column.position)
                for from_type, to_type in DEFAULT_SCHEME_TRANSITIONS
                for from_column in [columns_by_type.get(from_type)]
                for to_column in [columns_by_type.get(to_type)]
                if from_column is not None and to_column is not None
            ]

        transitions: list[ColumnTransition] = []
        for from_position, to_position in template_pairs:
            from_column = position_to_column.get(from_position)
            to_column = position_to_column.get(to_position)
            if from_column is None or to_column is None:
                continue
            transitions.append(
                ColumnTransition(
                    board=board,
                    from_column=from_column,
                    to_column=to_column,
                ),
            )
        if transitions:
            ColumnTransition.objects.bulk_create(transitions)

        TaskStatusService.apply_graph_from_scheme(
            board,
            scheme,
            position_to_column=position_to_column,
            columns_by_type=columns_by_type,
        )

    @staticmethod
    @transaction.atomic
    def switch_scheme(board: Board, slug: str) -> Board:
        scheme = BoardSchemeService.get_scheme(slug)
        BoardSchemeService.apply_scheme(board, scheme, delete_tasks=True)
        return board

    @staticmethod
    def ensure_board_columns(board: Board) -> None:
        active_count = BoardColumn.objects.filter(board=board, is_active=True).count()
        if active_count > 0:
            return

        scheme = board.active_scheme
        if scheme is None:
            scheme = BoardSchemeService.ensure_default_scheme()
        if not scheme.is_locked and not scheme.columns.exists():
            board.active_scheme = scheme
            board.save(update_fields=["active_scheme", "updated_at"])
            return
        BoardSchemeService.apply_scheme(board, scheme, delete_tasks=False)

    @staticmethod
    def assert_column_mutable(column: BoardColumn) -> None:
        if column.is_locked:
            raise ValidationError(
                "Column belongs to a locked board scheme and cannot be changed.",
                code="column_locked",
            )

    @staticmethod
    def assert_board_mutable(board: Board) -> None:
        if BoardSchemeService.is_board_locked(board):
            raise ValidationError(
                "Active board scheme is locked and cannot be changed.",
                code="scheme_locked",
            )

    @staticmethod
    @transaction.atomic
    def delete_scheme(board: Board, slug: str) -> None:
        scheme = BoardSchemeService.get_scheme(slug)
        if scheme.is_locked:
            raise ValidationError(
                "Locked schemes cannot be deleted.",
                code="scheme_locked",
            )

        active = BoardSchemeService.get_active_scheme(board)
        if active and active.pk == scheme.pk:
            default = BoardSchemeService.ensure_default_scheme()
            BoardSchemeService.apply_scheme(board, default, delete_tasks=True)

        scheme.delete()

    @staticmethod
    def _delete_board_tasks(board: Board) -> None:
        if not board.pk:
            return

        from apps.tasks.models import Task

        Task.objects.filter(board=board).delete()
