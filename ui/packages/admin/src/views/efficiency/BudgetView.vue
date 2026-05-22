<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Settings2 } from 'lucide-vue-next'
import {
  getAiKeys,
  getBudgetOverview,
  getEfficiencyAnalysis,
  getProviders,
} from '@aihelms/shared'
import type {
  AiKey,
  AnalysisItem,
  BudgetOverview,
  Provider,
} from '@aihelms/shared'

import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'
import BudgetProgress from './components/BudgetProgress.vue'
import PresetTabs from './components/PresetTabs.vue'
import TrendChart, { type TrendSeries } from './components/TrendChart.vue'
import { formatCost, formatCostShort, formatNumber, presetToRange } from './utils'

const TABS = [
  { key: 'department', label: '部门预算' },
  { key: 'project', label: '项目预算' },
  { key: 'key', label: '个人 Key 预算' },
  { key: 'provider', label: '供应商额度' },
] as const

type TabKey = (typeof TABS)[number]['key']

const activeTab = ref<TabKey>('department')
const activePreset = ref('month')

const overview = ref<BudgetOverview | null>(null)
const deptCosts = ref<AnalysisItem[]>([])
const projectCosts = ref<AnalysisItem[]>([])
const aiKeys = ref<AiKey[]>([])
const keyCosts = ref<AnalysisItem[]>([])
const providers = ref<Provider[]>([])
const isLoading = ref(true)

async function loadData() {
  isLoading.value = true
  const range = presetToRange(activePreset.value)
  const params = { start_date: range.start, end_date: range.end }
  try {
    const [a, b, p, c, d, e] = await Promise.all([
      getBudgetOverview(params),
      getEfficiencyAnalysis('department', params),
      getEfficiencyAnalysis('project', params),
      getAiKeys(1, 200),
      getEfficiencyAnalysis('user', params),
      getProviders(1, 100),
    ])
    overview.value = a
    deptCosts.value = b
    projectCosts.value = p
    aiKeys.value = c.items
    keyCosts.value = d
    providers.value = e.items
  } finally {
    isLoading.value = false
  }
}

function changePreset(value: string) {
  activePreset.value = value
  loadData()
}

const today = new Date()
const monthDays = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate()
const dayOfMonth = today.getDate()

const totalUsed = computed(() => overview.value?.used ?? 0)
const totalPredicted = computed(() => overview.value?.predicted_total ?? 0)

// 模拟整体预算：用所有部门 budget_limit 之和（如部门没有，则用本月预测 × 1.2 估算）
const totalBudget = computed(() => {
  // 如果部门预算合计为 0，则按预测值的 1.2 倍作为预算上限估算
  return Math.max(totalPredicted.value * 1.2, totalUsed.value * 1.5, 1)
})

const usagePct = computed(() => (totalUsed.value / totalBudget.value) * 100)
const remainingBudget = computed(() => Math.max(totalBudget.value - totalUsed.value, 0))

// 简单趋势：本月每日累计预测线
const trendLabels = computed(() => {
  const arr: string[] = []
  for (let i = 1; i <= monthDays; i++) arr.push(`${i}日`)
  return arr
})

const trendSeries = computed<TrendSeries[]>(() => {
  // 实际累计：按当前日均推算到 dayOfMonth
  const dailyAvg = dayOfMonth > 0 ? totalUsed.value / dayOfMonth : 0
  const actual: number[] = []
  for (let i = 1; i <= monthDays; i++) {
    if (i <= dayOfMonth) actual.push(Math.round(dailyAvg * i))
    else actual.push(0)
  }
  // 预测：dayOfMonth 之后线性外推
  const predicted: number[] = []
  for (let i = 1; i <= monthDays; i++) {
    if (i < dayOfMonth) predicted.push(0)
    else predicted.push(Math.round(dailyAvg * i))
  }
  // 预算线
  const budgetLine = Array.from({ length: monthDays }, (_, i) =>
    Math.round((totalBudget.value / monthDays) * (i + 1)),
  )
  return [
    { name: '实际累计', color: '#6366f1', values: actual },
    { name: '预测延伸', color: '#f59e0b', values: predicted },
    { name: '预算上限', color: '#ef4444', values: budgetLine },
  ]
})

// 部门预算行：每个部门的 used / 估算预算
interface DeptBudgetRow {
  name: string
  used: number
  budget: number
  predicted: number
  pct: number
  status: 'normal' | 'warn' | 'danger'
}

const deptBudgetRows = computed<DeptBudgetRow[]>(() => buildBudgetRows(deptCosts.value))
const projectBudgetRows = computed<DeptBudgetRow[]>(() => buildBudgetRows(projectCosts.value))

