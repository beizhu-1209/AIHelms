<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Download, HelpCircle } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkPointComponent,
} from 'echarts/components'
import { request } from '@aihelms/shared/src/api/request'
import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'
import PresetTabs from './components/PresetTabs.vue'
import { formatCost, formatCostShort, formatNumber, formatChange } from './utils'

use([CanvasRenderer, LineChart, PieChart, BarChart, GridComponent, TooltipComponent, LegendComponent, MarkPointComponent])

// --- Types ---
interface CostKpi {
  total_cost: number
  daily_avg_cost: number
  cost_change: number | null
}

interface CostTrendItem {
  date: string
  llm_cost: number
  mcp_cost: number
  is_anomaly?: boolean
}

interface CostComposition {
  by_resource_type: { name: string; value: number }[]
  by_department: { name: string; value: number }[]
}

interface PerCapitaItem {
  department: string
  per_capita_cost: number
}

interface DeptDetailRow {
  department: string
  llm_cost: number
  mcp_cost: number
  total_cost: number
  requests: number
  per_capita_cost: number
  cost_change: number | null
}

interface ModelDetailRow {
  model: string
  requests: number
  tokens: number
  cost: number
  ratio: number
  avg_cost: number
}

interface DateDetailRow {
  date: string
  llm_cost: number
  mcp_cost: number
  total_cost: number
  requests: number
  active_users: number
}

// --- State ---
const TIME_PRESETS = [
  { key: 'month', label: '本月' },
  { key: '7d', label: '近7天' },
  { key: '30d', label: '近30天' },
]

const RESOURCE_TYPES = [
  { key: '', label: '全部' },
  { key: 'llm', label: 'LLM' },
  { key: 'mcp', label: 'MCP' },
]

const DETAIL_TABS = [
  { key: 'department', label: '按部门' },
  { key: 'model', label: '按模型' },
  { key: 'date', label: '按日期' },
] as const

type DetailTab = (typeof DETAIL_TABS)[number]['key']

const activePreset = ref('month')
const resourceType = ref('')
const departmentFilter = ref('')
const activeDetailTab = ref<DetailTab>('department')
const isLoading = ref(true)
const isDetailLoading = ref(false)
const customStart = ref('')
const customEnd = ref('')

const kpi = ref<CostKpi>({ total_cost: 0, daily_avg_cost: 0, cost_change: null })
const trendData = ref<CostTrendItem[]>([])
const composition = ref<CostComposition>({ by_resource_type: [], by_department: [] })
const perCapita = ref<PerCapitaItem[]>([])
const deptDetail = ref<DeptDetailRow[]>([])
const modelDetail = ref<ModelDetailRow[]>([])
const dateDetail = ref<DateDetailRow[]>([])

// --- Data fetching ---
async function loadOverview() {
  isLoading.value = true
  try {
    const params: Record<string, string> = {}
    if (activePreset.value === 'custom' && customStart.value && customEnd.value) {
      params.start_date = customStart.value
      params.end_date = customEnd.value
    } else {
      params.period = activePreset.value
    }
    if (resourceType.value) params.resource_type = resourceType.value
    if (departmentFilter.value) params.department = departmentFilter.value
    const res = await request<{
      kpi: CostKpi
      trend: CostTrendItem[]
      composition: CostComposition
      per_capita: PerCapitaItem[]
    }>('/api/v1/efficiency/cost', { params })
    kpi.value = res.kpi
    trendData.value = res.trend
    composition.value = res.composition
    perCapita.value = res.per_capita
  } finally {
    isLoading.value = false
  }
  await loadDetail()
}

async function loadDetail() {
  isDetailLoading.value = true
  try {
    const params: Record<string, string> = {
      period: activePreset.value,
      tab: activeDetailTab.value,
    }
    if (resourceType.value) params.resource_type = resourceType.value
    if (departmentFilter.value) params.department = departmentFilter.value
    const res = await request<{
      department?: DeptDetailRow[]
      model?: ModelDetailRow[]
      date?: DateDetailRow[]
    }>('/api/v1/efficiency/cost/detail', { params })
    if (res.department) deptDetail.value = res.department
    if (res.model) modelDetail.value = res.model
    if (res.date) dateDetail.value = res.date
  } finally {
    isDetailLoading.value = false
  }
}

function handlePresetChange(val: string) {
  activePreset.value = val
  loadOverview()
}

function handleResourceChange(val: string) {
  resourceType.value = val
  loadOverview()
}

function handleDetailTabChange(tab: DetailTab) {
  activeDetailTab.value = tab
  loadDetail()
}

// --- Chart options ---
const COLORS = { llm: '#6366f1', mcp: '#10b981', anomaly: '#ef4444' }

