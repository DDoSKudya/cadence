import csv
from collections.abc import Callable
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.analytics import export_data as data
from apps.analytics.export_filenames import build_export_filename_stem
from apps.analytics.export_i18n import et, resolve_export_locale
from apps.analytics.filters import (
    AnalyticsFilters,
    parse_filters_payload,
    period_label,
)
from apps.analytics.models import AnalyticsExportJob, ExportType, FileFormat
from apps.analytics.xlsx_builder import AnalyticsXlsxBuilder, ExportMeta, SheetChartSpec
from apps.boards.scheme_services import BoardSchemeService
from apps.boards.services import ColumnSettingsService

ExportHandler = Callable[[AnalyticsExportJob, AnalyticsFilters, str], tuple[Path, int]]

REPORT_TITLE_KEYS = {
    ExportType.TASKS: "export.report.tasks",
    ExportType.ARCHIVE: "export.report.archive",
    ExportType.WEEKLY_SUMMARY: "export.report.weekly_summary",
    ExportType.TAG_SUMMARY: "export.report.tag_summary",
    ExportType.NOTIFICATION_REPORT: "export.report.notification_report",
    ExportType.JOBS_REPORT: "export.report.jobs_report",
    ExportType.IMPORTS_REPORT: "export.report.imports_report",
}

CSV_PRIMARY_SHEET = {
    ExportType.TASKS: "export.sheet.tasks",
    ExportType.ARCHIVE: "export.sheet.archive",
    ExportType.WEEKLY_SUMMARY: "export.sheet.summary",
    ExportType.TAG_SUMMARY: "export.sheet.tags",
    ExportType.NOTIFICATION_REPORT: "export.sheet.notifications",
    ExportType.JOBS_REPORT: "export.sheet.jobs",
    ExportType.IMPORTS_REPORT: "export.sheet.imports",
}


def export_report(export_job: AnalyticsExportJob) -> tuple[Path, int]:
    filters = parse_filters_payload(export_job.filters)
    handler = EXPORT_HANDLERS.get(export_job.export_type)
    if handler is None:
        raise ValueError(f"Unsupported export type: {export_job.export_type}")
    return handler(export_job, filters, export_job.file_format)


def _export_dir(export_job: AnalyticsExportJob) -> Path:
    relative = Path("exports") / "analytics" / str(export_job.id)
    absolute = Path(settings.MEDIA_ROOT) / relative
    absolute.mkdir(parents=True, exist_ok=True)
    return relative


def _build_meta(
    export_job: AnalyticsExportJob,
    filters: AnalyticsFilters,
    *,
    export_type: ExportType,
) -> ExportMeta:
    locale = resolve_export_locale(export_job.filters)
    board = ColumnSettingsService.get_default_board()
    scheme = BoardSchemeService.get_active_scheme(board)
    period = period_label(filters)
    if "week" in period:
        period_text = et("export.periodWeek", locale=locale, week=period["week"])
    elif period.get("from") or period.get("to"):
        period_text = et(
            "export.periodRange",
            locale=locale,
            start=period.get("from", "…"),
            end=period.get("to", "…"),
        )
    else:
        period_text = et("export.periodAll", locale=locale)

    title_key = REPORT_TITLE_KEYS.get(export_type, "export.reportTitle")
    return ExportMeta(
        locale=locale,
        report_title=et(title_key, locale=locale),
        scheme_name=scheme.name if scheme is not None else "",
        period_label=period_text,
        generated_at=timezone.now(),
    )


