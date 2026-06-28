from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from apps.analytics import selectors
from apps.analytics.export_i18n import (
    translate_column,
    translate_source,
    translate_status,
)
from apps.analytics.filters import AnalyticsFilters, period_bounds
from apps.analytics.week_format import format_week_label
from apps.boards.services import ColumnSettingsService
from apps.imports.models import ImportLog
from apps.jobs.models import BackgroundJob
from apps.notifications.models import NotificationJob
from apps.tasks.models import Task

PREVIEW_ROW_LIMIT = 8

EXPORT_SHEET_IDS = {
    "export.sheet.overview": "overview",
    "export.sheet.tasks": "tasks",
    "export.sheet.archive": "archive",
    "export.sheet.summary": "summary",
    "export.sheet.byTags": "byTags",
    "export.sheet.byColumns": "byColumns",
    "export.sheet.staleTasks": "staleTasks",
    "export.sheet.tags": "tags",
    "export.sheet.notifications": "notifications",
    "export.sheet.jobs": "jobs",
    "export.sheet.imports": "imports",
}


def serialize_preview_rows(rows: list[list]) -> list[list[str]]:
    return [["" if cell is None else str(cell) for cell in row] for row in rows]


def export_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M")


def tasks_queryset(filters: AnalyticsFilters):
    board = ColumnSettingsService.get_default_board()
    return selectors._apply_filters(
        Task.objects.filter(board=board), filters, period=False
    )


def task_row(task: Task, locale: str) -> list:
    week = ""
    if task.week is not None:
        week = format_week_label(f"{task.week.iso_year}-W{task.week.iso_week:02d}")
    tags = ", ".join(tag.name for tag in task.tags.all())
    return [
        task.id,
        task.title,
        translate_column(locale, task.column.system_type, task.column.name),
        translate_column(locale, task.column.system_type, task.column.system_type),
        week,
        tags,
        translate_source(locale, task.source),
        export_datetime(task.due_at),
        export_datetime(task.created_at),
        export_datetime(task.closed_at),
        export_datetime(task.archived_at),
    ]


def task_rows(queryset, locale: str) -> list[list]:
    queryset = queryset.select_related("column", "week").prefetch_related("tags")
    return [task_row(task, locale) for task in queryset]


def column_breakdown_rows(filters: AnalyticsFilters, locale: str) -> list[list]:
    breakdown = selectors.get_breakdown(filters, group_by="column")
    return [
        [
            translate_column(
                locale,
                item.get("system_type", ""),
                item.get("name", item["key"]),
            ),
            item["count"],
        ]
        for item in breakdown["items"]
        if item["count"] > 0
    ]


def status_count_rows(items: list, status_index: int) -> list[list]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item[status_index] or "—")
        counts[status] = counts.get(status, 0) + 1
    ranked = sorted(counts.items(), key=lambda row: -row[1])
    return [[status, count] for status, count in ranked]


def archive_export_data(
    filters: AnalyticsFilters,
    locale: str,
) -> tuple[list[list], list[list], list[list]]:
    board = ColumnSettingsService.get_default_board()
    queryset = (
        selectors._apply_filters(
            Task.objects.filter(board=board, archived_at__isnull=False),
            filters,
            period=False,
        )
        .select_related("column", "week")
        .prefetch_related("tags")
    )
    detail_rows = [[*task_row(task, locale), task.completion_note] for task in queryset]
    archive_analytics = selectors.get_archive_analytics(filters)
    closed_overview_rows = [
        [format_week_label(item["week"]), item["count"]]
        for item in archive_analytics["closed_by_week"]
        if item["count"] > 0
    ]
    column_overview_rows = column_breakdown_rows(filters, locale)
    return closed_overview_rows, column_overview_rows, detail_rows


