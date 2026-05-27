<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { AlertTriangle, Download, HelpCircle } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { request } from '@aihelms/shared/src/api/request'
import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

interface OverviewKpi {
  coverage_rate: number
  coverage_change: number
  total_investment: number
  investment_change: number
  per_capita_cost: number
  per_capita_change: number
}

interface TrendData {
  dates: string[]
  active_users: number[]
  cost: number[]
}

interface DeptRanking {
  name: string
  coverage_rate: number
  per_capita_cost: number
}

interface DepartmentRow {
  name: string
  total_members: number
  active_members: number
  coverage_rate: number
  total_cost: number
  per_capita_cost: number
  change: number
}

interface OverviewData {
  conclusion: string
  warnings: string[]
  kpi: OverviewKpi
  trend: TrendData
  department_ranking: DeptRanking[]
  department_table: DepartmentRow[]
}

const data = ref<OverviewData | null>(null)
const isLoading = ref(true)
const trendTab = ref<'day' | 'week' | 'month'>('day')
const sortKey = ref<keyof DepartmentRow>('coverage_rate')
const sortAsc = ref(false)
const timePreset = ref('month')
const customStart = ref('')
const customEnd = ref('')

function getDateParams(): Record<string, string> {
  if (timePreset.value === 'custom' && customStart.value && customEnd.value) {
    return { start_date: customStart.value, end_date: customEnd.value }
  }
  return { period: timePreset.value }
}

async function loadData() {
  isLoading.value = true
  try {
    data.value = await request<OverviewData>('/api/v1/efficiency/overview', {
      params: { ...getDateParams(), granularity: trendTab.value },
    })
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

function changeTrendTab(tab: 'day' | 'week' | 'month') {
  trendTab.value = tab
  loadData()
}

function toggleSort(key: keyof DepartmentRow) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    sortAsc.value = false
  }
}

const sortedTable = computed(() => {
  if (!data.value) return []
  const rows = [...data.value.department_table]
  rows.sort((a, b) => {
    const av = a[sortKey.value]
    const bv = b[sortKey.value]
    const cmp = typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv))
    return sortAsc.value ? cmp : -cmp
  })
  return rows
})

const trendChartOption = computed(() => {
  if (!data.value) return {}
  const { dates, active_users, cost } = data.value.trend
  return {
    tooltip: { trigger: 'axis' },
    legend: { show: false },
    grid: { top: 20, right: 60, bottom: 28, left: 50 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 } },
    yAxis: [
      { type: 'value', name: '活跃人数', nameTextStyle: { fontSize: 10 }, axisLabel: { fontSize: 10 } },
      { type: 'value', name: '成本(元)', nameTextStyle: { fontSize: 10 }, axisLabel: { fontSize: 10 } },
    ],
    series: [
      { name: '活跃用户', type: 'bar', data: active_users, itemStyle: { color: '#818cf8', borderRadius: [3, 3, 0, 0] } },
      { name: '成本', type: 'line', yAxisIndex: 1, data: cost, smooth: true, lineStyle: { color: '#f97316' }, itemStyle: { color: '#f97316' } },
    ],
  }
})

const coverageChartOption = computed(() => {
  if (!data.value) return {}
  const ranking = data.value.department_ranking.slice(0, 10)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 8, right: 16, bottom: 24, left: 80 },
    xAxis: { type: 'value', max: 100, axisLabel: { fontSize: 10, formatter: '{value}%' } },
    yAxis: { type: 'category', data: ranking.map((d) => d.name), axisLabel: { fontSize: 10 } },
    series: [{ type: 'bar', data: ranking.map((d) => d.coverage_rate), itemStyle: { color: '#6366f1', borderRadius: [0, 3, 3, 0] } }],
  }
})

const perCapitaChartOption = computed(() => {
  if (!data.value) return {}
  const ranking = data.value.department_ranking.slice(0, 10)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 8, right: 16, bottom: 24, left: 80 },
    xAxis: { type: 'value', axisLabel: { fontSize: 10 } },
    yAxis: { type: 'category', data: ranking.map((d) => d.name), axisLabel: { fontSize: 10 } },
    series: [{ type: 'bar', data: ranking.map((d) => d.per_capita_cost), itemStyle: { color: '#f59e0b', borderRadius: [0, 3, 3, 0] } }],
  }
})