def _export_tasks(
    export_job: AnalyticsExportJob,
    filters: AnalyticsFilters,
    file_format: str,
) -> tuple[Path, int]:
    meta = _build_meta(export_job, filters, export_type=ExportType.TASKS)
    rows = data.task_rows(data.tasks_queryset(filters), meta.locale)
    header_keys = [
        "export.col.id",
        "export.col.title",
        "export.col.column",
        "export.col.systemType",
        "export.col.week",
        "export.col.tags",
        "export.col.source",
        "export.col.dueAt",
        "export.col.createdAt",
        "export.col.closedAt",
        "export.col.archivedAt",
    ]
    overview_headers = ["export.col.column", "export.col.count"]
    overview_rows = data.column_breakdown_rows(filters, meta.locale)
    overview_charts = (
        [SheetChartSpec("pie", "export.chart.columnDistribution")]
        if overview_rows
        else None
    )
    return _write_output(
        export_job,
        file_format,
        filters,
        meta,
        [
            (
                "export.sheet.overview",
                overview_headers,
                overview_rows,
                None,
                overview_charts,
            ),
            ("export.sheet.tasks", header_keys, rows),
        ],
        csv_sheet_key=CSV_PRIMARY_SHEET[ExportType.TASKS],
    )


def _export_archive(
    export_job: AnalyticsExportJob,
    filters: AnalyticsFilters,
    file_format: str,
) -> tuple[Path, int]:
    meta = _build_meta(export_job, filters, export_type=ExportType.ARCHIVE)
    closed_rows, column_rows, rows = data.archive_export_data(filters, meta.locale)
    header_keys = [
        "export.col.id",
        "export.col.title",
        "export.col.column",
        "export.col.systemType",
        "export.col.week",
        "export.col.tags",
        "export.col.source",
        "export.col.dueAt",
        "export.col.createdAt",
        "export.col.closedAt",
        "export.col.archivedAt",
        "export.col.completionNote",
    ]
    closed_headers = ["export.col.week", "export.col.count"]
    column_headers = ["export.col.column", "export.col.count"]
    overview_sheets = []
    if closed_rows:
        overview_sheets.append(
            (
                "export.sheet.overview",
                closed_headers,
                closed_rows,
                None,
                [SheetChartSpec("bar_col", "export.chart.closedByWeek")],
            ),
        )
    elif column_rows:
        overview_sheets.append(
            (
                "export.sheet.overview",
                column_headers,
                column_rows,
                None,
                [SheetChartSpec("pie", "export.chart.columnDistribution")],
            ),
        )
    return _write_output(
        export_job,
        file_format,
        filters,
        meta,
        [
            *overview_sheets,
            ("export.sheet.archive", header_keys, rows),
        ],
        csv_sheet_key=CSV_PRIMARY_SHEET[ExportType.ARCHIVE],
    )


def _export_weekly_summary(
    export_job: AnalyticsExportJob,
    filters: AnalyticsFilters,
    file_format: str,
) -> tuple[Path, int]:
    meta = _build_meta(export_job, filters, export_type=ExportType.WEEKLY_SUMMARY)
    summary_rows, tag_rows, column_rows, stale_rows, kpis_data = (
        data.weekly_summary_export_data(filters, meta.locale)
    )
    summary_header_keys = [
        "export.col.week",
        "export.col.created",
        "export.col.closed",
        "export.col.carriedOver",
    ]
    tag_header_keys = ["export.col.tag", "export.col.count"]
    column_header_keys = [
        "export.col.column",
        "export.col.systemType",
        "export.col.count",
    ]
    stale_header_keys = [
        "export.col.id",
        "export.col.title",
        "export.col.column",
        "export.col.daysInColumn",
    ]
    kpis = [
        ("export.kpi.created", kpis_data["created"]),
        ("export.kpi.closed", kpis_data["closed"]),
        ("export.kpi.active", kpis_data["active"]),
        ("export.kpi.overdue", kpis_data["overdue"]),
        ("export.kpi.stale", kpis_data["stale"]),
    ]
    sheets = [
        (
            "export.sheet.summary",
            summary_header_keys,
            summary_rows,
            kpis,
            [SheetChartSpec("weekly_combo", "export.chart.weeklyTrend")],
        ),
        (
            "export.sheet.byTags",
            tag_header_keys,
            tag_rows,
            None,
            [SheetChartSpec("pie", "export.chart.byTags")],
        ),
        (
            "export.sheet.byColumns",
            column_header_keys,
            column_rows,
            None,
            [SheetChartSpec("bar_col", "export.chart.byColumns")],
        ),
        ("export.sheet.staleTasks", stale_header_keys, stale_rows, None, None),
    ]
    return _write_output(
        export_job,
        file_format,
        filters,
        meta,
        sheets,
        csv_sheet_key=CSV_PRIMARY_SHEET[ExportType.WEEKLY_SUMMARY],
    )


