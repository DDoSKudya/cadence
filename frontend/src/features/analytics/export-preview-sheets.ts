import type { EChartsOption } from "echarts";
import type { ComposerTranslation } from "vue-i18n";

import {
  breakdownChartOption,
  breakdownDonutOption,
  notificationsOption,
  telegramActionsOption,
  weeklyColumnOption,
  weeklyTrendOption,
} from "@/features/analytics/chart-options";
import { columnBreakdownLabel, telegramActionLabel } from "@/features/analytics/labels";
import { CHART_COLORS } from "@/features/analytics/register-echarts";
import type { BreakdownItem, ExportFormat, ExportPreviewSheetsMap, ExportSnapshot, ExportType } from "@/features/analytics/types";

const PREVIEW_ROWS = 8;

export interface PreviewSheetModel {
  id: string;
  tabLabel: string;
  sheetTitle: string;
  kpis?: Array<{ label: string; value: number }>;
  headers: string[];
  rows: string[][];
  hiddenRows?: number;
  chart?: {
    option: EChartsOption;
    title: string;
    size: "md" | "lg" | "donut";
  };
}

export interface PreviewDocumentMeta {
  reportTitle: string;
  schemeName?: string;
  periodLabel: string;
  generatedAt: string;
}

export interface PreviewDocumentModel {
  meta: PreviewDocumentMeta;
  sheets: PreviewSheetModel[];
  showTabs: boolean;
}

function col(t: ComposerTranslation, key: string): string {
  return t(`analytics.exportDoc.cols.${key}`);
}

function sheet(t: ComposerTranslation, key: string): string {
  return t(`analytics.exportDoc.sheets.${key}`);
}

function chartTitle(t: ComposerTranslation, key: string): string {
  return t(`analytics.exportDoc.charts.${key}`);
}

function limitRows(rows: string[][], total?: number) {
  if (rows.length <= PREVIEW_ROWS) {
    const hidden = total !== undefined && total > rows.length ? total - rows.length : undefined;
    return { rows, hidden };
  }
  return {
    rows: rows.slice(0, PREVIEW_ROWS),
    hidden: (total ?? rows.length) - PREVIEW_ROWS,
  };
}

function breakdownRows(items: BreakdownItem[]) {
  return items
    .filter((item) => item.count > 0)
    .map((item) => [columnBreakdownLabel(item), String(item.count)]);
}

function sheetData(
  previewSheets: ExportPreviewSheetsMap | undefined,
  sheetId: string,
  fallbackRows: string[][],
  fallbackTotal?: number,
) {
  const preview = previewSheets?.[sheetId];
  if (preview) {
    return { rows: preview.rows, total: preview.total, kpis: preview.kpis };
  }
  return { rows: fallbackRows, total: fallbackTotal ?? fallbackRows.length, kpis: undefined };
}

function baseMeta(
  exportType: ExportType,
  snapshot: ExportSnapshot,
  t: ComposerTranslation,
  weekLabelFn: (week: string) => string,
): PreviewDocumentMeta {
  const period = snapshot.summary?.period ?? {};
  let periodLabel = t("analytics.exportPreview.periodAll");
  if (period.week) {
    periodLabel = t("analytics.exportPreview.periodWeek", { week: weekLabelFn(period.week) });
  } else if (period.from || period.to) {
    periodLabel = t("analytics.exportPreview.periodRange", {
      start: period.from ?? "…",
      end: period.to ?? "…",
    });
  }

  return {
    reportTitle: t(`analytics.exportReport.${exportType}`),
    schemeName: snapshot.schemeName,
    periodLabel,
    generatedAt: new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date()),
  };
}

function makeSheet(
  partial: Omit<PreviewSheetModel, "rows"> & { rows: string[][]; totalRows?: number },
): PreviewSheetModel {
  const limited = limitRows(partial.rows, partial.totalRows);
  return {
    id: partial.id,
    tabLabel: partial.tabLabel,
    sheetTitle: partial.sheetTitle,
    kpis: partial.kpis,
    headers: partial.headers,
    rows: limited.rows,
    hiddenRows: limited.hidden,
    chart: partial.chart,
  };
}

