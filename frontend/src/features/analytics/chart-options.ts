import type { EChartsOption } from "echarts";

import type { BreakdownItem, StaleTaskItem, WeeklyTrendItem } from "@/features/analytics/types";
import { cycleBucketLabel, telegramActionLabel } from "@/features/analytics/labels";
import { t } from "@/i18n";

import { CHART_COLORS } from "./register-echarts";

const PALETTE = [
  CHART_COLORS.primary,
  CHART_COLORS.accent,
  CHART_COLORS.violet,
  CHART_COLORS.indigo,
  CHART_COLORS.warn,
  CHART_COLORS.slate,
];

const baseTooltip = {
  trigger: "axis" as const,
  backgroundColor: "#ffffff",
  borderColor: CHART_COLORS.grid,
  textStyle: { color: "#161b26", fontSize: 12 },
};

const itemTooltip = {
  trigger: "item" as const,
  backgroundColor: "#ffffff",
  borderColor: CHART_COLORS.grid,
  textStyle: { color: "#161b26", fontSize: 12 },
};

function truncateLabel(value: string, max = 22): string {
  if (value.length <= max) {
    return value;
  }
  return `${value.slice(0, max - 1)}…`;
}

function percentOf(value: number, total: number): number {
  if (total <= 0) {
    return 0;
  }
  return Math.round((value / total) * 100);
}

function legendLine(name: string, count: number, total: number): string {
  return `${truncateLabel(name, 14)} · ${count} (${percentOf(count, total)}%)`;
}

const DONUT_CENTER_RICH = {
  value: {
    fontSize: 18,
    fontWeight: 600,
    color: "#161b26",
    lineHeight: 22,
    align: "center" as const,
  },
  hint: {
    fontSize: 10,
    color: CHART_COLORS.text,
    lineHeight: 14,
    align: "center" as const,
  },
};

function donutCenterFormatter(total: number): string {
  return `{value|${total}}\n{hint|${t("analytics.total").toLowerCase()}}`;
}

function donutCenterLabel(total: number) {
  const formatter = () => donutCenterFormatter(total);
  return {
    show: true,
    position: "center" as const,
    formatter,
    rich: DONUT_CENTER_RICH,
  };
}

function donutEmphasisLabel(total: number) {
  return {
    scale: true,
    scaleSize: 4,
    label: {
      show: true,
      formatter: () => donutCenterFormatter(total),
      rich: DONUT_CENTER_RICH,
    },
  };
}

export function weeklyTrendOption(
  items: WeeklyTrendItem[],
  weekLabel: (week: string) => string,
): EChartsOption {
  return {
    color: [CHART_COLORS.primary, CHART_COLORS.accent, CHART_COLORS.warn],
    tooltip: baseTooltip,
    legend: {
      bottom: 0,
      itemWidth: 10,
      itemHeight: 8,
      itemGap: 16,
      textStyle: { color: CHART_COLORS.text, fontSize: 11 },
    },
    grid: { left: 8, right: 8, top: 12, bottom: 40, containLabel: true },
    xAxis: {
      type: "category",
      data: items.map((item) => weekLabel(item.week)),
      axisLine: { lineStyle: { color: CHART_COLORS.grid } },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      splitLine: { lineStyle: { color: CHART_COLORS.grid, type: "dashed" } },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
    },
    series: [
      {
        name: t("analytics.created"),
        type: "bar",
        barMaxWidth: 20,
        itemStyle: { borderRadius: [3, 3, 0, 0] },
        data: items.map((item) => item.created),
      },
      {
        name: t("analytics.closed"),
        type: "bar",
        barMaxWidth: 20,
        itemStyle: { borderRadius: [3, 3, 0, 0] },
        data: items.map((item) => item.closed),
      },
      {
        name: t("analytics.carriedOver"),
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        lineStyle: { width: 2, color: CHART_COLORS.warn },
        itemStyle: { color: CHART_COLORS.warn },
        data: items.map((item) => item.carried_over),
      },
    ],
  };
}

