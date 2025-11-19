<template>
  <div class="chart-renderer">
    <v-chart
      v-if="validOption"
      class="chart"
      :option="validOption"
      :autoresize="true"
      :style="{ height: chartHeight }"
    />
    <div v-else class="error-message">
      <p class="text-red-500">图表配置无效</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  HeatmapChart,
  FunnelChart
} from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  HeatmapChart,
  FunnelChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent
])

interface Props {
  option: any
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '400px'
})

// 验证图表配置
const validOption = computed(() => {
  if (!props.option || typeof props.option !== 'object') {
    console.error('[ChartRenderer] Invalid option:', props.option)
    return null
  }

  // 验证必要的 ECharts 配置字段
  // ECharts 至少需要 series 或 dataset
  if (!props.option.series && !props.option.dataset) {
    console.error('[ChartRenderer] Missing required ECharts fields (series/dataset):', props.option)
    return null
  }

  return props.option
})

const chartHeight = computed(() => props.height)
</script>

<style scoped>
.chart-renderer {
  width: 100%;
  margin: 1rem 0;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart {
  width: 100%;
}

.error-message {
  padding: 2rem;
  text-align: center;
}
</style>
