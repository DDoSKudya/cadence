<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";

import AnalyticsChart from "@/features/analytics/components/AnalyticsChart.vue";
import { buildPreviewDocument } from "@/features/analytics/export-preview-sheets";
import type { ExportPreviewSheetsMap, ExportSnapshot, ExportType } from "@/features/analytics/types";
import { weekLabel } from "@/lib/week";

const props = defineProps<{
  exportType: ExportType;
  fileFormat: "csv" | "xlsx" | "pdf";
  snapshot: ExportSnapshot;
  previewSheets?: ExportPreviewSheetsMap;
}>();

const { t } = useI18n();
const activeSheetId = ref("");

function safeWeekLabel(week: string): string {
  try {
    return weekLabel(week);
  } catch {
    return week;
  }
}

const documentModel = computed(() =>
  buildPreviewDocument(
    props.exportType,
    props.fileFormat,
    props.snapshot,
    t,
    safeWeekLabel,
    props.previewSheets,
  ),
);

const activeSheet = computed(
  () =>
    documentModel.value.sheets.find((sheet) => sheet.id === activeSheetId.value) ??
    documentModel.value.sheets[0] ??
    null,
);

watch(
  () => props.exportType,
  () => {
    activeSheetId.value = documentModel.value.sheets[0]?.id ?? "";
  },
  { immediate: true },
);

watch(
  () => documentModel.value.sheets,
  (sheets) => {
    if (!sheets.some((sheet) => sheet.id === activeSheetId.value)) {
      activeSheetId.value = sheets[0]?.id ?? "";
    }
  },
);
</script>

<template>
  <div class="export-preview">
    <div class="export-workbook">
    <div class="export-workbook-viewport">
      <Transition name="export-sheet-swap" mode="out-in">
        <article v-if="activeSheet" :key="activeSheet.id" class="export-worksheet">
          <h3 class="export-worksheet-title">{{ activeSheet.sheetTitle }}</h3>

          <div class="export-worksheet-body">
          <div class="export-worksheet-meta-wrap">
          <table class="export-worksheet-meta" aria-label="metadata">
            <tbody>
              <tr>
                <th scope="row">{{ $t("analytics.exportDoc.meta.brand") }}</th>
                <td>{{ documentModel.meta.reportTitle }}</td>
              </tr>
              <tr v-if="documentModel.meta.schemeName">
                <th scope="row">{{ $t("analytics.exportDoc.meta.scheme") }}</th>
                <td>{{ documentModel.meta.schemeName }}</td>
              </tr>
              <tr>
                <th scope="row">{{ $t("analytics.exportDoc.meta.period") }}</th>
                <td>{{ documentModel.meta.periodLabel }}</td>
              </tr>
              <tr>
                <th scope="row">{{ $t("analytics.exportDoc.meta.generatedAt") }}</th>
                <td>{{ documentModel.meta.generatedAt }}</td>
              </tr>
            </tbody>
          </table>
          </div>

          <table v-if="activeSheet.kpis?.length" class="export-worksheet-kpis" aria-label="KPI">
            <thead>
              <tr>
                <th v-for="kpi in activeSheet.kpis" :key="kpi.label" scope="col">
                  {{ kpi.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td v-for="kpi in activeSheet.kpis" :key="kpi.label">{{ kpi.value }}</td>
              </tr>
            </tbody>
          </table>

          <div class="export-worksheet-table-wrap">
            <table class="export-worksheet-table">
              <thead>
                <tr>
                  <th v-for="header in activeSheet.headers" :key="header" scope="col">
                    {{ header }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in activeSheet.rows" :key="rowIndex">
                  <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
                </tr>
                <tr v-if="!activeSheet.rows.length && !activeSheet.hiddenRows">
                  <td :colspan="activeSheet.headers.length" class="export-worksheet-empty">
                    {{ $t("analytics.exportDoc.table.noData") }}
                  </td>
                </tr>
                <tr v-if="activeSheet.hiddenRows">
                  <td :colspan="activeSheet.headers.length" class="export-worksheet-more">
                    {{
                      $t("analytics.exportPreview.moreRows", { count: activeSheet.hiddenRows })
                    }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="activeSheet.chart" class="export-worksheet-chart">
            <p class="export-worksheet-chart-title">{{ activeSheet.chart.title }}</p>
            <div
              class="export-worksheet-chart-canvas"
              :class="`export-worksheet-chart-canvas--${activeSheet.chart.size}`"
            >
              <AnalyticsChart :option="activeSheet.chart.option" :size="activeSheet.chart.size" />
            </div>
          </div>

          <p class="export-worksheet-footnote">{{ $t("analytics.exportPreview.footnote") }}</p>
          </div>
        </article>
      </Transition>
    </div>

    <div
      v-if="documentModel.showTabs && documentModel.sheets.length > 1"
      class="export-workbook-tabs"
      role="tablist"
    >
      <button
        v-for="sheet in documentModel.sheets"
        :key="sheet.id"
        class="export-workbook-tab"
        :class="{ 'export-workbook-tab-active': sheet.id === activeSheetId }"
        type="button"
        role="tab"
        :aria-selected="sheet.id === activeSheetId"
        @click="activeSheetId = sheet.id"
      >
        {{ sheet.tabLabel }}
      </button>
    </div>
    </div>
  </div>
</template>
