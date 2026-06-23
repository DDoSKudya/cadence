<script lang="ts">
import { computed, defineComponent, type PropType } from "vue";
import type { EChartsOption } from "echarts";
import VChart from "vue-echarts";

import "@/features/analytics/register-echarts";

type ChartSize = "sm" | "md" | "lg" | "donut";

export default defineComponent({
  components: { VChart },
  props: {
    option: {
      type: Object as PropType<EChartsOption>,
      required: true,
    },
    size: {
      type: String as PropType<ChartSize>,
      default: "md",
    },
  },
  setup(props) {
    const hasData = computed(() => {
      const series = props.option.series;
      if (!series) {
      return false;
    }
      const list = Array.isArray(series) ? series : [series];
      return list.some((item) => {
        if (!item || !("data" in item) || !Array.isArray(item.data)) {
          return false;
        }
        return item.data.length > 0;
      });
    });

    return { hasData };
  },
});
</script>

<template>
  <VChart
    v-if="hasData"
    class="analytics-chart"
    :class="`analytics-chart--${size}`"
    :option="option"
    autoresize
    :update-options="{ notMerge: true }"
  />
</template>
