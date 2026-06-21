from collections import defaultdict

from django.db.models import Q

from apps.boards.models import Board
from apps.boards.services import ColumnSettingsService
from apps.tasks.models import Task
from apps.weeks.models import Week


def active_tasks_for_board(board: Board, week: Week):
    return (
        Task.objects.filter(board=board, archived_at__isnull=True)
        .filter(Q(week=week) | Q(week__isnull=True))
        .select_related("week", "column")
        .prefetch_related("tags")
        .order_by("column_id", "position")
    )


def build_board_payload(board: Board, week: Week) -> dict:
    columns = list(ColumnSettingsService.active_columns(board))
    tasks_by_column: dict[int, list[Task]] = defaultdict(list)

    for task in active_tasks_for_board(board, week):
        tasks_by_column[task.column_id].append(task)

    return {
        "board": board,
        "week": week,
        "columns": columns,
        "tasks_by_column": tasks_by_column,
    }
