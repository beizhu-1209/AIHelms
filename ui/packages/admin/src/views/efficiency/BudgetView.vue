<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { HelpCircle, AlertTriangle } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { request } from '@aihelms/shared/src/api/request'
import GlassCard from './components/GlassCard.vue'
import BudgetProgress from './components/BudgetProgress.vue'
import { formatCost, formatCostShort } from './utils'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

// --- Types ---
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

interface DeptBudgetRow {
  department: string
  monthly_budget: number
  used: number
  execution_rate: number
  predicted_end: number
  risk: 'safe' | 'warning' | 'danger'
  trend: number[]
}

interface ProjectBudgetRow {
  project: string
  monthly_budget: number
  used: number
  execution_rate: number
  predicted_end: number
  risk: 'safe' | 'warning' | 'danger'
}

interface KeyBudgetRow {
  key_name: string
  owner: string
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
  suggestion: string
}

// --- State ---
const DETAIL_TABS = [
  { key: 'department', label: '部门预算' },
  { key: 'project', label: '项目预算' },
  { key: 'key', label: 'Key预算Top10' },
] as const

type DetailTab = (typeof DETAIL_TABS)[number]['key']

const activeDetailTab = ref<DetailTab>('department')
const isLoading = ref(true)

const globalBudget = ref<BudgetGlobal>({
  used: 0, budget: 0, remaining: 0, predicted: 0, risk: 'safe', execution_rate: 0,
})
const trendData = ref<BudgetTrendItem[]>([])
const deptRows = ref<DeptBudgetRow[]>([])
const projectRows = ref<ProjectBudgetRow[]>([])
const keyRows = ref<KeyBudgetRow[]>([])
const alerts = ref<BudgetAlert[]>([])

// --- Data fetching ---
async function loadData() {
  isLoading.value = true
  try {
    const [budgetRes, alertRes] = await Promise.all([
      request<{
        global: BudgetGlobal
        trend: BudgetTrendItem[]
        departments: DeptBudgetRow[]
        projects: ProjectBudgetRow[]
        keys: KeyBudgetRow[]
      }>('/api/v1/efficiency/budget'),
      request<BudgetAlert[]>('/api/v1/efficiency/budget/alerts'),
    ])
    globalBudget.value = budgetRes.global
    trendData.value = budgetRes.trend
    deptRows.value = budgetRes.departments
    projectRows.value = budgetRes.projects
    keyRows.value = budgetRes.keys
    alerts.value = alertRes
  } finally {
    isLoading.value = false
  }
}

// --- Helpers ---
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

// --- Chart option ---
const trendChartOption = computed(() => {
  const dates = trendData.value.map((d) => d.date)
  const actual = trendData.value.map((d) => d.actual_cumulative)
  const predicted = trendData.value.map((d) => d.predicted_cumulative)
  const budgetLine = trendData.value.map((d) => d.budget_limit)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['实际累计', '线性预测', '预算上限'], bottom: 0 },
    grid: { top: 20, right: 20, bottom: 40, left: 60 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatCostShort(v), fontSize: 10 } },
    series: [
      {
        name: '实际累计', type: 'line', data: actual, smooth: false,
        itemStyle: { color: '#6366f1' }, lineStyle: { color: '#6366f1', width: 2 },
        areaStyle: { color: 'rgba(99,102,241,0.08)' },
      },
      {
        name: '线性预测', type: 'line', data: predicted, smooth: false,
        itemStyle: { color: '#94a3b8' },
        lineStyle: { color: '#94a3b8', width: 1.5, type: 'dashed' },
      },
      {
        name: '预算上限', type: 'line', data: budgetLine, smooth: false,
        itemStyle: { color: '#ef4444' },
        lineStyle: { color: '#ef4444', width: 1.5, type: 'dashed' },
        symbol: 'none',
      },
    ],
  }
})

const globalRiskClass = computed(() => {
  if (globalBudget.value.risk === 'danger') return 'border-red-300 bg-red-50/50'
  if (globalBudget.value.risk === 'warning') return 'border-amber-300 bg-amber-50/50'
  return 'border-slate-200/60 bg-white/70'
})

onMounted(loadData)
</script>