export function breakdownBarOption(
  items: BreakdownItem[],
  color: string,
  valueSuffix = "",
): EChartsOption {
  const sorted = [...items].filter((item) => item.count > 0).sort((a, b) => a.count - b.count);
  if (sorted.length === 0) {
    return {};
  }
  return {
    color: [color],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "#ffffff",
      borderColor: CHART_COLORS.grid,
      textStyle: { color: "#161b26", fontSize: 12 },
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params;
        if (!point || typeof point.value !== "number") {
          return "";
        }
        return `${point.name}: <strong>${point.value}</strong>${valueSuffix}`;
      },
    },
    grid: { left: 4, right: 32, top: 4, bottom: 4, containLabel: true },
    xAxis: {
      type: "value",
      minInterval: 1,
      splitLine: { lineStyle: { color: CHART_COLORS.grid, type: "dashed" } },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
    },
    yAxis: {
      type: "category",
      data: sorted.map((item) => truncateLabel(item.key, 20)),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
    },
    series: [
      {
        type: "bar",
        barWidth: 12,
        itemStyle: { borderRadius: [0, 4, 4, 0] },
        label: {
          show: true,
          position: "right",
          color: CHART_COLORS.text,
          fontSize: 10,
          distance: 4,
        },
        data: sorted.map((item) => item.count),
      },
    ],
  };
}

export function weeklyColumnOption(
  items: { key: string; count: number }[],
  color: string,
): EChartsOption {
  const filtered = items.filter((item) => item.count > 0);
  if (filtered.length === 0) {
    return {};
  }
  return {
    color: [color],
    tooltip: baseTooltip,
    grid: {
      left: 8,
      right: 8,
      top: 12,
      bottom: filtered.length > 5 ? 28 : 20,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: filtered.map((item) => item.key),
      axisLine: { lineStyle: { color: CHART_COLORS.grid } },
      axisLabel: {
        color: CHART_COLORS.text,
        fontSize: 10,
        rotate: filtered.length > 5 ? 24 : 0,
      },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      splitLine: { lineStyle: { color: CHART_COLORS.grid, type: "dashed" } },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
    },
    series: [
      {
        type: "bar",
        barMaxWidth: 32,
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        data: filtered.map((item) => item.count),
      },
    ],
  };
}

export function breakdownDonutOption(
  items: BreakdownItem[],
  colors: string[] = PALETTE,
): EChartsOption {
  const data = items.filter((item) => item.count > 0);
  if (data.length === 0) {
    return {};
  }
  const total = data.reduce((sum, item) => sum + item.count, 0);
  const sideLegend = data.length <= 4;
  const pieCenterX = sideLegend ? "36%" : "50%";

  return {
    color: colors,
    tooltip: {
      ...itemTooltip,
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params;
        if (!point || typeof point.value !== "number") {
          return "";
        }
        return `${point.name}: <strong>${point.value}</strong> (${percentOf(point.value, total)}%)`;
      },
    },
    legend: {
      orient: sideLegend ? "vertical" : "horizontal",
      right: sideLegend ? 0 : undefined,
      left: sideLegend ? undefined : "center",
      top: sideLegend ? "middle" : undefined,
      bottom: sideLegend ? undefined : 0,
      type: data.length > 5 ? "scroll" : "plain",
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 8,
      textStyle: { color: CHART_COLORS.text, fontSize: 10, lineHeight: 14 },
      formatter: (name: string) => {
        const item = data.find((entry) => entry.key === name);
        if (!item) {
          return name;
        }
        return legendLine(name, item.count, total);
      },
    },
    series: [
      {
        type: "pie",
        radius: sideLegend ? ["54%", "72%"] : ["42%", "58%"],
        center: [pieCenterX, "50%"],
        itemStyle: { borderRadius: 3, borderColor: "#fff", borderWidth: 2 },
        label: donutCenterLabel(total),
        emphasis: donutEmphasisLabel(total),
        labelLine: { show: false },
        minAngle: 10,
        data: data.map((item) => ({ name: item.key, value: item.count })),
      },
    ],
  };
}