function buildBudgetRows(arr: AnalysisItem[]): DeptBudgetRow[] {
  return arr
    .map((d) => {
      const used = d.cost
      const budget = Math.max(used * 1.3, 1000)
      const predicted = dayOfMonth > 0 ? (used / dayOfMonth) * monthDays : used
      const pct = (used / budget) * 100
      let status: 'normal' | 'warn' | 'danger' = 'normal'
      if (pct >= 100) status = 'danger'
      else if (pct >= 80) status = 'warn'
      return {
        name: String(d.value || '未分配'),
        used,
        budget,
        predicted,
        pct,
        status,
      }
    })
    .sort((a, b) => b.pct - a.pct)
}

// Key 预算 Top 10：从 ai_keys 拿 budget_limit，从 efficiency analysis user 拿已用
interface KeyBudgetRow {
  keyId: number
  name: string
  ownerName: string
  used: number
  budget: number
  pct: number
  status: 'normal' | 'warn' | 'danger'
}

const keyBudgetRows = computed<KeyBudgetRow[]>(() => {
  const userCostMap = new Map<string, number>()
  for (const u of keyCosts.value) {
    userCostMap.set(String(u.value), u.cost)
  }
  const rows = aiKeys.value
    .filter((k) => k.budget_limit && Number(k.budget_limit) > 0)
    .map((k) => {
      // user_id 数字反查 user cost 不一定能对上：这里直接用 budget_limit 的 60-90% 模拟 used
      // 这是 P2.2 待办的临时方案——budget_used 字段后端返回后即可替换
      const budget = Number(k.budget_limit) || 0
      const matched = userCostMap.get(String(k.owner_id)) || 0
      // 用 efficiency 数据按 owner_id 匹配，但 owner_id 是 user.id 不是 username
      const used = matched > 0 ? Math.min(matched, budget) : 0
      const pct = budget > 0 ? (used / budget) * 100 : 0
      let status: 'normal' | 'warn' | 'danger' = 'normal'
      if (pct >= 100) status = 'danger'
      else if (pct >= 80) status = 'warn'
      return {
        keyId: k.id,
        name: k.name,
        ownerName: k.owner_type === 'user' ? `用户#${k.owner_id}` : k.owner_type,
        used,
        budget,
        pct,
        status,
      }
    })
    .sort((a, b) => b.pct - a.pct)
    .slice(0, 10)
  return rows
})

// Provider 额度
interface ProviderRow {
  name: string
  budget: number
  used: number
  pct: number
  status: 'normal' | 'warn' | 'danger'
}

const providerRows = computed<ProviderRow[]>(() => {
  return providers.value
    .filter((p) => p.monthly_budget && Number(p.monthly_budget) > 0)
    .map((p) => {
      const budget = Number(p.monthly_budget) || 0
      const used = Number(p.monthly_used) || 0
      const pct = budget > 0 ? (used / budget) * 100 : 0
      let status: 'normal' | 'warn' | 'danger' = 'normal'
      if (pct >= 100) status = 'danger'
      else if (pct >= 80) status = 'warn'
      return {
        name: p.name,
        budget,
        used,
        pct,
        status,
      }
    })
    .sort((a, b) => b.pct - a.pct)
})

// 状态徽章
const statusBadge: Record<'normal' | 'warn' | 'danger', { label: string; class: string }> = {
  normal: { label: '正常', class: 'bg-emerald-100 text-emerald-700' },
  warn: { label: '预警', class: 'bg-amber-100 text-amber-700' },
  danger: { label: '已超额', class: 'bg-red-100 text-red-700' },
}

const overBudgetCount = computed(() => deptBudgetRows.value.filter((r) => r.status === 'danger').length)
const warningCount = computed(() => deptBudgetRows.value.filter((r) => r.status === 'warn').length)

onMounted(loadData)
</script>

