<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, Download, RefreshCw } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { createExportTask, getEfficiencyBudget, getEfficiencyBudgetAlerts, toast } from '@aihelms/shared'
import TooltipIcon from '../../components/TooltipIcon.vue'
import ExportTaskNotice from '../../components/ExportTaskNotice.vue'
import GlassCard from './components/GlassCard.vue'
import BudgetProgress from './components/BudgetProgress.vue'
import { formatCost, formatCostShort, submitEfficiencyRefresh, keepRefreshIndicator } from './utils'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

interface BudgetGlobal {
  used: number
  budget: number
  remaining: number
  predicted: number
  risk: 'safe' | 'warning' | 'danger'
  execution_rate: number
}

interface BudgetTrendItem {
  date: string
  actual_cumulative: number
  predicted_cumulative: number | null
  budget_limit: number
}

interface ScopeBudgetRow {
  department?: string
  project?: string
  monthly_budget: number
  used: number
  user_key_budget: number
  user_key_used: number
  user_key_count: number
  scope_key_budget: number
  scope_key_used: number
  scope_key_count: number
  execution_rate: number
  predicted_end: number
  risk: 'safe' | 'warning' | 'danger'
  trend?: number[]
}

interface KeyBudgetRow {
  key_name: string
  owner: string
  owner_type: string
  key_type: string
  budget: number
  used: number
  execution_rate: number
}

interface BudgetAlert {
  target: string
  type: string
  execution_rate: number
  predicted_overspend: number
}

type DetailTab = 'department' | 'project' | 'key'

const DETAIL_TABS = [
  { key: 'department' as const, label: '部门预算' },
  { key: 'project' as const, label: '项目预算' },
  { key: 'key' as const, label: 'Key预算' },
]