def weekly_summary_export_data(
    filters: AnalyticsFilters,
    locale: str,
) -> tuple[list[list], list[list], list[list], list[list], dict[str, int]]:
    summary = selectors.get_summary(filters)
    trend = selectors.get_weekly_trend(filters)
    summary_rows = [
        [
            format_week_label(item["week"]),
            item["created"],
            item["closed"],
            item["carried_over"],
        ]
        for item in trend["items"]
        if item["created"] or item["closed"] or item["carried_over"]
    ]
    tag_rows = [
        [item["key"], item["count"]]
        for item in selectors.get_breakdown(filters, group_by="tag")["items"]
    ]
    column_rows = [
        [
            translate_column(
                locale,
                item.get("system_type", ""),
                item.get("name", item["key"]),
            ),
            translate_column(
                locale,
                item.get("system_type", ""),
                item.get("system_type", ""),
            ),
            item["count"],
        ]
        for item in selectors.get_breakdown(filters, group_by="column")["items"]
    ]
    board = ColumnSettingsService.get_default_board()
    active_qs = selectors._apply_filters(
        Task.objects.filter(board=board, archived_at__isnull=True),
        filters,
        period=False,
    )
    stale_qs = selectors._stale_tasks_queryset(active_qs)
    stale_rows = [
        [
            item["id"],
            item["title"],
            translate_column(
                locale,
                item.get("column_system_type", ""),
                item["column"],
            ),
            item["days_in_column"],
        ]
        for item in selectors._stale_task_items(stale_qs)
    ]
    kpis = {
        "created": summary["tasks_created"],
        "closed": summary["tasks_closed"],
        "active": summary["active_tasks"],
        "overdue": summary["overdue_tasks"],
        "stale": summary["stale_tasks"],
    }
    return summary_rows, tag_rows, column_rows, stale_rows, kpis


def tag_summary_rows(filters: AnalyticsFilters) -> list[list]:
    return [
        [item["key"], item["count"]]
        for item in selectors.get_breakdown(filters, group_by="tag")["items"]
    ]


def notification_report_data(
    filters: AnalyticsFilters,
    locale: str,
) -> tuple[list[list], list[list], list[list]]:
    board = ColumnSettingsService.get_default_board()
    period_start, period_end = period_bounds(filters)
    task_ids = selectors._scoped_task_ids(board, filters)
    jobs = selectors._filter_datetime(
        NotificationJob.objects.filter(task_id__in=task_ids).select_related("task"),
        "created_at",
        period_start,
        period_end,
    )
    detail_rows = [
        [
            job.id,
            job.task_id,
            job.task.title if job.task_id else "",
            job.status,
            job.reason,
            job.telegram_chat_id,
            export_datetime(job.scheduled_at),
            export_datetime(job.sent_at),
            export_datetime(job.failed_at),
            job.last_error,
        ]
        for job in jobs
    ]
    status_overview_rows = status_count_rows(detail_rows, 3)
    telegram_actions = selectors.get_notifications(filters)["telegram_actions"]
    action_overview_rows = [
        [translate_status(locale, action["slug"]), action["count"]]
        for action in telegram_actions
        if action["count"] > 0
    ]
    return action_overview_rows, status_overview_rows, detail_rows


def jobs_report_data(filters: AnalyticsFilters) -> tuple[list[list], list[list]]:
    period_start, period_end = period_bounds(filters)
    jobs = selectors._filter_datetime(
        BackgroundJob.objects.all(),
        "created_at",
        period_start,
        period_end,
    )
    detail_rows = [
        [
            job.id,
            job.job_type,
            job.status,
            job.attempts,
            export_datetime(job.scheduled_at),
            export_datetime(job.started_at),
            export_datetime(job.finished_at),
            job.last_error,
            export_datetime(job.created_at),
        ]
        for job in jobs
    ]
    status_overview_rows = status_count_rows(detail_rows, 2)
    return status_overview_rows, detail_rows


def imports_report_data(filters: AnalyticsFilters) -> tuple[list[list], list[list]]:
    period_start, period_end = period_bounds(filters)
    logs = selectors._filter_datetime(
        ImportLog.objects.all(),
        "created_at",
        period_start,
        period_end,
    )
    detail_rows = [
        [
            log.id,
            log.filename,
            log.status,
            log.tasks_created,
            log.source_label,
            log.error_message,
            export_datetime(log.started_at),
            export_datetime(log.finished_at),
            export_datetime(log.created_at),
        ]
        for log in logs
    ]
    status_overview_rows = status_count_rows(detail_rows, 2)
    return status_overview_rows, detail_rows