function sortIcon(key: keyof DepartmentRow): string {
  if (sortKey.value !== key) return ''
  return sortAsc.value ? ' ↑' : ' ↓'
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-4">
    <!-- Time filter -->
    <div class="flex items-center gap-3">
      <div class="inline-flex rounded-lg bg-slate-100 p-0.5">
        <button
          v-for="p in [{ k: 'month', l: '本月' }, { k: '7d', l: '近7天' }, { k: '30d', l: '近30天' }]"
          :key="p.k"
          class="rounded-md px-3 py-1.5 text-xs font-medium transition"
          :class="timePreset === p.k ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
          @click="changePreset(p.k)"
        >
          {{ p.l }}
        </button>
      </div>
      <div class="flex items-center gap-1.5 text-xs text-slate-500">
        <input v-model="customStart" type="date" class="rounded border border-slate-200 px-2 py-1 text-xs" />
        <span>~</span>
        <input v-model="customEnd" type="date" class="rounded border border-slate-200 px-2 py-1 text-xs" />
        <button
          class="rounded bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-100"
          @click="applyCustomRange"
        >
          查询
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else-if="data">
      <!-- ① Core conclusion banner -->
      <GlassCard padding="p-5">
        <div class="flex items-start gap-3">
          <div class="flex-1">
            <p class="text-sm leading-relaxed text-slate-700">{{ data.conclusion }}</p>
          </div>
        </div>
        <div v-if="data.warnings.length > 0" class="mt-3 space-y-1.5">
          <div
            v-for="(w, i) in data.warnings"
            :key="i"
            class="flex items-center gap-2 rounded-lg bg-amber-50/80 px-3 py-2 text-xs text-amber-800"
          >
            <AlertTriangle class="h-3.5 w-3.5 shrink-0 text-amber-500" />
            <span>{{ w }}</span>
          </div>
        </div>
      </GlassCard>

      <!-- ② KPI cards -->
      <div class="grid grid-cols-3 gap-4">
        <KpiCard
          label="AI 覆盖率"
          :value="`${data.kpi.coverage_rate}%`"
          :change="data.kpi.coverage_change"
          change-kind="up-good"
        />
        <KpiCard
          label="总投入"
          :value="`¥${data.kpi.total_cost.toLocaleString()}`"
          :change="data.kpi.cost_change"
          change-kind="up-bad"
        />
        <KpiCard
          label="人均成本"
          :value="`¥${data.kpi.per_capita_cost.toFixed(1)}`"
          unit="/人"
          :change="data.kpi.per_capita_change"
          change-kind="up-bad"
        />
      </div>

      <!-- ③ Dual-axis trend chart -->
      <GlassCard title="活跃用户与成本趋势" subtitle="柱状=活跃用户数 | 折线=成本(元)" tooltip="蓝色柱=当天有调用的独立用户数；橙色线=当天 LLM+MCP 总成本。支持切换日/周/月粒度。">
        <template #action>
          <div class="inline-flex rounded-md bg-slate-100 p-0.5">
            <button
              v-for="g in [{ k: 'day', l: '日' }, { k: 'week', l: '周' }, { k: 'month', l: '月' }]"
              :key="g.k"
              class="rounded px-2.5 py-0.5 text-xs"
              :class="trendTab === g.k ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'"
              @click="changeTrendTab(g.k as 'day' | 'week' | 'month')"
            >
              {{ g.l }}
            </button>
          </div>
        </template>
        <VChart :option="trendChartOption" class="h-64 w-full" autoresize />
      </GlassCard>

      <!-- ④ Department ranking (left-right split) -->
      <div class="grid grid-cols-2 gap-4">
        <GlassCard title="部门覆盖率排行" subtitle="活跃用户 / 总人数" tooltip="部门覆盖率 = 部门内有调用的用户 ÷ 部门总人数。">
          <VChart :option="coverageChartOption" class="h-56 w-full" autoresize />
        </GlassCard>
        <GlassCard title="部门人均成本排行" subtitle="总成本 / 活跃人数" tooltip="部门人均成本 = 部门总 AI 成本 ÷ 部门活跃用户数。">
          <VChart :option="perCapitaChartOption" class="h-56 w-full" autoresize />
        </GlassCard>
      </div>

      <!-- ⑤ Department detail table -->
      <GlassCard title="部门明细" padding="p-0" tooltip="汇总各部门 AI 使用情况。数据每日凌晨更新。">
        <template #action>
          <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">
            <Download class="h-3.5 w-3.5" /> 导出
          </button>
        </template>
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-left text-slate-500">
                <th class="cursor-pointer px-5 py-3 font-medium" @click="toggleSort('name')">部门{{ sortIcon('name') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('total_members')">总人数{{ sortIcon('total_members') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('active_members')">活跃人数{{ sortIcon('active_members') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('coverage_rate')">覆盖率{{ sortIcon('coverage_rate') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('total_cost')">总成本{{ sortIcon('total_cost') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('per_capita_cost')">人均成本{{ sortIcon('per_capita_cost') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleSort('change')">
                  环比
                  <span :title="'与上一周期相比的变化百分比'"><HelpCircle class="ml-0.5 inline h-3 w-3 text-slate-400" /></span>
                  {{ sortIcon('change') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in sortedTable"
                :key="row.name"
                class="border-b border-slate-50 transition-colors hover:bg-slate-50/50"
              >
                <td class="px-5 py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="px-3 py-3 text-right text-slate-600">{{ row.total_members }}</td>
                <td class="px-3 py-3 text-right text-slate-600">{{ row.active_members }}</td>
                <td class="px-3 py-3 text-right font-medium text-indigo-600">{{ row.coverage_rate }}%</td>
                <td class="px-3 py-3 text-right text-slate-700">¥{{ row.total_cost.toLocaleString() }}</td>
                <td class="px-3 py-3 text-right text-slate-700">¥{{ row.per_capita_cost.toFixed(1) }}</td>
                <td class="px-3 py-3 text-right" :class="row.change > 0 ? 'text-red-500' : row.change < 0 ? 'text-emerald-600' : 'text-slate-400'">
                  {{ row.change > 0 ? '+' : '' }}{{ row.change.toFixed(1) }}%
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="sortedTable.length === 0" class="py-10 text-center text-sm text-slate-400">暂无数据</div>
        </div>
      </GlassCard>
    </template>

    <!-- Error / empty state -->
    <div v-else class="py-20 text-center text-sm text-slate-400">加载失败，请刷新重试</div>
  </div>
</template>