def _export_tag_summary(
    export_job: AnalyticsExportJob,
    filters: AnalyticsFilters,
    file_format: str,
) -> tuple[Path, int]:
    meta = _build_meta(export_job, filters, export_type=ExportType.TAG_SUMMARY)
    header_keys = ["export.col.tag", "export.col.count"]
    rows = data.tag_summary_rows(filters)
    charts = [SheetChartSpec("pie", "export.chart.tagDistribution")] if rows else None
    return _write_output(
        export_job,
        file_format,
        filters,
        meta,
        [("export.sheet.tags", header_keys, rows, None, charts)],
        csv_sheet_key=CSV_PRIMARY_SHEET[ExportType.TAG_SUMMARY],
    )


def _export_notification_report(
    export_job: AnalyticsExportJob,
    filters: AnalyticsFilters,
    file_format: str,
) -> tuple[Path, int]:
    meta = _build_meta(export_job, filters, export_type=ExportType.NOTIFICATION_REPORT)
    action_rows, status_rows, rows = data.notification_report_data(filters, meta.locale)
    header_keys = [
        "export.col.id",
        "export.col.taskId",
        "export.col.taskTitle",
        "export.col.status",
        "export.col.reason",
        "export.col.telegramChat",
        "export.col.scheduledAt",
        "export.col.sentAt",
        "export.col.failedAt",
        "export.col.lastError",
    ]
    status_headers = ["export.col.status", "export.col.count"]
    action_headers = ["export.col.status", "export.col.count"]
    overview_sheets = []
    if action_rows:
        overview_sheets.append(
            (
                "export.sheet.overview",
                action_headers,
                action_rows,
                None,
                [SheetChartSpec("pie", "export.chart.telegramActions")],
            ),
        )
    elif status_rows:
        overview_sheets.append(
            (
                "export.sheet.overview",
                status_headers,
                status_rows,
                None,
                [SheetChartSpec("pie", "export.chart.notificationStatus")],
            ),
        )
    return _write_output(
        export_job,
        file_format,
        filters,
        meta,
        [
            *overview_sheets,
            ("export.sheet.notifications", header_keys, rows),
        ],
        csv_sheet_key=CSV_PRIMARY_SHEET[ExportType.NOTIFICATION_REPORT],
    )


def _export_jobs_report(
    export_job: AnalyticsExportJob,
    filters: AnalyticsFilters,
    file_format: str,
) -> tuple[Path, int]:
    meta = _build_meta(export_job, filters, export_type=ExportType.JOBS_REPORT)
    status_rows, rows = data.jobs_report_data(filters)
    header_keys = [
        "export.col.id",
        "export.col.jobType",
        "export.col.status",
        "export.col.attempts",
        "export.col.scheduledAt",
        "export.col.startedAt",
        "export.col.finishedAt",
        "export.col.lastError",
        "export.col.createdAt",
    ]
    status_headers = ["export.col.status", "export.col.count"]
    overview_sheets = []
    if status_rows:
        overview_sheets.append(
            (
                "export.sheet.overview",
                status_headers,
                status_rows,
                None,
                [SheetChartSpec("pie", "export.chart.jobStatus")],
            ),
        )
    return _write_output(
        export_job,
        file_format,
        filters,
        meta,
        [
            *overview_sheets,
            ("export.sheet.jobs", header_keys, rows),
        ],
        csv_sheet_key=CSV_PRIMARY_SHEET[ExportType.JOBS_REPORT],
    )