function weeklySummarySheets(
  snapshot: ExportSnapshot,
  t: ComposerTranslation,
  weekLabelFn: (week: string) => string,
  previewSheets?: ExportPreviewSheetsMap,
): PreviewSheetModel[] {
  const summary = snapshot.summary;
  const trendItems = snapshot.weeklyTrend.filter(
    (item) => item.created > 0 || item.closed > 0 || item.carried_over > 0,
  );
  const trendRows = trendItems.map((item) => [
    weekLabelFn(item.week),
    String(item.created),
    String(item.closed),
    String(item.carried_over),
  ]);

  const tagRows = snapshot.tagBreakdown
    .filter((item) => item.count > 0)
    .map((item) => [item.key, String(item.count)]);

  const columnRows = snapshot.columnBreakdown
    .filter((item) => item.count > 0)
    .map((item) => [
      columnBreakdownLabel(item),
      item.system_type ?? "—",
      String(item.count),
    ]);

  const staleRows = (summary?.stale_items ?? []).map((item) => [
    String(item.id),
    item.title,
    columnBreakdownLabel({
      key: item.column,
      count: item.days_in_column,
      name: item.column,
      system_type: item.column_system_type,
    }),
    String(item.days_in_column),
  ]);
  const trend = sheetData(previewSheets, "summary", trendRows, trendItems.length);
  const tags = sheetData(previewSheets, "byTags", tagRows, tagRows.length);
  const columns = sheetData(previewSheets, "byColumns", columnRows, columnRows.length);
  const stale = sheetData(previewSheets, "staleTasks", staleRows, staleRows.length);
  const apiKpis = trend.kpis;
  const kpis =
    apiKpis !== undefined
      ? [
          { label: t("analytics.created"), value: apiKpis.created },
          { label: t("analytics.closed"), value: apiKpis.closed },
          { label: t("analytics.active"), value: apiKpis.active },
          { label: t("analytics.overdue"), value: apiKpis.overdue },
          { label: t("analytics.stale"), value: apiKpis.stale },
        ]
      : summary
        ? [
            { label: t("analytics.created"), value: summary.tasks_created },
            { label: t("analytics.closed"), value: summary.tasks_closed },
            { label: t("analytics.active"), value: summary.active_tasks },
            { label: t("analytics.overdue"), value: summary.overdue_tasks },
            { label: t("analytics.stale"), value: summary.stale_tasks },
          ]
        : undefined;

  return [
    makeSheet({
      id: "summary",
      tabLabel: sheet(t, "summary"),
      sheetTitle: sheet(t, "summary"),
      kpis,
      headers: [
        col(t, "week"),
        col(t, "created"),
        col(t, "closed"),
        col(t, "carriedOver"),
      ],
      rows: trend.rows,
      totalRows: trend.total,
      chart:
        trend.rows.length > 0
          ? {
              title: chartTitle(t, "weeklyTrend"),
              option: weeklyTrendOption(
                snapshot.weeklyTrend.filter(
                  (item) => item.created > 0 || item.closed > 0 || item.carried_over > 0,
                ),
                weekLabelFn,
              ),
              size: "lg",
            }
          : undefined,
    }),
    makeSheet({
      id: "byTags",
      tabLabel: sheet(t, "byTags"),
      sheetTitle: sheet(t, "byTags"),
      headers: [col(t, "tag"), col(t, "count")],
      rows: tags.rows,
      totalRows: tags.total,
      chart:
        tagRows.length > 0
          ? {
              title: chartTitle(t, "byTags"),
              option: breakdownDonutOption(snapshot.tagBreakdown.filter((item) => item.count > 0)),
              size: "donut",
            }
          : undefined,
    }),
    makeSheet({
      id: "byColumns",
      tabLabel: sheet(t, "byColumns"),
      sheetTitle: sheet(t, "byColumns"),
      headers: [col(t, "column"), col(t, "systemType"), col(t, "count")],
      rows: columns.rows,
      totalRows: columns.total,
      chart:
        columns.rows.length > 0
          ? {
              title: chartTitle(t, "byColumns"),
              option: weeklyColumnOption(
                snapshot.columnBreakdown
                  .filter((item) => item.count > 0)
                  .map((item) => ({ key: columnBreakdownLabel(item), count: item.count })),
                CHART_COLORS.primary,
              ),
              size: "md",
            }
          : undefined,
    }),
    makeSheet({
      id: "staleTasks",
      tabLabel: sheet(t, "staleTasks"),
      sheetTitle: sheet(t, "staleTasks"),
      headers: [col(t, "id"), col(t, "title"), col(t, "column"), col(t, "daysInColumn")],
      rows: stale.rows,
      totalRows: stale.total,
    }),
  ];
}