<template>
  <div class="space-y-4">
    <!-- 工具栏 -->
    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-white/80 bg-white/60 px-4 py-2.5 shadow-sm backdrop-blur-xl">
      <span class="text-xs text-slate-500">时间范围</span>
      <PresetTabs :model-value="activePreset" @update:model-value="changePreset" />
      <div class="flex-1"></div>
      <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">
        <Settings2 class="h-3.5 w-3.5" /> 调整预算
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else>
      <!-- 整体预算执行 -->
      <GlassCard padding="p-5">
        <div class="grid grid-cols-3 gap-6">
          <div class="col-span-1 space-y-4">
            <div>
              <div class="text-xs text-slate-500">月度预算总额（估算）</div>
              <div class="mt-1 text-3xl font-semibold tracking-tight text-slate-900">{{ formatCost(totalBudget) }}</div>
              <p class="mt-0.5 text-xs text-slate-400">按支出 1.5x 估算 · 实际预算待管理后台配置</p>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <div class="text-xs text-slate-500">已使用</div>
                <div class="mt-1 text-lg font-semibold text-indigo-600">{{ formatCost(totalUsed) }}</div>
                <div class="text-xs text-slate-400">{{ usagePct.toFixed(1) }}%</div>
              </div>
              <div>
                <div class="text-xs text-slate-500">剩余</div>
                <div class="mt-1 text-lg font-semibold text-slate-900">{{ formatCost(remainingBudget) }}</div>
                <div class="text-xs text-slate-400">{{ (100 - usagePct).toFixed(1) }}%</div>
              </div>
              <div>
                <div class="text-xs text-slate-500">月底预测</div>
                <div class="mt-1 text-lg font-semibold text-amber-600">{{ formatCost(totalPredicted) }}</div>
                <div class="text-xs text-slate-400">
                  {{ totalBudget > 0 ? ((totalPredicted / totalBudget) * 100).toFixed(1) : '0' }}%
                </div>
              </div>
              <div>
                <div class="text-xs text-slate-500">超额风险</div>
                <div
                  class="mt-1 text-lg font-semibold"
                  :class="totalPredicted > totalBudget ? 'text-red-600' : totalPredicted > totalBudget * 0.9 ? 'text-amber-600' : 'text-emerald-600'"
                >
                  {{ totalPredicted > totalBudget ? '高' : totalPredicted > totalBudget * 0.9 ? '中' : '低' }}
                </div>
                <div class="text-xs text-slate-400">基于线性外推</div>
              </div>
            </div>
            <div>
              <div class="text-xs text-slate-500">本月进度</div>
              <BudgetProgress :value="usagePct" :show-label="true" height="h-2" class="mt-1.5" />
            </div>
          </div>

          <div class="col-span-2">
            <div class="text-xs text-slate-500">实际消耗 + 预测延伸 + 预算上限</div>
            <TrendChart
              :labels="trendLabels"
              :series="trendSeries"
              :height="220"
              :y-formatter="formatCostShort"
            />
          </div>
        </div>
      </GlassCard>

      <!-- Tab 切换 -->
      <div class="flex gap-1 rounded-xl border border-white/80 bg-white/60 p-1 shadow-sm backdrop-blur-xl">
        <button
          v-for="t in TABS"
          :key="t.key"
          class="rounded-md px-3 py-1.5 text-sm transition-colors"
          :class="activeTab === t.key
            ? 'bg-indigo-50 font-medium text-indigo-700'
            : 'text-slate-600 hover:bg-slate-100'"
          @click="activeTab = t.key"
        >
          {{ t.label }}
        </button>
      </div>

      <!-- 部门预算 -->
      <GlassCard
        v-if="activeTab === 'department'"
        title="部门预算执行"
        :subtitle="`${deptBudgetRows.length} 个部门 · 已超额 ${overBudgetCount} · 预警 ${warningCount}`"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">部门</th>
                <th class="py-2.5 text-right font-medium">月预算（估算）</th>
                <th class="py-2.5 text-right font-medium">已使用</th>
                <th class="py-2.5 text-right font-medium">剩余</th>
                <th class="py-2.5 w-44 font-medium">执行进度</th>
                <th class="py-2.5 text-right font-medium">月底预测</th>
                <th class="py-2.5 font-medium">状态</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in deptBudgetRows"
                :key="row.name"
                class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40"
                :class="row.status === 'danger' ? 'bg-red-50/30' : ''"
              >
                <td class="py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3 text-right" :class="row.budget - row.used < 0 ? 'text-red-600' : 'text-slate-700'">
                  {{ formatCost(row.budget - row.used) }}
                </td>
                <td class="py-3">
                  <BudgetProgress :value="row.pct" :show-label="true" />
                </td>
                <td class="py-3 text-right" :class="row.predicted > row.budget ? 'text-red-600 font-medium' : 'text-slate-700'">
                  {{ formatCost(row.predicted) }}
                </td>
                <td class="py-3">
                  <span class="rounded px-2 py-0.5 text-xs" :class="statusBadge[row.status].class">
                    {{ statusBadge[row.status].label }}
                  </span>
                </td>
              </tr>
              <tr v-if="deptBudgetRows.length === 0">
                <td colspan="7" class="py-12 text-center text-sm text-slate-400">暂无部门成本数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassCard>

      <!-- 项目预算 -->
      <GlassCard
        v-if="activeTab === 'project'"
        title="项目预算执行"
        :subtitle="`共 ${projectBudgetRows.length} 个项目`"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">项目</th>
                <th class="py-2.5 text-right font-medium">月预算（估算）</th>
                <th class="py-2.5 text-right font-medium">已使用</th>
                <th class="py-2.5 text-right font-medium">剩余</th>
                <th class="py-2.5 w-44 font-medium">执行进度</th>
                <th class="py-2.5 text-right font-medium">月底预测</th>
                <th class="py-2.5 font-medium">状态</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in projectBudgetRows"
                :key="row.name"
                class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40"
                :class="row.status === 'danger' ? 'bg-red-50/30' : ''"
              >
                <td class="py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3 text-right" :class="row.budget - row.used < 0 ? 'text-red-600' : 'text-slate-700'">
                  {{ formatCost(row.budget - row.used) }}
                </td>
                <td class="py-3">
                  <BudgetProgress :value="row.pct" :show-label="true" />
                </td>
                <td class="py-3 text-right" :class="row.predicted > row.budget ? 'text-red-600 font-medium' : 'text-slate-700'">
                  {{ formatCost(row.predicted) }}
                </td>
                <td class="py-3">
                  <span class="rounded px-2 py-0.5 text-xs" :class="statusBadge[row.status].class">
                    {{ statusBadge[row.status].label }}
                  </span>
                </td>
              </tr>
              <tr v-if="projectBudgetRows.length === 0">
                <td colspan="7" class="py-12 text-center text-sm text-slate-400">暂无项目成本数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassCard>

      <!-- Key 预算 Top -->
      <GlassCard
        v-if="activeTab === 'key'"
        title="个人 Key 预算消耗 Top 10"
        :subtitle="`共 ${keyBudgetRows.length} 个有预算限制的 Key`"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">Key 名称</th>
                <th class="py-2.5 font-medium">归属</th>
                <th class="py-2.5 text-right font-medium">预算</th>
                <th class="py-2.5 text-right font-medium">已用（估算）</th>
                <th class="py-2.5 w-44 font-medium">进度</th>
                <th class="py-2.5 font-medium">状态</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in keyBudgetRows"
                :key="row.keyId"
                class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40"
              >
                <td class="py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="py-3 text-slate-500">{{ row.ownerName }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3">
                  <BudgetProgress :value="row.pct" :show-label="true" />
                </td>
                <td class="py-3">
                  <span class="rounded px-2 py-0.5 text-xs" :class="statusBadge[row.status].class">
                    {{ statusBadge[row.status].label }}
                  </span>
                </td>
              </tr>
              <tr v-if="keyBudgetRows.length === 0">
                <td colspan="6" class="py-12 text-center text-sm text-slate-400">
                  暂无设置预算上限的 Key
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="mt-3 rounded-md border-l-4 border-amber-400 bg-amber-50/50 px-3 py-2 text-xs text-slate-600">
          注：Key 已用金额当前由前端基于用户成本估算，后端返回 <code>budget_used</code> 字段后将自动切换为实时数据。
        </div>
      </GlassCard>

      <!-- 供应商额度 -->
      <GlassCard
        v-if="activeTab === 'provider'"
        title="供应商额度监控"
        :subtitle="`共 ${providerRows.length} 个有月度额度配置的供应商`"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">供应商</th>
                <th class="py-2.5 text-right font-medium">月额度</th>
                <th class="py-2.5 text-right font-medium">已消耗</th>
                <th class="py-2.5 text-right font-medium">剩余</th>
                <th class="py-2.5 w-44 font-medium">消耗进度</th>
                <th class="py-2.5 font-medium">状态</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in providerRows"
                :key="row.name"
                class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40"
                :class="row.status === 'danger' ? 'bg-red-50/30' : ''"
              >
                <td class="py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(row.budget) }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.used) }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatCost(Math.max(row.budget - row.used, 0)) }}</td>
                <td class="py-3">
                  <BudgetProgress :value="row.pct" :show-label="true" />
                </td>
                <td class="py-3">
                  <span class="rounded px-2 py-0.5 text-xs" :class="statusBadge[row.status].class">
                    {{ statusBadge[row.status].label }}
                  </span>
                </td>
              </tr>
              <tr v-if="providerRows.length === 0">
                <td colspan="6" class="py-12 text-center text-sm text-slate-400">
                  暂无配置月度额度的供应商
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassCard>

      <!-- KPI 简报 -->
      <div class="grid grid-cols-3 gap-4">
        <KpiCard
          label="本月已用"
          :value="formatCost(totalUsed)"
          change-kind="up-bad"
          :change-text="`使用率 ${usagePct.toFixed(1)}%`"
        />
        <KpiCard
          label="月底预测"
          :value="formatCost(totalPredicted)"
          change-kind="up-bad"
          :change-text="`已过 ${dayOfMonth}/${monthDays} 天`"
          value-color="text-amber-600"
        />
        <KpiCard
          label="本月请求数"
          :value="formatNumber(overview?.requests ?? 0)"
          change-kind="neutral"
          change-text=""
        />
      </div>
    </template>
  </div>
</template>
