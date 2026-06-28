from datetime import datetime, time, timedelta

from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Q,
    QuerySet,
)
from django.utils import timezone

from apps.analytics.constants import (
    DEFAULT_WEEKS_COUNT,
    MAX_WEEKS_COUNT,
    STALE_ITEMS_LIMIT,
)
from apps.analytics.filters import AnalyticsFilters, period_bounds, resolve_tag_ids
from apps.boards.models import SystemType, TaskStatus
from apps.boards.scheme_services import BoardSchemeService
from apps.boards.services import ColumnSettingsService
from apps.core.models import ProjectSettings, Tag
from apps.core.tag_services import TagService
from apps.notifications.models import (
    CallbackAction,
    NotificationJob,
    NotificationStatus,
    TelegramCallbackLog,
)
from apps.tasks.models import Task, TaskEvent, TaskEventType
from apps.weeks.models import Week
from apps.weeks.services import WeekService


def get_summary(filters: AnalyticsFilters) -> dict:
    board = ColumnSettingsService.get_default_board()
    period_start, period_end = period_bounds(filters)
    scoped = _apply_filters(Task.objects.filter(board=board), filters)

    created_qs = _filter_datetime(scoped, "created_at", period_start, period_end)
    closed_qs = _filter_datetime(
        scoped.filter(closed_at__isnull=False),
        "closed_at",
        period_start,
        period_end,
    )
    archived_qs = _filter_datetime(
        scoped.filter(archived_at__isnull=False),
        "archived_at",
        period_start,
        period_end,
    )

    active_qs = Task.objects.filter(board=board, archived_at__isnull=True)
    active_qs = _apply_filters(active_qs, filters, period=False)

    now = timezone.now()
    overdue_count = active_qs.filter(due_at__lt=now, due_at__isnull=False).count()
    stale_qs = _stale_tasks_queryset(active_qs)
    stale_count = stale_qs.count()
    stale_items = _stale_task_items(stale_qs[:STALE_ITEMS_LIMIT])

    closed_total = closed_qs.count()
    evidence_count = closed_qs.exclude(evidence_url="").count()
    evidence_rate = evidence_count / closed_total if closed_total else 0.0

    return {
        "tasks_created": created_qs.count(),
        "tasks_closed": closed_total,
        "tasks_archived": archived_qs.count(),
        "active_tasks": active_qs.count(),
        "overdue_tasks": overdue_count,
        "stale_tasks": stale_count,
        "evidence_rate": round(evidence_rate, 4),
        "stale_items": stale_items,
        **_active_scheme_meta(board),
    }


def get_weekly_trend(
    filters: AnalyticsFilters,
    *,
    weeks_count: int = DEFAULT_WEEKS_COUNT,
) -> dict:
    board = ColumnSettingsService.get_default_board()
    weeks_count = max(1, min(weeks_count, MAX_WEEKS_COUNT))
    current = WeekService.get_or_create_current_week()
    weeks = _recent_weeks(current, weeks_count)

    items: list[dict] = []
    for week in weeks:
        period_start = timezone.make_aware(datetime.combine(week.starts_on, time.min))
        period_end = timezone.make_aware(datetime.combine(week.ends_on, time.max))

        base = _apply_filters(Task.objects.filter(board=board), filters, period=False)
        created = base.filter(
            created_at__gte=period_start,
            created_at__lte=period_end,
        ).count()
        closed = base.filter(
            closed_at__isnull=False,
            closed_at__gte=period_start,
            closed_at__lte=period_end,
        ).count()
        carried_over = base.filter(
            week_id=week.id,
            archived_at__isnull=True,
        ).count()

        items.append(
            {
                "week": f"{week.iso_year}-W{week.iso_week:02d}",
                "created": created,
                "closed": closed,
                "carried_over": carried_over,
            },
        )

    return {"items": items}


def get_breakdown(filters: AnalyticsFilters, *, group_by: str) -> dict:
    board = ColumnSettingsService.get_default_board()
    period_start, period_end = period_bounds(filters)
    scoped = _apply_filters(Task.objects.filter(board=board), filters)
    scoped = _filter_datetime(scoped, "created_at", period_start, period_end)

    if group_by == "tag":
        items = _breakdown_by_tag(scoped)
    elif group_by == "column":
        items = _breakdown_by_column(scoped)
    elif group_by == "source":
        items = _breakdown_by_source(scoped)
    else:
        items = []

    return {"group_by": group_by, "items": items}