const trendChartOption = computed(() => {
  const dates = trendData.value.map((d) => d.date)
  const llmValues = trendData.value.map((d) => d.llm_cost)
  const mcpValues = trendData.value.map((d) => d.mcp_cost)
  const anomalyPoints = trendData.value
    .filter((d) => d.is_anomaly)
    .map((d) => ({ coord: [d.date, d.llm_cost + d.mcp_cost], value: d.llm_cost + d.mcp_cost }))

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['LLM', 'MCP'], bottom: 0 },
    grid: { top: 20, right: 20, bottom: 40, left: 60 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatCostShort(v), fontSize: 10 } },
    series: [
      {
        name: 'LLM', type: 'line', data: llmValues, smooth: true,
        itemStyle: { color: COLORS.llm }, lineStyle: { color: COLORS.llm },
        markPoint: anomalyPoints.length > 0 ? {
          data: anomalyPoints.map((p) => ({
            coord: p.coord, symbol: 'circle', symbolSize: 10,
            itemStyle: { color: COLORS.anomaly, borderColor: '#fff', borderWidth: 2 },
          })),
        } : undefined,
      },
      {
        name: 'MCP', type: 'line', data: mcpValues, smooth: true,
        itemStyle: { color: COLORS.mcp }, lineStyle: { color: COLORS.mcp },
      },
    ],
  }
})

const DONUT_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#a855f7']

const resourceDonutOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  series: [{
    type: 'pie', radius: ['50%', '75%'],
    data: composition.value.by_resource_type.map((d, i) => ({
      name: d.name, value: d.value, itemStyle: { color: DONUT_COLORS[i % DONUT_COLORS.length] },
    })),
    label: { show: true, fontSize: 10 },
  }],
}))

const deptDonutOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  series: [{
    type: 'pie', radius: ['50%', '75%'],
    data: composition.value.by_department.map((d, i) => ({
      name: d.name, value: d.value, itemStyle: { color: DONUT_COLORS[i % DONUT_COLORS.length] },
    })),
    label: { show: true, fontSize: 10 },
  }],
}))

const perCapitaOption = computed(() => {
  const sorted = [...perCapita.value].sort((a, b) => a.per_capita_cost - b.per_capita_cost)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 10, right: 40, bottom: 10, left: 100, containLabel: false },
    xAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatCostShort(v), fontSize: 10 } },
    yAxis: { type: 'category', data: sorted.map((d) => d.department), axisLabel: { fontSize: 10 } },
    series: [{
      type: 'bar', data: sorted.map((d) => d.per_capita_cost),
      itemStyle: { color: '#8b5cf6', borderRadius: [0, 4, 4, 0] },
      barMaxWidth: 20,
    }],
  }
})

onMounted(loadOverview)
</script>