def _export_imports_report(
    export_job: AnalyticsExportJob,
    filters: AnalyticsFilters,
    file_format: str,
) -> tuple[Path, int]:
    meta = _build_meta(export_job, filters, export_type=ExportType.IMPORTS_REPORT)
    status_rows, rows = data.imports_report_data(filters)
    header_keys = [
        "export.col.id",
        "export.col.filename",
        "export.col.status",
        "export.col.tasksCreated",
        "export.col.sourceLabel",
        "export.col.errorMessage",
        "export.col.startedAt",
        "export.col.finishedAt",
        "export.col.createdAt",
    ]
    status_headers = ["export.col.status", "export.col.count"]
    overview_sheets = []
    if status_rows:
        overview_sheets.append(
            (
                "export.sheet.overview",
                status_headers,
                status_rows,
                None,
                [SheetChartSpec("pie", "export.chart.importStatus")],
            ),
        )
    return _write_output(
        export_job,
        file_format,
        filters,
        meta,
        [
            *overview_sheets,
            ("export.sheet.imports", header_keys, rows),
        ],
        csv_sheet_key=CSV_PRIMARY_SHEET[ExportType.IMPORTS_REPORT],
    )


def _write_output(
    export_job: AnalyticsExportJob,
    file_format: str,
    filters: AnalyticsFilters,
    meta: ExportMeta,
    sheets: list[tuple],
    *,
    csv_sheet_key: str | None = None,
) -> tuple[Path, int]:
    export_dir = _export_dir(export_job)
    stem = build_export_filename_stem(
        export_job.export_type,
        filters,
        generated_at=meta.generated_at,
    )
    if file_format == FileFormat.CSV:
        if csv_sheet_key is not None:
            sheet = next(
                (item for item in sheets if item[0] == csv_sheet_key),
                sheets[-1],
            )
        else:
            sheet = sheets[0]
        sheet_key, header_keys, rows, *_rest = sheet
        headers = [et(key, locale=meta.locale) for key in header_keys]
        filename = f"{stem}.csv"
        path = Path(settings.MEDIA_ROOT) / export_dir / filename
        _write_csv(path, headers, rows)
    elif file_format == FileFormat.PDF:
        from apps.analytics.pdf_builder import AnalyticsPdfBuilder

        filename = f"{stem}.pdf"
        path = Path(settings.MEDIA_ROOT) / export_dir / filename
        AnalyticsPdfBuilder(meta).save(path, sheets)
    else:
        filename = f"{stem}.xlsx"
        path = Path(settings.MEDIA_ROOT) / export_dir / filename
        xlsx_builder = AnalyticsXlsxBuilder(meta)
        for sheet in sheets:
            sheet_key, header_keys, rows = sheet[0], sheet[1], sheet[2]
            kpis = sheet[3] if len(sheet) > 3 else None
            charts = sheet[4] if len(sheet) > 4 else None
            xlsx_builder.add_table_sheet(
                sheet_key=sheet_key,
                header_keys=header_keys,
                rows=rows,
                kpis=kpis,
                charts=charts,
            )
        xlsx_builder.save(path)

    row_count = sum(len(sheet[2]) for sheet in sheets)
    return export_dir / filename, row_count


def _write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


EXPORT_HANDLERS: dict[str, ExportHandler] = {
    ExportType.TASKS: _export_tasks,
    ExportType.ARCHIVE: _export_archive,
    ExportType.WEEKLY_SUMMARY: _export_weekly_summary,
    ExportType.TAG_SUMMARY: _export_tag_summary,
    ExportType.NOTIFICATION_REPORT: _export_notification_report,
    ExportType.JOBS_REPORT: _export_jobs_report,
    ExportType.IMPORTS_REPORT: _export_imports_report,
}
