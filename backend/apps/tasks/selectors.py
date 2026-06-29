from collections import defaultdict

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from apps.boards.models import Board
from apps.boards.services import ColumnSettingsService
from apps.tasks.models import Task
from apps.weeks.models import Week


def get_board_task(pk: int) -> Task:
    board = ColumnSettingsService.get_default_board()
    return get_object_or_404(Task, pk=pk, board=board)


def active_tasks_for_board(board: Board, _week: Week | None = None):
    """Return all open board tasks.

    ``_week`` is accepted for call-site compatibility (board context week in the
    payload). Open tasks stay visible across ISO weeks; only archiving removes them.
    """
    return (
        Task.objects.filter(board=board, archived_at__isnull=True)
        .select_related("week", "column", "task_status")
        .prefetch_related("tags")
        .annotate(
            _outgoing_links_count=Count("outgoing_links", distinct=True),
            _incoming_links_count=Count("incoming_links", distinct=True),
        )
        .order_by("column_id", "position")
    )


def search_active_tasks(
    board: Board,
    *,
    query: str,
    exclude_task_id: int | None = None,
    limit: int = 12,
):
    queryset = Task.objects.filter(board=board, archived_at__isnull=True)
    if exclude_task_id is not None:
        queryset = queryset.exclude(pk=exclude_task_id)

    trimmed = query.strip()
    if trimmed:
        queryset = queryset.filter(
            Q(title__icontains=trimmed) | Q(external_ref__icontains=trimmed),
        )

    return queryset.order_by("title")[:limit]


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
