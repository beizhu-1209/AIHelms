<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { AlertTriangle, Download, RefreshCw } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { createExportTask, getEfficiencyOverview, toast } from '@aihelms/shared'
import TooltipIcon from '../../components/TooltipIcon.vue'
import ExportTaskNotice from '../../components/ExportTaskNotice.vue'
import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'
import PresetTabs from './components/PresetTabs.vue'
import { submitEfficiencyRefresh, keepRefreshIndicator } from './utils'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

interface OverviewKpi {
  coverage_rate: number
  coverage_change: number | null
  total_cost: number
  cost_change: number | null
  per_capita_cost: number
  active_per_capita_cost?: number
  per_capita_change: number | null
}

interface TrendData {
  dates: string[]
  active_users: number[]
  cost: number[]
}

interface RankingItem {
  name: string
  coverage_rate: number
  per_capita_cost: number
}

interface DetailRow {
  id: number
  name: string
  path: string
  total_members: number
  active_members: number
  coverage_rate: number
  total_cost: number
  per_capita_cost: number
  active_per_capita_cost: number
  cost_change: number | null
  active_per_capita_change: number | null
  change: number | null
  active_people: string[]
}

interface OverviewData {
  conclusion: string
  warnings: string[]
  dimension: 'department' | 'project'
  dimension_label: string
  kpi: OverviewKpi
  trend: TrendData
  department_ranking: RankingItem[]
  department_table: DetailRow[]
  freshness?: { last_updated_at: string | null; last_updated_label: string; update_status: string }
}

type Granularity = 'day' | 'week' | 'month'
type Dimension = 'department' | 'project'

type SortKey = keyof Pick<
  DetailRow,
  | 'name'
  | 'path'
  | 'total_members'
  | 'active_members'
  | 'coverage_rate'
  | 'total_cost'
  | 'active_per_capita_cost'
  | 'cost_change'
  | 'active_per_capita_change'
>

const TIME_PRESETS = [
  { key: 'month', label: '本月' },
  { key: '7d', label: '近7天' },
  { key: '30d', label: '近30天' },
]

const DIMENSION_OPTIONS: { key: Dimension; label: string }[] = [
  { key: 'department', label: '按部门' },
  { key: 'project', label: '按项目' },
]

const data = ref<OverviewData | null>(null)
const isLoading = ref(true)
const isRefreshing = ref(false)
const exporting = ref(false)
const exportNotice = ref('')
const dimension = ref<Dimension>('department')
const sortKey = ref<SortKey>('coverage_rate')
const sortAsc = ref(false)
const timePreset = ref('month')
const customStart = ref('')
const customEnd = ref('')
const page = ref(1)
const pageSize = 20

const dimensionText = computed(() => (dimension.value === 'project' ? '项目' : '部门'))

function getDateParams(): Record<string, string> {
  if (timePreset.value === 'custom' && customStart.value && customEnd.value) {
    return { start_date: customStart.value, end_date: customEnd.value }
  }
  return { period: timePreset.value }
}

async function loadData() {
  isLoading.value = true
  try {
    data.value = await getEfficiencyOverview<OverviewData>({ ...getDateParams(), dimension: dimension.value })
    page.value = 1
  } finally {
    isLoading.value = false
  }
}

function changePreset(val: string) {
  timePreset.value = val
  loadData()
}

function applyCustomRange() {
  if (customStart.value && customEnd.value) {
    timePreset.value = 'custom'
    loadData()
  }
}

function changeDimension(value: Dimension) {
  dimension.value = value
  loadData()
}

async function refreshData() {
  isRefreshing.value = true
  let queued = false
  try {
    await submitEfficiencyRefresh('overview')
    queued = true
    toast.info('数据更新中，请稍后刷新页面查看', 8000)
  } catch (e) {
    toast.error((e as { message?: string }).message || '刷新失败')
  } finally {
    if (queued) await keepRefreshIndicator()
    isRefreshing.value = false
  }
}

const lastUpdatedLabel = computed(() => data.value?.freshness?.last_updated_label || '--')