def get_cycle_time(filters: AnalyticsFilters) -> dict:
    board = ColumnSettingsService.get_default_board()
    period_start, period_end = period_bounds(filters)
    scoped = _apply_filters(
        Task.objects.filter(board=board, closed_at__isnull=False),
        filters,
        period=False,
    )
    scoped = _filter_datetime(scoped, "closed_at", period_start, period_end)

    duration_expr = ExpressionWrapper(
        F("closed_at") - F("created_at"),
        output_field=DurationField(),
    )
    aggregate = scoped.aggregate(
        avg_duration=Avg(duration_expr),
        count=Count("id"),
    )
    count = aggregate["count"] or 0
    avg_seconds = (
        aggregate["avg_duration"].total_seconds() if aggregate["avg_duration"] else 0
    )
    distribution = _cycle_time_distribution(scoped)

    return {
        "avg_hours": round(avg_seconds / 3600, 2) if count else 0,
        "count": count,
        "distribution": distribution,
    }


def get_notifications(filters: AnalyticsFilters) -> dict:
    board = ColumnSettingsService.get_default_board()
    period_start, period_end = period_bounds(filters)
    task_ids = _scoped_task_ids(board, filters)

    jobs = NotificationJob.objects.filter(task_id__in=task_ids)
    jobs = _filter_datetime(jobs, "created_at", period_start, period_end)
    callbacks = TelegramCallbackLog.objects.filter(task_id__in=task_ids)
    callbacks = _filter_datetime(callbacks, "created_at", period_start, period_end)

    sent = jobs.filter(status=NotificationStatus.SUCCEEDED).count()
    failures = jobs.filter(status=NotificationStatus.FAILED).count()
    telegram_actions = _aggregate_telegram_actions(board, callbacks)
    done_actions = _telegram_action_count(telegram_actions, "done")
    in_progress_actions = _telegram_action_count(telegram_actions, "process")
    closed_after = _tasks_closed_after_notification(
        board,
        task_ids,
        period_start,
        period_end,
    )

    return {
        "notifications_sent": sent,
        "notification_failures": failures,
        "telegram_actions": telegram_actions,
        "telegram_done_actions": done_actions,
        "telegram_in_progress_actions": in_progress_actions,
        "tasks_closed_after_notification": closed_after,
    }


def get_task_flow(filters: AnalyticsFilters) -> dict:
    board = ColumnSettingsService.get_default_board()
    period_start, period_end = period_bounds(filters)
    active_qs = _apply_filters(
        Task.objects.filter(board=board, archived_at__isnull=True),
        filters,
        period=False,
    )
    current = WeekService.get_or_create_current_week()
    carry_over_count = _carry_over_count(active_qs, current)

    events = TaskEvent.objects.filter(event_type=TaskEventType.REOPENED)
    events = _filter_datetime(events, "created_at", period_start, period_end)
    reopened_count = events.count()

    now = timezone.now()
    age_aggregate = active_qs.aggregate(
        avg_age=Avg(
            ExpressionWrapper(now - F("created_at"), output_field=DurationField())
        ),
    )
    avg_age = age_aggregate["avg_age"]
    avg_open_age_hours = round(avg_age.total_seconds() / 3600, 2) if avg_age else 0

    trend = get_weekly_trend(filters)

    return {
        "reopened_count": reopened_count,
        "avg_open_age_hours": avg_open_age_hours,
        "carry_over_count": carry_over_count,
        "items": trend["items"],
    }


