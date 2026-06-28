from __future__ import annotations

import base64
import io
from typing import Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from apps.analytics.export_i18n import et
from apps.analytics.xlsx_builder import SheetChartSpec

ChartCanvasSize = Literal["md", "lg", "donut"]

COLOR_PRIMARY = "#5b6ee8"
COLOR_ACCENT = "#4a7fd6"
COLOR_WARN = "#f59e0b"
COLOR_VIOLET = "#8b5cf6"
COLOR_INDIGO = "#6366f1"
COLOR_SLATE = "#64748b"
COLOR_TEXT = "#5c6478"
COLOR_GRID = "#e8ebf0"

PIE_PALETTE = [
    COLOR_PRIMARY,
    COLOR_ACCENT,
    COLOR_VIOLET,
    COLOR_INDIGO,
    COLOR_WARN,
    COLOR_SLATE,
]


def _truncate(value: str, max_len: int = 20) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[: max_len - 1]}…"


def _figure_size(kind: str) -> tuple[float, float]:
    if kind == "weekly_combo":
        return (11.0, 4.8)
    if kind == "pie":
        return (9.5, 4.5)
    return (10.0, 4.2)


def _style_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.tick_params(colors=COLOR_TEXT, labelsize=8)
    ax.grid(axis="y", color=COLOR_GRID, linestyle="--", linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)


def _weekly_combo_chart(
    rows: list[list],
    locale: str,
    title: str,
) -> tuple[bytes, ChartCanvasSize]:
    labels = [str(row[0]) for row in rows]
    created = [float(row[1]) for row in rows]
    closed = [float(row[2]) for row in rows]
    carried = [float(row[3]) for row in rows if len(row) > 3]

    fig, ax1 = plt.subplots(figsize=_figure_size("weekly_combo"))
    x = range(len(labels))
    width = 0.35
    ax1.bar(
        [index - width / 2 for index in x],
        created,
        width,
        label=et("export.kpi.created", locale=locale),
        color=COLOR_PRIMARY,
        edgecolor="white",
        linewidth=0.6,
        zorder=2,
    )
    ax1.bar(
        [index + width / 2 for index in x],
        closed,
        width,
        label=et("export.kpi.closed", locale=locale),
        color=COLOR_ACCENT,
        edgecolor="white",
        linewidth=0.6,
        zorder=2,
    )
    if carried:
        ax2 = ax1.twinx()
        ax2.plot(
            list(x),
            carried,
            color=COLOR_WARN,
            marker="o",
            markersize=4,
            linewidth=1.8,
            label=et("export.col.carriedOver", locale=locale),
            zorder=3,
        )
        ax2.tick_params(colors=COLOR_TEXT, labelsize=8)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_color(COLOR_GRID)
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(
            lines1 + lines2,
            labels1 + labels2,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.14),
            ncol=3,
            fontsize=7,
            frameon=False,
        )
    else:
        ax1.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.14),
            ncol=2,
            fontsize=7,
            frameon=False,
        )
    ax1.set_xticks(list(x))
    ax1.set_xticklabels([_truncate(label, 12) for label in labels], fontsize=8)
    _style_axes(ax1)
    ax1.set_title(title, fontsize=10, color="#334155", pad=8)
    fig.tight_layout()
    return _figure_png(fig), "lg"


def _pie_chart(
    rows: list[list], title: str, *, locale: str
) -> tuple[bytes, ChartCanvasSize]:
    labels, values = _chart_pairs(rows)
    total = sum(values)

    fig, ax = plt.subplots(figsize=_figure_size("pie"))
    colors = PIE_PALETTE[: len(values)]
    wedges = ax.pie(
        values,
        labels=None,
        colors=colors,
        startangle=90,
        wedgeprops={"linewidth": 1.2, "edgecolor": "white"},
    )[0]
    centre_circle = plt.Circle((0, 0), 0.55, fc="white")
    ax.add_artist(centre_circle)
    ax.text(
        0,
        0.05,
        str(int(total)),
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color="#161b26",
    )
    ax.text(
        0,
        -0.18,
        et("export.total", locale=locale),
        ha="center",
        va="center",
        fontsize=7,
        color=COLOR_TEXT,
    )
    legend_labels = []
    for label, value in zip(labels, values, strict=True):
        pct = round(value / total * 100) if total else 0
        legend_labels.append(f"{_truncate(label, 14)} · {int(value)} ({pct}%)")
    side = len(values) <= 4
    if side:
        ax.legend(
            wedges,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            fontsize=7,
            frameon=False,
        )
    else:
        ax.legend(
            wedges,
            legend_labels,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.08),
            ncol=2,
            fontsize=7,
            frameon=False,
        )
    ax.set_title(title, fontsize=10, color="#334155", pad=8)
    fig.tight_layout()
    return _figure_png(fig), "donut"