function toggleSort(key: SortKey) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    sortAsc.value = false
  }
}

function formatMoney(value: number) {
  return `¥${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

function formatPercent(value: number | null) {
  if (value === null || value === undefined) return '--'
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`
}

function sortIcon(key: SortKey): string {
  if (sortKey.value !== key) return ''
  return sortAsc.value ? ' ↑' : ' ↓'
}

const sortedTable = computed(() => {
  if (!data.value) return []
  const rows = [...data.value.department_table]
  rows.sort((a, b) => {
    const av = a[sortKey.value]
    const bv = b[sortKey.value]
    const left = av === null || av === undefined ? -Infinity : av
    const right = bv === null || bv === undefined ? -Infinity : bv
    const cmp = typeof left === 'number' && typeof right === 'number'
      ? left - right
      : String(left).localeCompare(String(right), 'zh-CN')
    return sortAsc.value ? cmp : -cmp
  })
  return rows
})

const totalPages = computed(() => Math.max(1, Math.ceil(sortedTable.value.length / pageSize)))
const visibleRows = computed(() => sortedTable.value.slice((page.value - 1) * pageSize, page.value * pageSize))

const trendChartOption = computed(() => {
  if (!data.value) return {}
  const { dates, active_users, cost } = data.value.trend
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, data: ['活跃用户', '平台成本'] },
    grid: { top: 24, right: 64, bottom: 48, left: 54 },
    xAxis: { type: 'category', name: '时间', data: dates, axisLabel: { fontSize: 10 } },
    yAxis: [
      { type: 'value', name: '人数', nameTextStyle: { fontSize: 10 }, axisLabel: { fontSize: 10 } },
      { type: 'value', name: '元', nameTextStyle: { fontSize: 10 }, axisLabel: { fontSize: 10 } },
    ],
    series: [
      { name: '活跃用户', type: 'bar', data: active_users, itemStyle: { color: '#818cf8', borderRadius: [3, 3, 0, 0] } },
      { name: '平台成本', type: 'line', yAxisIndex: 1, data: cost, smooth: true, lineStyle: { color: '#f97316' }, itemStyle: { color: '#f97316' } },
    ],
  }
})

const coverageChartOption = computed(() => {
  if (!data.value) return {}
  const ranking = data.value.department_ranking.slice(0, 10)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 8, right: 16, bottom: 24, left: 90 },
    xAxis: { type: 'value', name: '%', max: 100, axisLabel: { fontSize: 10, formatter: '{value}%' } },
    yAxis: { type: 'category', data: ranking.map((d) => d.name), axisLabel: { fontSize: 10 } },
    series: [{ type: 'bar', data: ranking.map((d) => d.coverage_rate), itemStyle: { color: '#6366f1', borderRadius: [0, 3, 3, 0] } }],
  }
})

const perCapitaChartOption = computed(() => {
  if (!data.value) return {}
  const ranking = data.value.department_ranking.slice(0, 10)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 8, right: 16, bottom: 24, left: 90 },
    xAxis: { type: 'value', name: '元', axisLabel: { fontSize: 10 } },
    yAxis: { type: 'category', data: ranking.map((d) => d.name), axisLabel: { fontSize: 10 } },
    series: [{ type: 'bar', data: ranking.map((d) => d.per_capita_cost), itemStyle: { color: '#f59e0b', borderRadius: [0, 3, 3, 0] } }],
  }
})

async function exportRows() {
  exporting.value = true
  try {
    await createExportTask({
      source: 'efficiency',
      export_type: 'overview_scope',
      task_name: `AI效能总览-${dimensionText.value}明细`,
      params: { ...getDateParams(), dimension: dimension.value },
    })
    exportNotice.value = '导出任务已创建，请到资源审计 > 导出任务下载表格'
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建导出任务失败')
  } finally {
    exporting.value = false
  }
}


onMounted(loadData)
</script>

