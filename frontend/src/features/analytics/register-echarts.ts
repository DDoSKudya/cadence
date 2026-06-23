// Full ECharts bundle — avoids subpath imports (echarts/charts) that break when
// node_modules is stale or incomplete in Docker volumes.
import "echarts";

export const CHART_COLORS = {
  primary: "#5b6ee8",
  primarySoft: "#a5b0f5",
  accent: "#4a7fd6",
  accentSoft: "#93b4f0",
  warn: "#f59e0b",
  danger: "#ef4444",
  slate: "#64748b",
  violet: "#8b5cf6",
  indigo: "#6366f1",
  text: "#5c6478",
  grid: "#e8ebf0",
};