def _chart_pairs(rows: list[list]) -> tuple[list[str], list[float]]:
    labels: list[str] = []
    values: list[float] = []
    for row in rows:
        if len(row) >= 3:
            labels.append(str(row[0]))
            values.append(float(row[2]))
        elif len(row) >= 2:
            labels.append(str(row[0]))
            values.append(float(row[1]))
    return labels, values


def _bar_col_chart(
    rows: list[list], title: str, color: str = COLOR_PRIMARY
) -> tuple[bytes, ChartCanvasSize]:
    labels, values = _chart_pairs(rows)
    rotate = len(labels) > 5

    fig, ax = plt.subplots(figsize=_figure_size("bar_col"))
    bars = ax.bar(
        range(len(labels)),
        values,
        color=color,
        edgecolor="white",
        linewidth=0.6,
        width=0.65,
    )
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.02,
            str(int(value)),
            ha="center",
            va="bottom",
            fontsize=7,
            color=COLOR_TEXT,
        )
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(
        [_truncate(label, 16) for label in labels],
        rotation=24 if rotate else 0,
        ha="right" if rotate else "center",
        fontsize=8,
    )
    _style_axes(ax)
    ax.set_title(title, fontsize=10, color="#334155", pad=8)
    fig.tight_layout()
    return _figure_png(fig), "md"


def _figure_png(fig: plt.Figure) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buffer.getvalue()


def render_chart_image(
    spec: SheetChartSpec,
    rows: list[list],
    *,
    locale: str,
) -> tuple[str, ChartCanvasSize] | None:
    if not rows:
        return None
    title = et(spec.title_key, locale=locale)
    if spec.kind == "weekly_combo":
        if len(rows[0]) < 4:
            return None
        png, size = _weekly_combo_chart(rows, locale, title)
    elif spec.kind == "pie":
        if len(rows[0]) < 2:
            return None
        if len(rows) > 8:
            png, size = _bar_horizontal_chart(rows, title, COLOR_PRIMARY)
        else:
            png, size = _pie_chart(rows, title, locale=locale)
    else:
        if len(rows[0]) < 2:
            return None
        color = COLOR_ACCENT if "closed" in spec.title_key.lower() else COLOR_PRIMARY
        png, size = _bar_col_chart(rows, title, color=color)
    encoded = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{encoded}", size


def _bar_horizontal_chart(
    rows: list[list], title: str, color: str
) -> tuple[bytes, ChartCanvasSize]:
    labels, values = _chart_pairs(rows)
    sorted_pairs = sorted(zip(labels, values, strict=True), key=lambda item: item[1])
    labels = [item[0] for item in sorted_pairs]
    values = [item[1] for item in sorted_pairs]

    fig, ax = plt.subplots(figsize=(10.0, max(3.5, len(labels) * 0.42)))
    bars = ax.barh(range(len(labels)), values, color=color, height=0.55)
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_width() + max(values) * 0.02,
            bar.get_y() + bar.get_height() / 2,
            str(int(value)),
            va="center",
            fontsize=7,
            color=COLOR_TEXT,
        )
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels([_truncate(label, 20) for label in labels], fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.tick_params(colors=COLOR_TEXT, labelsize=8)
    ax.grid(axis="x", color=COLOR_GRID, linestyle="--", linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)
    ax.set_title(title, fontsize=10, color="#334155", pad=8)
    fig.tight_layout()
    return _figure_png(fig), "md"