<template>
  <div class="space-y-4">
    <ExportTaskNotice v-if="exportNotice" />
    <div class="rounded-xl border border-slate-200/70 bg-white/80 px-4 py-3 shadow-sm backdrop-blur-xl">
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-xs text-slate-500">时间</span>
        <PresetTabs :model-value="timePreset" :presets="TIME_PRESETS" @update:model-value="changePreset" />
        <div class="flex items-center gap-1.5 text-xs text-slate-500">
          <input v-model="customStart" type="date" class="rounded-md border border-slate-200 bg-white px-2 py-1.5 focus:border-indigo-300 focus:outline-none" />
          <span>至</span>
          <input v-model="customEnd" type="date" class="rounded-md border border-slate-200 bg-white px-2 py-1.5 focus:border-indigo-300 focus:outline-none" />
          <button class="rounded-md border border-slate-200 bg-white px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-50" @click="applyCustomRange">查询</button>
        </div>
        <span class="text-xs text-slate-500">视角</span>
        <div class="inline-flex rounded-lg bg-slate-100/80 p-1">
          <button
            v-for="item in DIMENSION_OPTIONS"
            :key="item.key"
            class="rounded-md px-3 py-1 text-xs transition-colors"
            :class="dimension === item.key ? 'bg-white font-medium text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
            @click="changeDimension(item.key)"
          >
            {{ item.label }}
          </button>
        </div>
        <div class="ml-auto flex items-center gap-2 text-xs text-slate-500">
          <span>最后更新时间：{{ lastUpdatedLabel }}</span>
          <button type="button" class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60" :disabled="isRefreshing" @click.prevent="refreshData">
            <RefreshCw class="h-3.5 w-3.5" :class="isRefreshing ? 'animate-spin' : ''" /> {{ isRefreshing ? '更新中' : '点击更新' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else-if="data">
      <GlassCard v-if="data.warnings.length > 0" padding="p-4">
        <div class="space-y-1.5">
          <div v-for="(warning, index) in data.warnings" :key="index" class="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            <AlertTriangle class="h-3.5 w-3.5 shrink-0 text-amber-500" />
            <span>{{ warning }}</span>
          </div>
        </div>
      </GlassCard>

      <div class="grid grid-cols-3 gap-4">
        <KpiCard
          label="AI 覆盖率"
          :value="`${data.kpi.coverage_rate}%`"
          :change="data.kpi.coverage_change"
          change-kind="up-good"
          tooltip="AI 覆盖率 = 所选时间内至少发生一次 LLM 或 MCP 调用的用户数 ÷ 平台启用用户数。"
        />
        <KpiCard
          label="平台投入"
          :value="formatMoney(data.kpi.total_cost)"
          :change="data.kpi.cost_change"
          change-kind="up-bad"
          tooltip="平台投入 = 所选时间内平台汇总的内部成本合计，只取 AIHelms 平台数据。"
        />
        <KpiCard
          label="活跃人均成本"
          :value="formatMoney(data.kpi.active_per_capita_cost ?? data.kpi.per_capita_cost)"
          :change="data.kpi.per_capita_change"
          change-kind="up-bad"
          tooltip="活跃人均成本 = 平台投入 ÷ 所选时间内活跃用户数。"
        />
      </div>

      <GlassCard title="活跃用户与平台成本趋势" tooltip="X 轴为顶部筛选时间内的统计粒度；左侧 Y 轴为活跃人数，右侧 Y 轴为平台成本，单位为元。">
        <VChart :option="trendChartOption" class="h-64 w-full" autoresize />
      </GlassCard>

      <div class="grid grid-cols-2 gap-4">
        <GlassCard :title="`${dimensionText}覆盖率排行`" tooltip="覆盖率 = 当前部门或项目下，所选时间内有调用的用户数 ÷ 该部门或项目总人数。">
          <VChart :option="coverageChartOption" class="h-56 w-full" autoresize />
        </GlassCard>
        <GlassCard :title="`${dimensionText}活跃人均成本排行`" tooltip="活跃人均成本 = 当前部门或项目的平台成本 ÷ 当前部门或项目的活跃用户数。">
          <VChart :option="perCapitaChartOption" class="h-56 w-full" autoresize />
        </GlassCard>
      </div>

      <GlassCard :title="`${dimensionText}明细`" padding="p-0" tooltip="明细受顶部时间和视角联动；趋势图按所选时间范围自动选择统计粒度。环比均与上一等长周期比较。">
        <template #action>
          <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" :disabled="exporting" @click="exportRows">
            <Download class="h-3.5 w-3.5" /> {{ exporting ? '导出中' : '导出' }}
          </button>
        </template>
        <div v-if="exportNotice" class="mx-5 mt-4 flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <span>{{ exportNotice }}</span>
          <RouterLink to="/export-tasks" class="rounded-md border border-emerald-300 bg-white px-3 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100">去下载</RouterLink>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-[1120px] w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-left text-slate-500">
                <th class="cursor-pointer px-5 py-3 font-medium" @click="toggleSort('name')">{{ dimensionText }}{{ sortIcon('name') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium" @click="toggleSort('path')">层级路径{{ sortIcon('path') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('total_members')">总人数{{ sortIcon('total_members') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('active_members')">活跃人数{{ sortIcon('active_members') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('coverage_rate')">覆盖率{{ sortIcon('coverage_rate') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('total_cost')">总成本{{ sortIcon('total_cost') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('active_per_capita_cost')">活跃人均成本{{ sortIcon('active_per_capita_cost') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('cost_change')">
                  总成本环比
                  <TooltipIcon text="总成本环比 = 当前周期总成本相对上一等长周期总成本的变化。" />
                  {{ sortIcon('cost_change') }}
                </th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('active_per_capita_change')">
                  活跃人均环比
                  <TooltipIcon text="活跃人均环比 = 当前周期活跃人均成本相对上一等长周期活跃人均成本的变化。" />
                  {{ sortIcon('active_per_capita_change') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in visibleRows" :key="row.id" class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
                <td class="px-5 py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="max-w-[16rem] truncate px-3 py-3 text-slate-500" :title="row.path">{{ row.path }}</td>
                <td class="px-3 py-3 text-right text-slate-600">{{ row.total_members }}</td>
                <td class="px-3 py-3 text-right text-slate-600">{{ row.active_members }}</td>
                <td class="px-3 py-3 text-right font-medium text-indigo-600">{{ row.coverage_rate }}%</td>
                <td class="px-3 py-3 text-right text-slate-700">{{ formatMoney(row.total_cost) }}</td>
                <td class="px-3 py-3 text-right text-slate-700">{{ formatMoney(row.active_per_capita_cost) }}</td>
                <td class="px-3 py-3 text-right" :class="row.cost_change && row.cost_change > 0 ? 'text-red-500' : row.cost_change && row.cost_change < 0 ? 'text-emerald-600' : 'text-slate-400'">{{ formatPercent(row.cost_change) }}</td>
                <td class="px-3 py-3 text-right" :class="row.active_per_capita_change && row.active_per_capita_change > 0 ? 'text-red-500' : row.active_per_capita_change && row.active_per_capita_change < 0 ? 'text-emerald-600' : 'text-slate-400'">{{ formatPercent(row.active_per_capita_change) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="sortedTable.length === 0" class="py-10 text-center text-sm text-slate-400">暂无数据</div>
        </div>
        <div v-if="sortedTable.length > pageSize" class="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
          <span>共 {{ sortedTable.length }} 条，每页 {{ pageSize }} 条</span>
          <div class="flex items-center gap-2">
            <button class="rounded border border-slate-200 px-2 py-1 disabled:cursor-not-allowed disabled:opacity-50" :disabled="page <= 1" @click="page -= 1">上一页</button>
            <span>{{ page }} / {{ totalPages }}</span>
            <button class="rounded border border-slate-200 px-2 py-1 disabled:cursor-not-allowed disabled:opacity-50" :disabled="page >= totalPages" @click="page += 1">下一页</button>
          </div>
        </div>
      </GlassCard>
    </template>

    <div v-else class="py-20 text-center text-sm text-slate-400">加载失败，请刷新重试</div>
  </div>
</template>
