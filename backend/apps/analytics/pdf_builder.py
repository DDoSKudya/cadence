from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

from django.utils import timezone
from weasyprint import CSS, HTML

from apps.analytics.export_i18n import et
from apps.analytics.pdf_charts import ChartCanvasSize, render_chart_image
from apps.analytics.xlsx_builder import ExportMeta, SheetChartSpec

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


@dataclass
class PdfChartBlock:
    title: str
    image_src: str
    size: ChartCanvasSize


@dataclass
class PdfSheetPage:
    sheet_title: str
    headers: list[str]
    rows: list[list[str]]
    kpis: list[tuple[str, str]] | None = None
    chart: PdfChartBlock | None = None
    empty_message: str = ""
    landscape: bool = False


class AnalyticsPdfBuilder:
    def __init__(self, meta: ExportMeta) -> None:
        self.meta = meta

    def save(self, path: Path, sheets: list[tuple]) -> None:
        pages = [self._build_page(sheet) for sheet in sheets]
        stylesheet = (ASSETS_DIR / "export_worksheet.css").read_text(encoding="utf-8")
        document_html = self._render_document(pages)
        html = HTML(string=document_html, base_url=str(ASSETS_DIR))
        html.write_pdf(
            path,
            stylesheets=[CSS(string=stylesheet)],
            optimize_size=(),
        )

    def _build_page(self, sheet: tuple) -> PdfSheetPage:
        sheet_key = sheet[0]
        header_keys = sheet[1]
        rows = sheet[2]
        kpis_raw = sheet[3] if len(sheet) > 3 else None
        charts = sheet[4] if len(sheet) > 4 else None

        headers = [et(key, locale=self.meta.locale) for key in header_keys]
        string_rows = [
            ["" if cell is None else str(cell) for cell in row] for row in rows
        ]
        kpis = None
        if kpis_raw:
            kpis = [
                (et(label_key, locale=self.meta.locale), str(value))
                for label_key, value in kpis_raw
            ]

        chart_block = None
        if charts:
            spec = charts[0]
            if isinstance(spec, SheetChartSpec):
                rendered = render_chart_image(spec, rows, locale=self.meta.locale)
                if rendered is not None:
                    image_src, size = rendered
                    chart_block = PdfChartBlock(
                        title=et(spec.title_key, locale=self.meta.locale),
                        image_src=image_src,
                        size=size,
                    )

        return PdfSheetPage(
            sheet_title=et(sheet_key, locale=self.meta.locale),
            headers=headers,
            rows=string_rows,
            kpis=kpis,
            chart=chart_block,
            empty_message=et("export.table.noData", locale=self.meta.locale),
            landscape=self._use_landscape(headers, string_rows),
        )

    @staticmethod
    def _use_landscape(headers: list[str], rows: list[list[str]]) -> bool:
        if len(headers) >= 6:
            return True
        if rows:
            max_cell = max(len(str(cell)) for row in rows for cell in row)
            if max_cell > 28:
                return True
        return len(headers) >= 5 and len(rows) > 12

    def _render_document(self, pages: list[PdfSheetPage]) -> str:
        body = "\n".join(self._render_page(page) for page in pages)
        locale = html.escape(self.meta.locale)
        return (
            f"<!DOCTYPE html><html lang='{locale}'>"
            "<head><meta charset='utf-8'></head>"
            f"<body>{body}</body></html>"
        )

    def _render_page(self, page: PdfSheetPage) -> str:
        meta_rows = [
            ("export.meta.brand", self.meta.report_title),
            ("export.scheme", self.meta.scheme_name),
            ("export.period", self.meta.period_label),
            ("export.generatedAt", self._format_generated_at()),
        ]
        meta_html = "".join(
            self._meta_row(label_key, value)
            for label_key, value in meta_rows
            if label_key != "export.scheme" or value
        )
        kpi_html = self._render_kpis(page.kpis)
        table_html = self._render_table(page)
        chart_html = self._render_chart(page.chart)
        footnote = et("export.footnote", locale=self.meta.locale)
        page_class = "pdf-page pdf-page--landscape" if page.landscape else "pdf-page"

        return f"""
<section class="{page_class}">
  <article class="export-worksheet">
    <h3 class="export-worksheet-title">{html.escape(page.sheet_title)}</h3>
    <div class="export-worksheet-body">
      <div class="export-worksheet-meta-wrap">
        <table class="export-worksheet-meta">
          <tbody>{meta_html}</tbody>
        </table>
      </div>
      {kpi_html}
      {table_html}
      {chart_html}
      <p class="export-worksheet-footnote">{html.escape(footnote)}</p>
    </div>
  </article>
</section>
"""

    def _meta_row(self, label_key: str, value: str) -> str:
        if not value and label_key == "export.scheme":
            return ""
        label = et(label_key, locale=self.meta.locale)
        return (
            "<tr>"
            f"<th scope='row'>{html.escape(label)}</th>"
            f"<td>{html.escape(value)}</td>"
            "</tr>"
        )

    def _render_kpis(self, kpis: list[tuple[str, str]] | None) -> str:
        if not kpis:
            return ""
        head = "".join(
            f"<th scope='col'>{html.escape(label)}</th>" for label, _ in kpis
        )
        values = "".join(f"<td>{html.escape(value)}</td>" for _, value in kpis)
        return (
            "<table class='export-worksheet-kpis' aria-label='KPI'>"
            f"<thead><tr>{head}</tr></thead>"
            f"<tbody><tr>{values}</tr></tbody>"
            "</table>"
        )

    def _render_table(self, page: PdfSheetPage) -> str:
        head = "".join(
            f"<th scope='col'>{html.escape(header)}</th>" for header in page.headers
        )
        if page.rows:
            body = "".join(
                "<tr>"
                + "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
                + "</tr>"
                for row in page.rows
            )
        else:
            colspan = max(len(page.headers), 1)
            body = (
                "<tr>"
                f"<td colspan='{colspan}' class='export-worksheet-empty'>"
                f"{html.escape(page.empty_message)}"
                "</td></tr>"
            )
        return (
            "<div class='export-worksheet-table-wrap'>"
            "<table class='export-worksheet-table'>"
            f"<thead><tr>{head}</tr></thead>"
            f"<tbody>{body}</tbody>"
            "</table></div>"
        )

    def _render_chart(self, chart: PdfChartBlock | None) -> str:
        if chart is None:
            return ""
        canvas_class = f"export-worksheet-chart-canvas--{chart.size}"
        return (
            "<div class='export-worksheet-chart'>"
            f"<p class='export-worksheet-chart-title'>{html.escape(chart.title)}</p>"
            f"<div class='export-worksheet-chart-canvas {canvas_class}'>"
            f"<img src='{chart.image_src}' alt=''>"
            "</div></div>"
        )

    def _format_generated_at(self) -> str:
        generated = self.meta.generated_at or timezone.now()
        local = timezone.localtime(generated)
        if self.meta.locale == "ru":
            return local.strftime("%d.%m.%Y, %H:%M")
        return local.strftime("%m/%d/%Y, %H:%M")