<template>
  <div class="space-y-4">
    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else>
      <!-- Global budget execution -->
      <div
        class="rounded-2xl border p-5 shadow-sm backdrop-blur-xl"
        :class="globalRiskClass"
      >
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold text-slate-900">本月预算执行</span>
            <span class="rounded px-2 py-0.5 text-xs" :class="riskBadgeClass(globalBudget.risk)">
              {{ riskLabel(globalBudget.risk) }}
            </span>
          </div>
          <span class="text-xs text-slate-400">当前自然月</span>
        </div>
        <BudgetProgress :value="globalBudget.execution_rate" :show-label="true" height="h-3" class="mb-4" />
        <div class="grid grid-cols-4 gap-4">
          <div>
            <div class="text-xs text-slate-500">已用</div>
            <div class="mt-1 text-xl font-semibold text-indigo-600">{{ formatCost(globalBudget.used) }}</div>
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
            <div class="text-xs text-slate-500">月底预测</div>
            <div class="mt-1 text-xl font-semibold" :class="globalBudget.predicted > globalBudget.budget ? 'text-red-600' : 'text-amber-600'">
              {{ formatCost(globalBudget.predicted) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Budget cumulative trend chart -->
      <GlassCard>
        <div class="mb-2 flex items-center gap-1">
          <span class="text-sm font-semibold text-slate-900">预算累计趋势</span>
          <HelpCircle class="h-3.5 w-3.5 text-slate-400" title="蓝实线=实际累计，灰虚线=线性预测，红虚线=预算上限" />
        </div>
        <VChart :option="trendChartOption" style="height: 280px; width: 100%" autoresize />
      </GlassCard>

      <!-- Budget detail table -->
      <GlassCard>
        <div class="mb-3 flex items-center gap-1">
          <span class="text-sm font-semibold text-slate-900">预算明细</span>
          <HelpCircle class="h-3.5 w-3.5 text-slate-400" title="按维度查看预算执行情况" />
        </div>
        <div class="mb-3 flex gap-1 rounded-lg bg-slate-100/80 p-1">
          <button
            v-for="tab in DETAIL_TABS" :key="tab.key"
            class="rounded-md px-3 py-1.5 text-xs transition-colors"
            :class="activeDetailTab === tab.key ? 'bg-white font-medium text-indigo-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'"
            @click="activeDetailTab = tab.key"
          >{{ tab.label }}</button>
        </div>

        <!-- Department budget table -->
        <div v-if="activeDetailTab === 'department'" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">部门</th>
                <th class="py-2.5 text-right font-medium">月预算</th>
                <th class="py-2.5 text-right font-medium">已用</th>
                <th class="py-2.5 w-36 font-medium">执行率</th>
                <th class="py-2.5 text-right font-medium">预测月底</th>
                <th class="py-2.5 font-medium">风险</th>
                <th class="py-2.5 font-medium">趋势</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in deptRows" :key="row.department" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.department }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.monthly_budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3">
                  <BudgetProgress :value="row.execution_rate" :show-label="true" />
                </td>
                <td class="py-3 text-right" :class="executionColor(row.predicted_end / row.monthly_budget * 100)">
                  {{ formatCost(row.predicted_end) }}
                </td>
                <td class="py-3">
                  <span class="rounded px-2 py-0.5 text-xs" :class="riskBadgeClass(row.risk)">{{ riskLabel(row.risk) }}</span>
                </td>
                <td class="py-3">
                  <svg v-if="row.trend.length >= 2" width="48" height="16" viewBox="0 0 48 16">
                    <polyline
                      :points="row.trend.map((v, i) => `${(i / (row.trend.length - 1)) * 48},${16 - (v / Math.max(...row.trend)) * 16}`).join(' ')"
                      fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linejoin="round"
                    />
                  </svg>
                </td>
              </tr>
              <tr v-if="deptRows.length === 0">
                <td colspan="7" class="py-12 text-center text-sm text-slate-400">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Project budget table -->
        <div v-else-if="activeDetailTab === 'project'" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">项目</th>
                <th class="py-2.5 text-right font-medium">月预算</th>
                <th class="py-2.5 text-right font-medium">已用</th>
                <th class="py-2.5 w-36 font-medium">执行率</th>
                <th class="py-2.5 text-right font-medium">预测月底</th>
                <th class="py-2.5 font-medium">风险</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in projectRows" :key="row.project" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.project }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.monthly_budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3">
                  <BudgetProgress :value="row.execution_rate" :show-label="true" />
                </td>
                <td class="py-3 text-right" :class="executionColor(row.predicted_end / row.monthly_budget * 100)">
                  {{ formatCost(row.predicted_end) }}
                </td>
                <td class="py-3">
                  <span class="rounded px-2 py-0.5 text-xs" :class="riskBadgeClass(row.risk)">{{ riskLabel(row.risk) }}</span>
                </td>
              </tr>
              <tr v-if="projectRows.length === 0">
                <td colspan="6" class="py-12 text-center text-sm text-slate-400">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Key budget Top10 table -->
        <div v-else-if="activeDetailTab === 'key'" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">Key名</th>
                <th class="py-2.5 font-medium">归属</th>
                <th class="py-2.5 font-medium">类型</th>
                <th class="py-2.5 text-right font-medium">预算</th>
                <th class="py-2.5 text-right font-medium">已用</th>
                <th class="py-2.5 w-36 font-medium">执行率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in keyRows" :key="row.key_name" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.key_name }}</td>
                <td class="py-3 text-slate-600">{{ row.owner }}</td>
                <td class="py-3 text-slate-600">{{ row.key_type }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3">
                  <BudgetProgress :value="row.execution_rate" :show-label="true" />
                </td>
              </tr>
              <tr v-if="keyRows.length === 0">
                <td colspan="6" class="py-12 text-center text-sm text-slate-400">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassCard>

      <!-- Overspend alert list -->
      <div v-if="alerts.length > 0" class="space-y-3">
        <div class="flex items-center gap-1">
          <AlertTriangle class="h-4 w-4 text-red-500" />
          <span class="text-sm font-semibold text-slate-900">超支预警</span>
        </div>
        <div
          v-for="(alert, idx) in alerts" :key="idx"
          class="rounded-2xl border-2 border-red-200 bg-red-50/40 p-4 backdrop-blur-xl"
        >
          <div class="flex items-start justify-between">
            <div>
              <div class="text-sm font-medium text-slate-900">{{ alert.target }}</div>
              <div class="mt-0.5 text-xs text-slate-500">{{ alert.type }}</div>
            </div>
            <span class="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">
              执行率 {{ alert.execution_rate.toFixed(0) }}%
            </span>
          </div>
          <div class="mt-2 grid grid-cols-2 gap-4 text-xs">
            <div>
              <span class="text-slate-500">预测超支：</span>
              <span class="font-medium text-red-600">{{ formatCost(alert.predicted_overspend) }}</span>
            </div>
            <div>
              <span class="text-slate-500">建议：</span>
              <span class="text-slate-700">{{ alert.suggestion }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