function getCurrentMonth(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function getLastMonth(): string {
  const d = new Date()
  d.setMonth(d.getMonth() - 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function changeMonth(month: string) {
  selectedMonth.value = month
  loadData()
}

function selectedMonthLabel(): string {
  if (!selectedMonth.value) return '--'
  const [year, month] = selectedMonth.value.split('-')
  return `${year}年${Number(month)}月`
}

const activeDetailTab = ref<DetailTab>('department')
const selectedMonth = ref(getCurrentMonth())
const isLoading = ref(true)
const isRefreshing = ref(false)
const exporting = ref(false)
const exportNotice = ref('')
const lastUpdatedAt = ref<Date | null>(null)
const lastUpdatedLabel = ref('--')
const detailPage = ref(1)
const pageSize = 20

const globalBudget = ref<BudgetGlobal>({ used: 0, budget: 0, remaining: 0, predicted: 0, risk: 'safe', execution_rate: 0 })
const trendData = ref<BudgetTrendItem[]>([])
const deptRows = ref<ScopeBudgetRow[]>([])
const projectRows = ref<ScopeBudgetRow[]>([])
const keyRows = ref<KeyBudgetRow[]>([])
const alerts = ref<BudgetAlert[]>([])

async function refreshData() {
  isRefreshing.value = true
  let queued = false
  try {
    await submitEfficiencyRefresh('budget')
    queued = true
    toast.info('数据更新中，请稍后刷新页面查看', 8000)
  } catch (e) {
    toast.error((e as { message?: string }).message || '刷新失败')
  } finally {
    if (queued) await keepRefreshIndicator()
    isRefreshing.value = false
  }
}

async function loadData() {
  isLoading.value = true
  detailPage.value = 1
  try {
    const [budgetRes, alertRes] = await Promise.all([
      getEfficiencyBudget<{ global: BudgetGlobal; trend: BudgetTrendItem[]; departments: ScopeBudgetRow[]; projects: ScopeBudgetRow[]; keys: KeyBudgetRow[]; freshness?: { last_updated_at: string | null; last_updated_label: string } }>({ month: selectedMonth.value }),
      getEfficiencyBudgetAlerts<BudgetAlert[]>({ month: selectedMonth.value }),
    ])
    globalBudget.value = budgetRes.global
    trendData.value = budgetRes.trend
    deptRows.value = budgetRes.departments
    projectRows.value = budgetRes.projects
    keyRows.value = budgetRes.keys
    alerts.value = alertRes
    lastUpdatedAt.value = budgetRes.freshness?.last_updated_at ? new Date(budgetRes.freshness.last_updated_at) : new Date()
    lastUpdatedLabel.value = budgetRes.freshness?.last_updated_label || formatLastUpdated()
  } finally {
    isLoading.value = false
  }
}

function riskBadgeClass(risk: 'safe' | 'warning' | 'danger'): string {
  if (risk === 'danger') return 'bg-red-100 text-red-700'
  if (risk === 'warning') return 'bg-amber-100 text-amber-700'
  return 'bg-emerald-100 text-emerald-700'
}

function riskLabel(risk: 'safe' | 'warning' | 'danger'): string {
  if (risk === 'danger') return '超支'
  if (risk === 'warning') return '预警'
  return '安全'
}

function executionColor(rate: number): string {
  if (rate > 100) return 'text-red-600'
  if (rate >= 80) return 'text-amber-600'
  return 'text-slate-700'
}

function ownerTypeLabel(type: string): string {
  if (type === 'user') return '用户'
  if (type === 'department') return '部门'
  if (type === 'project') return '项目'
  return type || '--'
}

function formatLastUpdated(): string {
  if (!lastUpdatedAt.value) return '--'
  const diffMinutes = Math.floor((Date.now() - lastUpdatedAt.value.getTime()) / 60000)
  if (diffMinutes < 1) return '刚刚'
  if (diffMinutes < 60) return `${diffMinutes}分钟前`
  const pad = (n: number) => String(n).padStart(2, '0')
  const d = lastUpdatedAt.value
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const activeRows = computed(() => {
  if (activeDetailTab.value === 'project') return projectRows.value
  if (activeDetailTab.value === 'key') return keyRows.value
  return deptRows.value
})
const totalPages = computed(() => Math.max(1, Math.ceil(activeRows.value.length / pageSize)))
const pagedDeptRows = computed(() => deptRows.value.slice((detailPage.value - 1) * pageSize, detailPage.value * pageSize))
const pagedProjectRows = computed(() => projectRows.value.slice((detailPage.value - 1) * pageSize, detailPage.value * pageSize))
const pagedKeyRows = computed(() => keyRows.value.slice((detailPage.value - 1) * pageSize, detailPage.value * pageSize))

function switchTab(tab: DetailTab) {
  activeDetailTab.value = tab
  detailPage.value = 1
}

async function exportDetail() {
  exporting.value = true
  try {
    await createExportTask({
      source: 'efficiency',
      export_type: `budget_${activeDetailTab.value}`,
      task_name: `预算管控-${DETAIL_TABS.find((tab) => tab.key === activeDetailTab.value)?.label || '明细'}`,
      params: { month: selectedMonth.value },
    })
    exportNotice.value = '导出任务已创建，请到资源审计 > 导出任务下载表格'
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建导出任务失败')
  } finally {
    exporting.value = false
  }
}


const trendChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['实际累计', '线性预测', '预算上限'], bottom: 0 },
  grid: { top: 20, right: 20, bottom: 44, left: 64 },
  xAxis: { type: 'category', name: '日期', data: trendData.value.map((d) => d.date), axisLabel: { fontSize: 10 } },
  yAxis: { type: 'value', name: '金额', axisLabel: { formatter: (v: number) => formatCostShort(v), fontSize: 10 } },
  series: [
    { name: '实际累计', type: 'line', data: trendData.value.map((d) => d.actual_cumulative), smooth: false, itemStyle: { color: '#2563eb' }, lineStyle: { color: '#2563eb', width: 2 }, areaStyle: { color: 'rgba(37,99,235,0.08)' } },
    { name: '线性预测', type: 'line', data: trendData.value.map((d) => d.predicted_cumulative), smooth: false, itemStyle: { color: '#94a3b8' }, lineStyle: { color: '#94a3b8', width: 1.5, type: 'dashed' } },
    { name: '预算上限', type: 'line', data: trendData.value.map((d) => d.budget_limit), smooth: false, itemStyle: { color: '#ef4444' }, lineStyle: { color: '#ef4444', width: 1.5, type: 'dashed' }, symbol: 'none' },
  ],
}))

const globalRiskClass = computed(() => {
  if (globalBudget.value.risk === 'danger') return 'border-red-300 bg-red-50/50'
  if (globalBudget.value.risk === 'warning') return 'border-amber-300 bg-amber-50/50'
  return 'border-slate-200 bg-white'
})

onMounted(loadData)
</script>

