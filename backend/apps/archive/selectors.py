from datetime import datetime

from django.db.models import Q, QuerySet

from apps.boards.services import ColumnSettingsService
from apps.tasks.models import Task
from apps.weeks.services import WeekService

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def archived_tasks_queryset() -> QuerySet[Task]:
    board = ColumnSettingsService.get_default_board()
    return (
        Task.objects.filter(board=board, archived_at__isnull=False)
        .select_related("week", "column")
        .prefetch_related("tags")
        .order_by("-closed_at", "-id")
    )


def list_archived_tasks(
    *,
    week: str | None = None,
    tag: str | None = None,
    source: str | None = None,
    closed_from: datetime | None = None,
    closed_to: datetime | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Task], int]:
    queryset = archived_tasks_queryset()

    if week:
        resolved = WeekService.resolve_week(week)
        queryset = queryset.filter(week_id=resolved.id)

    if tag:
        queryset = queryset.filter(tags__slug=tag.strip()).distinct()

    if source:
        queryset = queryset.filter(source=source.strip())

    if closed_from:
        queryset = queryset.filter(closed_at__gte=closed_from)

    if closed_to:
        queryset = queryset.filter(closed_at__lte=closed_to)

    if search:
        term = search.strip()
        if term:
            queryset = queryset.filter(
                Q(title__icontains=term) | Q(description__icontains=term),
            )

    total = queryset.count()
    offset = (page - 1) * page_size
    tasks = list(queryset[offset : offset + page_size])
    return tasks, total