def get_archive_analytics(filters: AnalyticsFilters) -> dict:
    board = ColumnSettingsService.get_default_board()
    period_start, period_end = period_bounds(filters)
    scoped = _apply_filters(
        Task.objects.filter(board=board, archived_at__isnull=False),
        filters,
        period=False,
    )
    scoped = _filter_datetime(scoped, "closed_at", period_start, period_end)

    closed_total = scoped.count()
    evidence_count = scoped.exclude(evidence_url="").count()
    notes_count = scoped.exclude(completion_note="").count()

    closed_by_week = list(
        scoped.values("week__iso_year", "week__iso_week")
        .annotate(count=Count("id"))
        .order_by("-week__iso_year", "-week__iso_week")[:20],
    )
    week_items = [
        {
            "week": (
                f"{row['week__iso_year']}-W{row['week__iso_week']:02d}"
                if row["week__iso_year"] and row["week__iso_week"]
                else "—"
            ),
            "count": row["count"],
        }
        for row in closed_by_week
    ]

    tag_rows = (
        Tag.objects.filter(scheme=TagService.get_active_scheme(), tasks__in=scoped)
        .annotate(count=Count("tasks", distinct=True))
        .order_by("-count", "name")
        .values("name", "count")[:20]
    )
    tag_items = [{"tag": row["name"], "count": row["count"]} for row in tag_rows]

    return {
        "closed_total": closed_total,
        "evidence_coverage": round(evidence_count / closed_total, 4)
        if closed_total
        else 0,
        "completion_notes_coverage": round(notes_count / closed_total, 4)
        if closed_total
        else 0,
        "closed_by_week": week_items,
        "closed_by_tag": tag_items,
    }


def _apply_filters(
    queryset: QuerySet[Task],
    filters: AnalyticsFilters,
    *,
    period: bool = True,
) -> QuerySet[Task]:
    if filters.source:
        queryset = queryset.filter(source=filters.source)

    tag_ids = resolve_tag_ids(filters.tags)
    if tag_ids:
        queryset = queryset.filter(tags__id__in=tag_ids).distinct()

    if period and filters.week is not None:
        queryset = queryset.filter(week_id=filters.week.id)

    return queryset


def _filter_datetime(
    queryset: QuerySet,
    field: str,
    start: datetime | None,
    end: datetime | None,
) -> QuerySet:
    if start is not None:
        queryset = queryset.filter(**{f"{field}__gte": start})
    if end is not None:
        queryset = queryset.filter(**{f"{field}__lte": end})
    return queryset


def _stale_tasks_queryset(active_qs: QuerySet[Task]) -> QuerySet[Task]:
    settings = ProjectSettings.load()
    now = timezone.now()
    planned_threshold = now - timedelta(minutes=settings.stale_planned_minutes)
    in_progress_threshold = now - timedelta(minutes=settings.stale_in_progress_minutes)
    return active_qs.filter(
        Q(
            column__system_type=SystemType.PLANNED,
            column_entered_at__lt=planned_threshold,
        )
        | Q(
            column__system_type=SystemType.IN_PROGRESS,
            column_entered_at__lt=in_progress_threshold,
        ),
    ).select_related("column")


def _stale_task_items(queryset: QuerySet[Task]) -> list[dict]:
    now = timezone.now()
    items: list[dict] = []
    for task in queryset:
        delta = now - task.column_entered_at
        items.append(
            {
                "id": task.id,
                "title": task.title,
                "column": task.column.name,
                "column_system_type": task.column.system_type,
                "days_in_column": round(delta.total_seconds() / 86400, 1),
            },
        )
    return items


def _breakdown_by_tag(queryset: QuerySet[Task]) -> list[dict]:
    scheme = TagService.get_active_scheme()
    rows = (
        Tag.objects.filter(scheme=scheme, tasks__in=queryset)
        .annotate(count=Count("tasks", distinct=True))
        .order_by("-count", "name")
        .values("name", "count")
    )
    return [{"key": row["name"], "count": row["count"]} for row in rows]


def _breakdown_by_column(queryset: QuerySet[Task]) -> list[dict]:
    rows = (
        queryset.values("column__name", "column__system_type")
        .annotate(count=Count("id"))
        .order_by("-count", "column__name")
    )
    return [
        {
            "key": row["column__system_type"] or row["column__name"],
            "name": row["column__name"],
            "system_type": row["column__system_type"],
            "count": row["count"],
        }
        for row in rows
    ]


def _breakdown_by_source(queryset: QuerySet[Task]) -> list[dict]:
    rows = queryset.values("source").annotate(count=Count("id")).order_by("-count")
    return [{"key": row["source"], "count": row["count"]} for row in rows]