<template>
  <div class="space-y-4">
    <ExportTaskNotice v-if="exportNotice" />
    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-sm font-semibold text-slate-900">预算</span>
        <div class="flex items-center gap-2 rounded-lg bg-slate-50 px-2 py-1">
          <input
            v-model="selectedMonth"
            type="month"
            class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 focus:border-blue-500 focus:outline-none"
            @change="loadData"
          />
          <button type="button" class="rounded-md px-2 py-1 text-xs text-slate-600 hover:bg-white" @click="changeMonth(getCurrentMonth())">本月</button>
          <button type="button" class="rounded-md px-2 py-1 text-xs text-slate-600 hover:bg-white" @click="changeMonth(getLastMonth())">上月</button>
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
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
    </div>

    <template v-else>
      <div class="rounded-xl border p-5 shadow-sm" :class="globalRiskClass">
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold text-slate-900">{{ selectedMonthLabel() }}预算执行</span>
            <span class="rounded px-2 py-0.5 text-xs" :class="riskBadgeClass(globalBudget.risk)">{{ riskLabel(globalBudget.risk) }}</span>
          </div>
          <TooltipIcon text="预算执行率 = 所选月份已用内部成本 ÷ 所选月份预算总额。已用只取平台成本数据，预算总额来自平台 Key 预算配置。" />
        </div>
        <BudgetProgress :value="globalBudget.execution_rate" :show-label="true" height="h-3" class="mb-4" />
        <div class="grid grid-cols-4 gap-4">
          <div>
            <div class="text-xs text-slate-500">已用</div>
            <div class="mt-1 text-xl font-semibold text-blue-600">{{ formatCost(globalBudget.used) }}</div>
          </div>
          <div>
            <div class="text-xs text-slate-500">预算</div>
            <div class="mt-1 text-xl font-semibold text-slate-900">{{ formatCost(globalBudget.budget) }}</div>
          </div>
          <div>
            <div class="text-xs text-slate-500">剩余</div>
            <div class="mt-1 text-xl font-semibold text-slate-900">{{ formatCost(globalBudget.remaining) }}</div>
          </div>
          <div>
            <div class="text-xs text-slate-500">月末预测</div>
            <div class="mt-1 text-xl font-semibold" :class="globalBudget.predicted > globalBudget.budget ? 'text-red-600' : 'text-amber-600'">{{ formatCost(globalBudget.predicted) }}</div>
          </div>
        </div>
      </div>

      <GlassCard>
        <div class="mb-2 flex items-center gap-1">
          <span class="text-sm font-semibold text-slate-900">预算累计趋势</span>
          <TooltipIcon text="实际累计为所选月份内部成本累计；预算上限为总预算按自然日均摊后的累计线。" />
        </div>
        <VChart :option="trendChartOption" style="height: 280px; width: 100%" autoresize />
      </GlassCard>

      <GlassCard>
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-1">
            <span class="text-sm font-semibold text-slate-900">预算明细</span>
            <TooltipIcon text="部门/项目明细同时展示人员归属 Key 和部门/项目直接归属 Key。" />
          </div>
          <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" :disabled="exporting" @click="exportDetail">
            <Download class="h-3.5 w-3.5" /> {{ exporting ? '导出中' : '导出' }}
          </button>
        </div>
        <div class="mb-3 flex gap-1 rounded-lg bg-slate-100 p-1">
          <button v-for="tab in DETAIL_TABS" :key="tab.key" class="rounded-md px-3 py-1.5 text-xs transition-colors" :class="activeDetailTab === tab.key ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'" @click="switchTab(tab.key)">{{ tab.label }}</button>
        </div>

        <div class="max-h-[520px] overflow-auto">
          <table v-if="activeDetailTab === 'department'" class="min-w-[1180px] w-full text-sm">
            <thead class="sticky top-0 z-10 bg-white">
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">部门</th>
                <th class="py-2.5 text-right font-medium">总预算</th>
                <th class="py-2.5 text-right font-medium">总已用</th>
                <th class="py-2.5 w-36 font-medium">执行率</th>
                <th class="py-2.5 text-right font-medium">人员Key数</th>
                <th class="py-2.5 text-right font-medium">人员Key已用</th>
                <th class="py-2.5 text-right font-medium">部门Key数</th>
                <th class="py-2.5 text-right font-medium">部门Key已用</th>
                <th class="py-2.5 text-right font-medium">月末预测</th>
                <th class="py-2.5 font-medium">风险</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in pagedDeptRows" :key="row.department" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.department }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.monthly_budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3"><BudgetProgress :value="row.execution_rate" :show-label="true" /></td>
                <td class="py-3 text-right text-slate-700">{{ row.user_key_count }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.user_key_used) }}</td>
                <td class="py-3 text-right text-slate-700">{{ row.scope_key_count }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.scope_key_used) }}</td>
                <td class="py-3 text-right" :class="executionColor(row.monthly_budget > 0 ? row.predicted_end / row.monthly_budget * 100 : 0)">{{ formatCost(row.predicted_end) }}</td>
                <td class="py-3"><span class="rounded px-2 py-0.5 text-xs" :class="riskBadgeClass(row.risk)">{{ riskLabel(row.risk) }}</span></td>
              </tr>
              <tr v-if="deptRows.length === 0"><td colspan="10" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
            </tbody>
          </table>

          <table v-else-if="activeDetailTab === 'project'" class="min-w-[1180px] w-full text-sm">
            <thead class="sticky top-0 z-10 bg-white">
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">项目</th>
                <th class="py-2.5 text-right font-medium">总预算</th>
                <th class="py-2.5 text-right font-medium">总已用</th>
                <th class="py-2.5 w-36 font-medium">执行率</th>
                <th class="py-2.5 text-right font-medium">人员Key数</th>
                <th class="py-2.5 text-right font-medium">人员Key已用</th>
                <th class="py-2.5 text-right font-medium">项目Key数</th>
                <th class="py-2.5 text-right font-medium">项目Key已用</th>
                <th class="py-2.5 text-right font-medium">月末预测</th>
                <th class="py-2.5 font-medium">风险</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in pagedProjectRows" :key="row.project" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.project }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.monthly_budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3"><BudgetProgress :value="row.execution_rate" :show-label="true" /></td>
                <td class="py-3 text-right text-slate-700">{{ row.user_key_count }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.user_key_used) }}</td>
                <td class="py-3 text-right text-slate-700">{{ row.scope_key_count }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.scope_key_used) }}</td>
                <td class="py-3 text-right" :class="executionColor(row.monthly_budget > 0 ? row.predicted_end / row.monthly_budget * 100 : 0)">{{ formatCost(row.predicted_end) }}</td>
                <td class="py-3"><span class="rounded px-2 py-0.5 text-xs" :class="riskBadgeClass(row.risk)">{{ riskLabel(row.risk) }}</span></td>
              </tr>
              <tr v-if="projectRows.length === 0"><td colspan="10" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
            </tbody>
          </table>

          <table v-else class="min-w-[900px] w-full text-sm">
            <thead class="sticky top-0 z-10 bg-white">
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">Key名</th>
                <th class="py-2.5 font-medium">归属对象</th>
                <th class="py-2.5 font-medium">归属类型</th>
                <th class="py-2.5 font-medium">Key类型</th>
                <th class="py-2.5 text-right font-medium">预算</th>
                <th class="py-2.5 text-right font-medium">已用</th>
                <th class="py-2.5 w-36 font-medium">执行率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in pagedKeyRows" :key="row.key_name" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.key_name }}</td>
                <td class="py-3 text-slate-600">{{ row.owner }}</td>
                <td class="py-3 text-slate-600">{{ ownerTypeLabel(row.owner_type) }}</td>
                <td class="py-3 text-slate-600">{{ row.key_type }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3"><BudgetProgress :value="row.execution_rate" :show-label="true" /></td>
              </tr>
              <tr v-if="keyRows.length === 0"><td colspan="7" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
            </tbody>
          </table>
        </div>

        <div v-if="activeRows.length > pageSize" class="mt-3 flex items-center justify-between text-xs text-slate-500">
          <span>共 {{ activeRows.length }} 条，每页 {{ pageSize }} 条</span>
          <div class="flex items-center gap-2">
            <button class="rounded border border-slate-200 px-2 py-1 disabled:cursor-not-allowed disabled:opacity-50" :disabled="detailPage <= 1" @click="detailPage--">上一页</button>
            <span>{{ detailPage }} / {{ totalPages }}</span>
            <button class="rounded border border-slate-200 px-2 py-1 disabled:cursor-not-allowed disabled:opacity-50" :disabled="detailPage >= totalPages" @click="detailPage++">下一页</button>
          </div>
        </div>
      </GlassCard>

      <div v-if="alerts.length > 0" class="space-y-3">
        <div class="flex items-center gap-1">
          <AlertTriangle class="h-4 w-4 text-red-500" />
          <span class="text-sm font-semibold text-slate-900">预算预警</span>
        </div>
        <div v-for="(alert, idx) in alerts" :key="idx" class="rounded-xl border border-red-200 bg-red-50/40 p-4">
          <div class="flex items-start justify-between">
            <div>
              <div class="text-sm font-medium text-slate-900">{{ alert.target }}</div>
              <div class="mt-0.5 text-xs text-slate-500">{{ alert.type }}</div>
            </div>
            <span class="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">执行率 {{ alert.execution_rate.toFixed(0) }}%</span>
          </div>
          <div class="mt-2 text-xs">
            <span class="text-slate-500">预测超支：</span>
            <span class="font-medium text-red-600">{{ formatCost(alert.predicted_overspend) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
