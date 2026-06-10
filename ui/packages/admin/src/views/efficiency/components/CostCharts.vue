<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import GlassCard from './GlassCard.vue'
import TooltipIcon from '../../../components/TooltipIcon.vue'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

type ChartOption = { [key: string]: unknown }

defineProps<{
  trendChartOption: ChartOption
  resourceCostOption: ChartOption
  scopeCostOption: ChartOption
  perCapitaOption: ChartOption
  dimensionLabel: string
  dimensionCostNote: string
}>()
</script>

<template>
      <GlassCard>
        <div class="mb-2 flex items-center gap-1">
          <span class="text-sm font-semibold text-slate-900">成本趋势</span>
          <TooltipIcon text="X轴为日期，Y轴为成本（元）。实线为内部成本，虚线为外部成本。" />
        </div>
        <VChart :option="trendChartOption" style="height: 280px; width: 100%" autoresize />
      </GlassCard>

      <div class="grid grid-cols-2 gap-4">
        <GlassCard>
          <div class="mb-2 flex items-center gap-1">
            <span class="text-sm font-semibold text-slate-900">资源类型成本</span>
            <TooltipIcon text="按 LLM、MCP 展示内部成本和外部成本。" />
          </div>
          <VChart :option="resourceCostOption" style="height: 260px; width: 100%" autoresize />
        </GlassCard>
        <GlassCard>
          <div class="mb-2 flex items-center gap-1">
            <span class="text-sm font-semibold text-slate-900">{{ dimensionLabel }}成本</span>
            <TooltipIcon :text="`按${dimensionLabel}归属展示内部成本和外部成本。${dimensionCostNote}`" />
          </div>
          <VChart :option="scopeCostOption" style="height: 260px; width: 100%" autoresize />
          <p class="mt-2 text-xs text-slate-500">{{ dimensionCostNote }}</p>
        </GlassCard>
      </div>

      <GlassCard>
        <div class="mb-2 flex items-center gap-1">
          <span class="text-sm font-semibold text-slate-900">{{ dimensionLabel }}人均成本</span>
          <TooltipIcon :text="`按${dimensionLabel}统计：内部成本 / 有调用记录的人数。${dimensionCostNote}`" />
        </div>
        <VChart :option="perCapitaOption" style="height: 260px; width: 100%" autoresize />
      </GlassCard>
</template>