export function buildPreviewDocument(
  exportType: ExportType,
  fileFormat: ExportFormat,
  snapshot: ExportSnapshot,
  t: ComposerTranslation,
  weekLabelFn: (week: string) => string,
  previewSheets?: ExportPreviewSheetsMap,
): PreviewDocumentModel {
  const meta = baseMeta(exportType, snapshot, t, weekLabelFn);
  const isStyledExport = fileFormat === "xlsx" || fileFormat === "pdf";

  if (exportType === "weekly_summary") {
    const sheets = weeklySummarySheets(snapshot, t, weekLabelFn, previewSheets).map((sheet) =>
      isStyledExport ? sheet : { ...sheet, chart: undefined },
    );
    return {
      meta,
      sheets: isStyledExport ? sheets : [sheets[0]],
      showTabs: isStyledExport,
    };
  }

  if (exportType === "tag_summary") {
    const fallbackRows = snapshot.tagBreakdown
      .filter((item) => item.count > 0)
      .map((item) => [item.key, String(item.count)]);
    const tags = sheetData(previewSheets, "tags", fallbackRows, fallbackRows.length);
    return {
      meta,
      showTabs: false,
      sheets: [
        makeSheet({
          id: "tags",
          tabLabel: sheet(t, "tags"),
          sheetTitle: sheet(t, "tags"),
          headers: [col(t, "tag"), col(t, "count")],
          rows: tags.rows,
          totalRows: tags.total,
          chart:
            isStyledExport && tags.rows.length > 0
              ? {
                  title: chartTitle(t, "tagDistribution"),
                  option: breakdownDonutOption(snapshot.tagBreakdown.filter((item) => item.count > 0)),
                  size: "donut",
                }
              : undefined,
        }),
      ],
    };
  }

  if (exportType === "tasks") {
    const overviewRows = breakdownRows(snapshot.columnBreakdown);
    const overview = sheetData(previewSheets, "overview", overviewRows, overviewRows.length);
    const tasks = sheetData(previewSheets, "tasks", [], 0);
    const sheets: PreviewSheetModel[] = [];

    if (isStyledExport && overview.rows.length > 0) {
      sheets.push(
        makeSheet({
          id: "overview",
          tabLabel: sheet(t, "overview"),
          sheetTitle: sheet(t, "overview"),
          headers: [col(t, "column"), col(t, "count")],
          rows: overview.rows,
          totalRows: overview.total,
          chart: {
            title: chartTitle(t, "columnDistribution"),
            option: breakdownChartOption(
              snapshot.columnBreakdown
                .filter((item) => item.count > 0)
                .map((item) => ({ key: columnBreakdownLabel(item), count: item.count })),
              CHART_COLORS.primary,
            ),
            size: "donut",
          },
        }),
      );
    }

    sheets.push(
      makeSheet({
        id: "tasks",
        tabLabel: sheet(t, "tasks"),
        sheetTitle: sheet(t, "tasks"),
        headers: [
          col(t, "id"),
          col(t, "title"),
          col(t, "column"),
          col(t, "systemType"),
          col(t, "week"),
          col(t, "tags"),
          col(t, "source"),
          col(t, "dueAt"),
          col(t, "createdAt"),
          col(t, "closedAt"),
          col(t, "archivedAt"),
        ],
        rows: tasks.rows,
        totalRows: tasks.total,
      }),
    );

    return { meta, sheets, showTabs: isStyledExport && sheets.length > 1 };
  }

  if (exportType === "archive") {
    const closed = snapshot.archiveStats?.closed_by_week.filter((item) => item.count > 0) ?? [];
    const overviewRows =
      closed.length > 0
        ? closed.map((item) => [weekLabelFn(item.week), String(item.count)])
        : breakdownRows(snapshot.columnBreakdown);
    const overview = sheetData(previewSheets, "overview", overviewRows, overviewRows.length);
    const archive = sheetData(previewSheets, "archive", [], 0);
    const sheets: PreviewSheetModel[] = [];

    if (isStyledExport && overview.rows.length > 0) {
      sheets.push(
        makeSheet({
          id: "overview",
          tabLabel: sheet(t, "overview"),
          sheetTitle: sheet(t, "overview"),
          headers:
            closed.length > 0
              ? [col(t, "week"), col(t, "count")]
              : [col(t, "column"), col(t, "count")],
          rows: overview.rows,
          totalRows: overview.total,
          chart:
            closed.length > 0
              ? {
                  title: chartTitle(t, "closedByWeek"),
                  option: weeklyColumnOption(
                    closed.map((item) => ({ key: weekLabelFn(item.week), count: item.count })),
                    CHART_COLORS.accent,
                  ),
                  size: "md",
                }
              : {
                  title: chartTitle(t, "columnDistribution"),
                  option: breakdownChartOption(
                    snapshot.columnBreakdown
                      .filter((item) => item.count > 0)
                      .map((item) => ({ key: columnBreakdownLabel(item), count: item.count })),
                    CHART_COLORS.primary,
                  ),
                  size: "donut",
                },
        }),
      );
    }

    sheets.push(
      makeSheet({
        id: "archive",
        tabLabel: sheet(t, "archive"),
        sheetTitle: sheet(t, "archive"),
        headers: [
          col(t, "id"),
          col(t, "title"),
          col(t, "column"),
          col(t, "systemType"),
          col(t, "week"),
          col(t, "tags"),
          col(t, "source"),
          col(t, "dueAt"),
          col(t, "createdAt"),
          col(t, "closedAt"),
          col(t, "archivedAt"),
          col(t, "completionNote"),
        ],
        rows: archive.rows,
        totalRows: archive.total,
      }),
    );

    return { meta, sheets, showTabs: isStyledExport && sheets.length > 1 };
  }

  if (exportType === "notification_report") {
    const actions = snapshot.notifications?.telegram_actions.filter((item) => item.count > 0) ?? [];
    const actionRows = actions.map((action) => [
      telegramActionLabel(action.slug),
      String(action.count),
    ]);
    const fallbackOverviewRows =
      actionRows.length > 0
        ? actionRows
        : snapshot.notifications
          ? [
              [t("analytics.sent"), String(snapshot.notifications.notifications_sent)],
              [t("analytics.failures"), String(snapshot.notifications.notification_failures)],
              [
                t("analytics.closedAfter"),
                String(snapshot.notifications.tasks_closed_after_notification),
              ],
            ]
          : [];
    const overview = sheetData(
      previewSheets,
      "overview",
      fallbackOverviewRows,
      fallbackOverviewRows.length,
    );
    const notifications = sheetData(previewSheets, "notifications", [], 0);
    const sheets: PreviewSheetModel[] = [];

    if (isStyledExport && overview.rows.length > 0) {
      sheets.push(
        makeSheet({
          id: "overview",
          tabLabel: sheet(t, "overview"),
          sheetTitle: sheet(t, "overview"),
          headers: [col(t, "status"), col(t, "count")],
          rows: overview.rows,
          totalRows: overview.total,
          chart:
            actionRows.length > 0
              ? {
                  title: chartTitle(t, "telegramActions"),
                  option: telegramActionsOption(actions),
                  size: "donut",
                }
              : snapshot.notifications
                ? {
                    title: chartTitle(t, "notifications"),
                    option: notificationsOption(snapshot.notifications),
                    size: "donut",
                  }
                : undefined,
        }),
      );
    }

    sheets.push(
      makeSheet({
        id: "notifications",
        tabLabel: sheet(t, "notifications"),
        sheetTitle: sheet(t, "notifications"),
        headers: [
          col(t, "id"),
          col(t, "taskId"),
          col(t, "taskTitle"),
          col(t, "status"),
          col(t, "reason"),
          col(t, "telegramChat"),
          col(t, "scheduledAt"),
          col(t, "sentAt"),
          col(t, "failedAt"),
          col(t, "lastError"),
        ],
        rows: notifications.rows,
        totalRows: notifications.total,
      }),
    );

    return { meta, sheets, showTabs: isStyledExport && sheets.length > 1 };
  }

  if (exportType === "jobs_report") {
    const overview = sheetData(previewSheets, "overview", [], 0);
    const jobs = sheetData(previewSheets, "jobs", [], 0);
    const sheets: PreviewSheetModel[] = [];
    if (isStyledExport && overview.rows.length > 0) {
      sheets.push(
        makeSheet({
          id: "overview",
          tabLabel: sheet(t, "overview"),
          sheetTitle: sheet(t, "overview"),
          headers: [col(t, "status"), col(t, "count")],
          rows: overview.rows,
          totalRows: overview.total,
        }),
      );
    }
    sheets.push(
      makeSheet({
        id: "jobs",
        tabLabel: sheet(t, "jobs"),
        sheetTitle: sheet(t, "jobs"),
        headers: [
          col(t, "id"),
          col(t, "jobType"),
          col(t, "status"),
          col(t, "attempts"),
          col(t, "scheduledAt"),
          col(t, "startedAt"),
          col(t, "finishedAt"),
          col(t, "lastError"),
          col(t, "createdAt"),
        ],
        rows: jobs.rows,
        totalRows: jobs.total,
      }),
    );
    return { meta, sheets, showTabs: isStyledExport && sheets.length > 1 };
  }

  if (exportType === "imports_report") {
    const overview = sheetData(previewSheets, "overview", [], 0);
    const imports = sheetData(previewSheets, "imports", [], 0);
    const sheets: PreviewSheetModel[] = [];
    if (isStyledExport && overview.rows.length > 0) {
      sheets.push(
        makeSheet({
          id: "overview",
          tabLabel: sheet(t, "overview"),
          sheetTitle: sheet(t, "overview"),
          headers: [col(t, "status"), col(t, "count")],
          rows: overview.rows,
          totalRows: overview.total,
        }),
      );
    }
    sheets.push(
      makeSheet({
        id: "imports",
        tabLabel: sheet(t, "imports"),
        sheetTitle: sheet(t, "imports"),
        headers: [
          col(t, "id"),
          col(t, "filename"),
          col(t, "status"),
          col(t, "tasksCreated"),
          col(t, "sourceLabel"),
          col(t, "errorMessage"),
          col(t, "startedAt"),
          col(t, "finishedAt"),
          col(t, "createdAt"),
        ],
        rows: imports.rows,
        totalRows: imports.total,
      }),
    );
    return { meta, sheets, showTabs: isStyledExport && sheets.length > 1 };
  }

  return { meta, sheets: [], showTabs: false };
}
