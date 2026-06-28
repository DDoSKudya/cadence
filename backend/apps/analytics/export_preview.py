from __future__ import annotations

from apps.analytics import export_data as data
from apps.analytics.export_i18n import resolve_export_locale
from apps.analytics.filters import AnalyticsFilters
from apps.analytics.models import ExportType


def preview_from_rows(
    sheet_key: str,
    rows: list[list],
    *,
    limit: int = data.PREVIEW_ROW_LIMIT,
) -> dict:
    total = len(rows)
    return {
        "id": data.EXPORT_SHEET_IDS[sheet_key],
        "rows": data.serialize_preview_rows(rows[:limit]),
        "total": total,
    }


def _append_overview_sheet(
    sheets: list[dict],
    rows: list[list],
    *,
    limit: int,
) -> None:
    if rows:
        sheets.append(
            preview_from_rows("export.sheet.overview", rows, limit=limit),
        )


def collect_export_preview(
    export_type: str,
    filters: AnalyticsFilters,
    *,
    locale: str | None = None,
    limit: int = data.PREVIEW_ROW_LIMIT,
) -> list[dict]:
    resolved_locale = resolve_export_locale({"locale": locale} if locale else None)
    if export_type == ExportType.TASKS:
        return _preview_tasks(filters, resolved_locale, limit=limit)
    if export_type == ExportType.ARCHIVE:
        return _preview_archive(filters, resolved_locale, limit=limit)
    if export_type == ExportType.WEEKLY_SUMMARY:
        return _preview_weekly_summary(filters, resolved_locale, limit=limit)
    if export_type == ExportType.TAG_SUMMARY:
        return _preview_tag_summary(filters, limit=limit)
    if export_type == ExportType.NOTIFICATION_REPORT:
        return _preview_notification_report(filters, resolved_locale, limit=limit)
    if export_type == ExportType.JOBS_REPORT:
        return _preview_jobs_report(filters, limit=limit)
    if export_type == ExportType.IMPORTS_REPORT:
        return _preview_imports_report(filters, limit=limit)
    raise ValueError(f"Unsupported export type: {export_type}")


def _preview_tasks(filters: AnalyticsFilters, locale: str, *, limit: int) -> list[dict]:
    rows = data.task_rows(data.tasks_queryset(filters), locale)
    overview_rows = data.column_breakdown_rows(filters, locale)
    sheets: list[dict] = []
    _append_overview_sheet(sheets, overview_rows, limit=limit)
    sheets.append(preview_from_rows("export.sheet.tasks", rows, limit=limit))
    return sheets


def _preview_archive(
    filters: AnalyticsFilters,
    locale: str,
    *,
    limit: int,
) -> list[dict]:
    closed_rows, column_rows, rows = data.archive_export_data(filters, locale)
    sheets: list[dict] = []
    if closed_rows:
        _append_overview_sheet(sheets, closed_rows, limit=limit)
    elif column_rows:
        _append_overview_sheet(sheets, column_rows, limit=limit)
    sheets.append(preview_from_rows("export.sheet.archive", rows, limit=limit))
    return sheets


def _preview_weekly_summary(
    filters: AnalyticsFilters,
    locale: str,
    *,
    limit: int,
) -> list[dict]:
    summary_rows, tag_rows, column_rows, stale_rows, kpis = (
        data.weekly_summary_export_data(filters, locale)
    )
    return [
        {
            "id": "summary",
            "rows": data.serialize_preview_rows(summary_rows[:limit]),
            "total": len(summary_rows),
            "kpis": kpis,
        },
        preview_from_rows("export.sheet.byTags", tag_rows, limit=limit),
        preview_from_rows("export.sheet.byColumns", column_rows, limit=limit),
        preview_from_rows("export.sheet.staleTasks", stale_rows, limit=limit),
    ]


def _preview_tag_summary(filters: AnalyticsFilters, *, limit: int) -> list[dict]:
    rows = data.tag_summary_rows(filters)
    return [preview_from_rows("export.sheet.tags", rows, limit=limit)]


def _preview_notification_report(
    filters: AnalyticsFilters,
    locale: str,
    *,
    limit: int,
) -> list[dict]:
    action_rows, status_rows, rows = data.notification_report_data(filters, locale)
    sheets: list[dict] = []
    if action_rows:
        _append_overview_sheet(sheets, action_rows, limit=limit)
    elif status_rows:
        _append_overview_sheet(sheets, status_rows, limit=limit)
    sheets.append(preview_from_rows("export.sheet.notifications", rows, limit=limit))
    return sheets


def _preview_jobs_report(filters: AnalyticsFilters, *, limit: int) -> list[dict]:
    status_rows, rows = data.jobs_report_data(filters)
    sheets: list[dict] = []
    _append_overview_sheet(sheets, status_rows, limit=limit)
    sheets.append(preview_from_rows("export.sheet.jobs", rows, limit=limit))
    return sheets


def _preview_imports_report(filters: AnalyticsFilters, *, limit: int) -> list[dict]:
    status_rows, rows = data.imports_report_data(filters)
    sheets: list[dict] = []
    _append_overview_sheet(sheets, status_rows, limit=limit)
    sheets.append(preview_from_rows("export.sheet.imports", rows, limit=limit))
    return sheets