<template>
  <div class="space-y-4">
    <!-- Filter bar -->
    <div class="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200/60 bg-white/70 px-4 py-2.5 shadow-sm backdrop-blur-xl">
      <span class="text-xs text-slate-500">时间</span>
      <PresetTabs :model-value="activePreset" :presets="TIME_PRESETS" @update:model-value="handlePresetChange" />
      <div class="flex items-center gap-1.5">
        <input v-model="customStart" type="date" class="rounded border border-slate-200 px-2 py-1 text-xs" />
        <span class="text-xs text-slate-400">~</span>
        <input v-model="customEnd" type="date" class="rounded border border-slate-200 px-2 py-1 text-xs" />
        <button
          class="rounded bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-100"
          @click="activePreset = 'custom'; loadOverview()"
        >查询</button>
      </div>
      <span class="text-xs text-slate-500">资源类型</span>
      <div class="inline-flex rounded-lg bg-slate-100/80 p-1">
        <button
          v-for="rt in RESOURCE_TYPES" :key="rt.key"
          class="rounded-md px-3 py-1 text-xs transition-colors"
          :class="resourceType === rt.key ? 'bg-white font-medium text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
          @click="handleResourceChange(rt.key)"
        >{{ rt.label }}</button>
      </div>
      <span class="text-xs text-slate-500">部门</span>
      <input
        v-model="departmentFilter"
        class="w-32 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 placeholder-slate-400 focus:border-indigo-300 focus:outline-none"
        placeholder="全部"
        @change="loadOverview()"
      />
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <!-- Content -->
    <template v-if="!isLoading">
      <!-- KPI cards -->
      <div class="grid grid-cols-3 gap-4">
        <KpiCard label="总成本" :value="formatCost(kpi.total_cost)" :change="kpi.cost_change" change-kind="up-bad" />
        <KpiCard label="日均成本" :value="formatCost(kpi.daily_avg_cost)" change-kind="neutral" change-text="" />
        <KpiCard
          label="环比变化"
          :value="formatChange(kpi.cost_change)"
          change-kind="neutral"
          :value-color="kpi.cost_change !== null && kpi.cost_change > 0 ? 'text-red-600' : 'text-emerald-600'"
          change-text=""
        />
      </div>

      <!-- Cost trend chart -->
      <GlassCard>
        <div class="mb-2 flex items-center gap-1">
          <span class="text-sm font-semibold text-slate-900">成本趋势</span>
          <HelpCircle class="h-3.5 w-3.5 text-slate-400" title="X轴为日期，Y轴为成本。蓝线=LLM，绿线=MCP，红点=异常" />
        </div>
        <VChart :option="trendChartOption" style="height: 280px; width: 100%" autoresize />
      </GlassCard>

      <!-- Cost composition (left-right split) -->
      <div class="grid grid-cols-2 gap-4">
        <GlassCard>
          <div class="mb-2 flex items-center gap-1">
            <span class="text-sm font-semibold text-slate-900">按资源类型</span>
            <HelpCircle class="h-3.5 w-3.5 text-slate-400" title="LLM与MCP成本占比" />
          </div>
          <VChart :option="resourceDonutOption" style="height: 240px; width: 100%" autoresize />
        </GlassCard>
        <GlassCard>
          <div class="mb-2 flex items-center gap-1">
            <span class="text-sm font-semibold text-slate-900">按部门</span>
            <HelpCircle class="h-3.5 w-3.5 text-slate-400" title="各部门成本占比" />
          </div>
          <VChart :option="deptDonutOption" style="height: 240px; width: 100%" autoresize />
        </GlassCard>
      </div>

      <!-- Per-capita cost ranking -->
      <GlassCard>
        <div class="mb-2 flex items-center gap-1">
          <span class="text-sm font-semibold text-slate-900">人均成本排名</span>
          <HelpCircle class="h-3.5 w-3.5 text-slate-400" title="按部门人均成本排序" />
        </div>
        <VChart :option="perCapitaOption" style="height: 260px; width: 100%" autoresize />
      </GlassCard>

      <!-- Cost detail table -->
      <GlassCard>
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-1">
            <span class="text-sm font-semibold text-slate-900">成本明细</span>
            <HelpCircle class="h-3.5 w-3.5 text-slate-400" title="按不同维度查看成本明细" />
          </div>
          <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">
            <Download class="h-3.5 w-3.5" /> 导出
          </button>
        </div>
        <!-- Tab switch -->
        <div class="mb-3 flex gap-1 rounded-lg bg-slate-100/80 p-1">
          <button
            v-for="tab in DETAIL_TABS" :key="tab.key"
            class="rounded-md px-3 py-1.5 text-xs transition-colors"
            :class="activeDetailTab === tab.key ? 'bg-white font-medium text-indigo-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'"
            @click="handleDetailTabChange(tab.key)"
          >{{ tab.label }}</button>
        </div>

        <div v-if="isDetailLoading" class="flex items-center justify-center py-10">
          <div class="h-6 w-6 animate-spin rounded-full border-3 border-indigo-500 border-t-transparent"></div>
        </div>

        <!-- Department table -->
        <div v-else-if="activeDetailTab === 'department'" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">部门</th>
                <th class="py-2.5 text-right font-medium">LLM成本</th>
                <th class="py-2.5 text-right font-medium">MCP成本</th>
                <th class="py-2.5 text-right font-medium">总成本</th>
                <th class="py-2.5 text-right font-medium">请求数</th>
                <th class="py-2.5 text-right font-medium">人均成本</th>
                <th class="py-2.5 text-right font-medium">环比</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in deptDetail" :key="row.department" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.department }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.llm_cost) }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.mcp_cost) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.total_cost) }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatNumber(row.requests) }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.per_capita_cost) }}</td>
                <td class="py-3 text-right" :class="row.cost_change !== null && row.cost_change > 0 ? 'text-red-500' : 'text-emerald-600'">
                  {{ formatChange(row.cost_change) }}
                </td>
              </tr>
              <tr v-if="deptDetail.length === 0">
                <td colspan="7" class="py-12 text-center text-sm text-slate-400">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Model table -->
        <div v-else-if="activeDetailTab === 'model'" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">模型</th>
                <th class="py-2.5 text-right font-medium">请求数</th>
                <th class="py-2.5 text-right font-medium">Token数</th>
                <th class="py-2.5 text-right font-medium">成本</th>
                <th class="py-2.5 text-right font-medium">占比</th>
                <th class="py-2.5 text-right font-medium">均次成本</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in modelDetail" :key="row.model" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.model }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatNumber(row.requests) }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatNumber(row.tokens) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.cost) }}</td>
                <td class="py-3 text-right text-slate-700">{{ (row.ratio * 100).toFixed(1) }}%</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.avg_cost) }}</td>
              </tr>
              <tr v-if="modelDetail.length === 0">
                <td colspan="6" class="py-12 text-center text-sm text-slate-400">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Date table -->
        <div v-else-if="activeDetailTab === 'date'" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">日期</th>
                <th class="py-2.5 text-right font-medium">LLM成本</th>
                <th class="py-2.5 text-right font-medium">MCP成本</th>
                <th class="py-2.5 text-right font-medium">总成本</th>
                <th class="py-2.5 text-right font-medium">请求数</th>
                <th class="py-2.5 text-right font-medium">活跃用户</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in dateDetail" :key="row.date" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.date }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.llm_cost) }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.mcp_cost) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.total_cost) }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatNumber(row.requests) }}</td>
                <td class="py-3 text-right text-slate-700">{{ row.active_users }}</td>
              </tr>
              <tr v-if="dateDetail.length === 0">
                <td colspan="6" class="py-12 text-center text-sm text-slate-400">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassCard>
    </template>
  </div>
</template>