export function breakdownChartOption(
  items: BreakdownItem[],
  color: string,
): EChartsOption {
  const filtered = items.filter((item) => item.count > 0);
  if (filtered.length === 0) {
    return {};
  }
  if (filtered.length <= 8) {
    return breakdownDonutOption(filtered);
  }
  return breakdownBarOption(filtered, color);
}

export function distributionOption(
  buckets: { bucket: string; count: number }[],
): EChartsOption {
  const filtered = buckets.filter((item) => item.count > 0);
  if (filtered.length === 0) {
    return {};
  }
  return {
    color: [CHART_COLORS.warn],
    tooltip: baseTooltip,
    grid: { left: 8, right: 8, top: 8, bottom: 20, containLabel: true },
    xAxis: {
      type: "category",
      data: filtered.map((item) => cycleBucketLabel(item.bucket)),
      axisLine: { lineStyle: { color: CHART_COLORS.grid } },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      splitLine: { lineStyle: { color: CHART_COLORS.grid, type: "dashed" } },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
    },
    series: [
      {
        type: "bar",
        barMaxWidth: 36,
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        data: filtered.map((item) => item.count),
      },
    ],
  };
}

export function coverageBarsOption(evidence: number, notes: number): EChartsOption {
  const items = [
    { label: t("analytics.withEvidence"), value: Math.round(evidence * 100), color: CHART_COLORS.accent },
    { label: t("analytics.withNote"), value: Math.round(notes * 100), color: CHART_COLORS.primary },
  ];

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "#ffffff",
      borderColor: CHART_COLORS.grid,
      textStyle: { color: "#161b26", fontSize: 12 },
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params;
        if (!point || typeof point.value !== "number") {
          return "";
        }
        return `${point.name}: <strong>${point.value}%</strong>`;
      },
    },
    grid: { left: 4, right: 36, top: 4, bottom: 4, containLabel: true },
    xAxis: {
      type: "value",
      max: 100,
      splitLine: { lineStyle: { color: CHART_COLORS.grid, type: "dashed" } },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10, formatter: "{value}%" },
    },
    yAxis: {
      type: "category",
      data: items.map((item) => item.label),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
    },
    series: [
      {
        type: "bar",
        barWidth: 14,
        itemStyle: { borderRadius: [0, 4, 4, 0] },
        label: {
          show: true,
          position: "right",
          formatter: "{c}%",
          color: CHART_COLORS.text,
          fontSize: 10,
          distance: 4,
        },
        data: items.map((item) => ({
          value: item.value,
          itemStyle: { color: item.color },
        })),
      },
    ],
  };
}

export function staleTasksOption(items: StaleTaskItem[]): EChartsOption {
  if (items.length === 0) {
    return {};
  }
  return breakdownBarOption(
    [...items]
      .sort((a, b) => b.days_in_column - a.days_in_column)
      .slice(0, 8)
      .map((item) => ({
        key: item.title,
        count: item.days_in_column,
      })),
    CHART_COLORS.warn,
    t("analytics.daysShort"),
  );
}

export function notificationsOption(metrics: {
  notifications_sent: number;
  notification_failures: number;
  tasks_closed_after_notification: number;
}): EChartsOption {
  return breakdownDonutOption(
    [
      { key: t("analytics.sent"), count: metrics.notifications_sent },
      { key: t("analytics.failures"), count: metrics.notification_failures },
      { key: t("analytics.closedAfter"), count: metrics.tasks_closed_after_notification },
    ],
    [CHART_COLORS.primary, CHART_COLORS.danger, CHART_COLORS.accent],
  );
}

export function telegramActionsOption(actions: { slug: string; count: number }[]): EChartsOption {
  if (actions.length === 0) {
    return {};
  }
  return breakdownDonutOption(
    actions.map((action) => ({
      key: telegramActionLabel(action.slug),
      count: action.count,
    })),
    [CHART_COLORS.accent, CHART_COLORS.primarySoft, CHART_COLORS.indigo, CHART_COLORS.violet],
  );
}