def _cycle_time_distribution(queryset: QuerySet[Task]) -> list[dict]:
    buckets = [
        ("bucket_0_1d", timedelta(days=1)),
        ("bucket_1_3d", timedelta(days=3)),
        ("bucket_3_7d", timedelta(days=7)),
        ("bucket_7d_plus", None),
    ]
    items: list[dict] = []
    for label, upper in buckets:
        durations = queryset.annotate(
            duration=ExpressionWrapper(
                F("closed_at") - F("created_at"),
                output_field=DurationField(),
            ),
        )
        if upper is None:
            count = durations.filter(duration__gte=timedelta(days=7)).count()
        elif label == "bucket_0_1d":
            count = durations.filter(duration__lt=upper).count()
        elif label == "bucket_1_3d":
            count = durations.filter(
                duration__gte=timedelta(days=1),
                duration__lt=upper,
            ).count()
        else:
            count = durations.filter(
                duration__gte=timedelta(days=3),
                duration__lt=upper,
            ).count()
        items.append({"bucket": label, "count": count})
    return items


def _recent_weeks(current: Week, count: int) -> list[Week]:
    weeks: list[Week] = []
    week = current
    for _ in range(count):
        weeks.append(week)
        week = _previous_week(week)
    weeks.reverse()
    return weeks


def _previous_week(week: Week) -> Week:
    previous_end = week.starts_on - timedelta(days=1)
    iso = previous_end.isocalendar()
    return WeekService.get_or_create_week(iso.year, iso.week)


def _carry_over_count(active_qs: QuerySet[Task], current: Week) -> int:
    return (
        active_qs.filter(week__isnull=False)
        .exclude(week_id=current.id)
        .filter(
            Q(week__iso_year__lt=current.iso_year)
            | Q(week__iso_year=current.iso_year, week__iso_week__lt=current.iso_week),
        )
        .count()
    )


def _active_scheme_meta(board) -> dict:
    scheme = BoardSchemeService.get_active_scheme(board)
    if scheme is None:
        return {}
    return {
        "scheme": {
            "slug": scheme.slug,
            "name": scheme.name,
        },
    }


def _scoped_task_ids(board, filters: AnalyticsFilters) -> list[int]:
    queryset = _apply_filters(Task.objects.filter(board=board), filters, period=False)
    return list(queryset.values_list("id", flat=True))


def _aggregate_telegram_actions(board, callbacks) -> list[dict]:
    statuses = list(
        TaskStatus.objects.filter(board=board, on_flow=True).order_by("position"),
    )
    counts: dict[str, int] = {status.slug: 0 for status in statuses}
    status_by_id = {status.id: status.slug for status in statuses}

    for log in callbacks.only("action", "payload"):
        if log.action == CallbackAction.TASK_SET_STATUS:
            payload = log.payload or {}
            status_id = payload.get("status_id")
            if status_id is None:
                continue
            slug = status_by_id.get(int(status_id))
            if slug is not None:
                counts[slug] = counts.get(slug, 0) + 1
        elif log.action == CallbackAction.TASK_DONE:
            counts["done"] = counts.get("done", 0) + 1
        elif log.action == CallbackAction.TASK_IN_PROGRESS:
            counts["process"] = counts.get("process", 0) + 1

    return [
        {"slug": slug, "count": count} for slug, count in counts.items() if count > 0
    ]


def _telegram_action_count(actions: list[dict], slug: str) -> int:
    return next((item["count"] for item in actions if item["slug"] == slug), 0)


def _tasks_closed_after_notification(
    board,
    task_ids: list[int],
    period_start: datetime | None,
    period_end: datetime | None,
) -> int:
    if not task_ids:
        return 0

    closed = Task.objects.filter(
        board=board,
        id__in=task_ids,
        closed_at__isnull=False,
    )
    closed = _filter_datetime(closed, "closed_at", period_start, period_end)

    count = 0
    window = timedelta(days=7)
    for task in closed.iterator(chunk_size=200):
        last_sent = (
            NotificationJob.objects.filter(
                task_id=task.id,
                status=NotificationStatus.SUCCEEDED,
                sent_at__isnull=False,
            )
            .order_by("-sent_at")
            .values_list("sent_at", flat=True)
            .first()
        )
        if last_sent is None or task.closed_at is None:
            continue
        if last_sent <= task.closed_at <= last_sent + window:
            count += 1
    return count
