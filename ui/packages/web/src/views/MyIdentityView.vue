<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuth, getMyKeys, type ActiveModel } from '@aihelms/shared'
import { request } from '@aihelms/shared/src/api/request'
import type { AiKey } from '@aihelms/shared/src/types/ai-key'
import type { EfficiencyKpi, TrendItem } from '@aihelms/shared/src/types/efficiency'
import type { ResourceApplication } from '@aihelms/shared/src/types/resource-application'
import type { McpServer } from '@aihelms/shared/src/types/mcp'
import type { Skill } from '@aihelms/shared/src/types/skill'
import { Copy, Check, Cpu, Server, Sparkles, Clock, CheckCircle2, XCircle, Eye, EyeOff } from 'lucide-vue-next'
import ProviderIcon from '../components/ProviderIcon.vue'

import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const { currentUser } = useAuth()
const { t } = useI18n()
const mainKey = ref<AiKey | null>(null)
const kpi = ref<EfficiencyKpi | null>(null)
const trend = ref<TrendItem[]>([])
const applications = ref<ResourceApplication[]>([])
const mcpNames = ref<Record<number, string>>({})
const skillNames = ref<Record<number, string>>({})
const modelIconUrls = ref<Record<string, string>>({})
const isLoading = ref(true)
const copied = ref(false)
const showFullKey = ref(false)
const endpointUrl = ref('')

const maskedKey = computed(() => {
  const val = mainKey.value?.key_value || mainKey.value?.litellm_key_id
  if (!val) return 'sk-xxxxxxxxxxxx'
  return val.slice(0, 7) + '****' + val.slice(-4)
})

const fullKey = computed(() => mainKey.value?.key_value || mainKey.value?.litellm_key_id || '')

const displayKey = computed(() => showFullKey.value ? fullKey.value : maskedKey.value)

const budgetDisplay = computed(() => {
  if (!mainKey.value) return t('identity.budget.unlimited')
  const scope = mainKey.value.budget_scope
  if (scope === 'unified') {
    return mainKey.value.budget_limit ? `¥${mainKey.value.budget_limit}` : t('identity.budget.unlimited')
  }
  if (scope === 'per_type') {
    const parts: string[] = []
    if (mainKey.value.budget_models_total) parts.push(t('identity.budget.models', { amount: mainKey.value.budget_models_total }))
    if (mainKey.value.budget_mcps_total) parts.push(t('identity.budget.mcps', { amount: mainKey.value.budget_mcps_total }))
    return parts.length ? parts.join(' / ') : t('identity.budget.unlimited')
  }
  if (scope === 'per_resource') return t('identity.budget.perResource')
  return t('identity.budget.unlimited')
})

const totalBudget = computed(() => {
  if (!mainKey.value) return null
  const scope = mainKey.value.budget_scope
  if (scope === 'unified' && mainKey.value.budget_limit) return Number(mainKey.value.budget_limit)
  if (scope === 'per_type') {
    const m = Number(mainKey.value.budget_models_total) || 0
    const c = Number(mainKey.value.budget_mcps_total) || 0
    return m + c > 0 ? m + c : null
  }
  return null
})

function formatBigToken(n: number): string {
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return String(n)
}

const dailyAvgCost = computed(() => {
  const cost = kpi.value?.total_cost ?? 0
  const day = new Date().getDate()
  return day > 0 ? cost / day : 0
})

const budgetUsedPercent = computed(() => {
  const budget = totalBudget.value
  if (!budget) return null
  const spent = kpi.value?.total_cost ?? 0
  return Math.min((spent / budget) * 100, 100)
})

const chartMode = ref<'cost' | 'token'>('cost')

const TOKEN_SERIES = [
  { key: 'input_tokens', labelKey: 'identity.overview.tokenInput', color: '#8b5cf6' },
  { key: 'output_tokens', labelKey: 'identity.overview.tokenOutput', color: '#0ea5e9' },
  { key: 'cache_read_tokens', labelKey: 'identity.overview.tokenCacheRead', color: '#10b981' },
  { key: 'cache_creation_tokens', labelKey: 'identity.overview.tokenCacheCreation', color: '#f59e0b' },
] as const

const tokenBreakdown = computed(() =>
  TOKEN_SERIES.map(s => ({
    labelKey: s.labelKey,
    color: s.color,
    value: kpi.value?.[s.key] ?? 0,
  })),
)

const chartOption = computed(() => {
  const periods = trend.value.map(t => t.period)
  const baseAxis = {
    xAxis: {
      type: 'category',
      data: periods,
      axisLabel: { fontSize: 10, color: '#94a3b8' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
    },
    splitLine: { lineStyle: { color: '#f1f5f9' } },
  }

  if (chartMode.value === 'token') {
    return {
      tooltip: { trigger: 'axis' },
      legend: {
        top: 0,
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { fontSize: 10, color: '#94a3b8' },
        data: TOKEN_SERIES.map(s => t(s.labelKey)),
      },
      grid: { top: 34, right: 20, bottom: 30, left: 50 },
      xAxis: baseAxis.xAxis,
      yAxis: {
        type: 'value',
        axisLabel: { fontSize: 10, color: '#94a3b8', formatter: (v: number) => formatBigToken(v) },
        splitLine: baseAxis.splitLine,
      },
      series: TOKEN_SERIES.map(s => ({
        name: t(s.labelKey),
        type: 'line',
        data: trend.value.map(item => item[s.key] ?? 0),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: s.color, width: 2 },
        itemStyle: { color: s.color },
      })),
    }
  }

  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 20, right: 20, bottom: 30, left: 50 },
    xAxis: baseAxis.xAxis,
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 10, color: '#94a3b8', formatter: (v: number) => `¥${v}` },
      splitLine: baseAxis.splitLine,
    },
    series: [{
      type: 'line',
      data: trend.value.map(item => item.cost),
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { color: '#8b5cf6', width: 2 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(139,92,246,0.15)' }, { offset: 1, color: 'rgba(139,92,246,0)' }] } },
      itemStyle: { color: '#8b5cf6' },
    }],
  }
})

async function handleCopy(): Promise<void> {
  if (!fullKey.value) return
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(fullKey.value)
    } else {
      const ta = document.createElement('textarea')
      ta.value = fullKey.value
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    /* ignore */
  }
}

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    model: t('identity.type.model'),
    mcp: t('identity.type.mcp'),
    skill: t('identity.type.skill'),
    agent: t('identity.type.agent'),
  }
  return labels[type] || type
}

function getStatusLabel(status: string): string {
  if (status === 'pending') return t('identity.status.pending')
  if (status === 'approved') return t('identity.status.approved')
  return t('identity.status.rejected')
}

function getModelIconUrl(modelId: string): string {
  return modelIconUrls.value[modelId] || '/icons/v1/default.svg'
}

onMounted(async () => {
  try {
    const [keysData, kpiData, trendData, appsData, mcpRes, skillRes, activeModelsData, configData] = await Promise.all([
      getMyKeys().catch(() => ({ personal: [] as AiKey[], department: [] as AiKey[], project: [] as AiKey[] })),
      request<EfficiencyKpi>('/api/v1/efficiency/overview', { params: { scope: 'self' }, silent: true }).catch(() => null),
      request<TrendItem[]>('/api/v1/efficiency/trend', { params: { scope: 'self', group_by: 'day' }, silent: true }).catch(() => []),
      request<{ items: ResourceApplication[] }>('/api/v1/resource-applications/my', { params: { page: 1, page_size: 10 }, silent: true }).catch(() => ({ items: [] as ResourceApplication[] })),
      request<{ items: McpServer[] }>('/api/v1/mcp/servers/published', { params: { page_size: 200 }, silent: true }).catch(() => ({ items: [] })),
      request<{ items: Skill[] }>('/api/v1/skills/published', { params: { page_size: 200 }, silent: true }).catch(() => ({ items: [] })),
      request<ActiveModel[]>('/api/v1/models/active', { silent: true }).catch(() => []),
      request<{ litellm_base_url: string }>('/api/v1/config/public', { silent: true }).catch(() => ({ litellm_base_url: '' })),
    ])
    mainKey.value = keysData.personal.find(k => k.key_type === 'personal_main') ?? null
    kpi.value = kpiData
    trend.value = trendData
    applications.value = appsData.items
    endpointUrl.value = configData.litellm_base_url || ''
    modelIconUrls.value = Object.fromEntries(
      activeModelsData.map(model => [model.model_id, model.icon_url]),
    )

    for (const m of mcpRes.items) {
      mcpNames.value[m.id] = m.name
    }
    for (const s of skillRes.items) {
      skillNames.value[s.id] = s.name
    }
  } catch { /* */ }
  finally { isLoading.value = false }
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-6 py-8">
    <!-- 加载态 -->
    <div v-if="isLoading" class="space-y-6">
      <div class="h-48 animate-pulse rounded-2xl bg-white" />
      <div class="h-32 animate-pulse rounded-2xl bg-white" />
    </div>

    <template v-else>
      <!-- AI 身份证 -->
      <section class="rounded-[24px] border border-white/80 bg-white/35 p-2.5 shadow-[0_20px_60px_rgba(20,30,60,.08)] backdrop-blur-xl">
        <div class="relative min-h-[280px] overflow-hidden rounded-[18px] bg-gradient-to-br from-white to-[#f6f4ff]">
          <!-- 右侧区域：用户头像或紫色背景 -->
          <div v-if="currentUser?.avatar" class="absolute right-0 top-0 h-full w-[30%] overflow-hidden" style="clip-path: polygon(30% 0, 100% 0, 100% 100%, 0 100%)">
            <img :src="currentUser.avatar" alt="" class="h-full w-full object-cover" />
          </div>
          <div v-else class="absolute right-0 top-0 h-full w-[30%] bg-gradient-to-br from-[#8C74FF] to-[#6D56FF]" style="clip-path: polygon(30% 0, 100% 0, 100% 100%, 0 100%)">
            <div class="absolute right-6 top-12 select-none text-[120px] font-extrabold leading-none text-white/[.08]">AI</div>
          </div>

          <!-- 内容区 -->
          <div class="relative z-10 w-[72%] p-6">
            <!-- 顶部 Logo + 状态 -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-[#8C74FF] to-[#6D56FF] text-sm font-bold text-white">
                  AI
                </div>
                <div>
                  <h3 class="text-sm font-extrabold text-gray-900">{{ t('identity.card.title') }}</h3>
                  <p class="text-[10px] tracking-[1.5px] text-gray-400">ACCESS PASS</p>
                </div>
              </div>
              <span v-if="mainKey" class="rounded-xl px-3 py-1.5 text-xs font-bold"
                :class="mainKey.is_active ? 'bg-[#F3F0FF] text-[#6D56FF]' : 'bg-slate-100 text-slate-500'">
                {{ mainKey.is_active ? t('identity.card.active') : t('identity.card.inactive') }}
              </span>
            </div>

            <!-- 用户信息 -->
            <div class="mt-5 flex items-center gap-4">
              <div>
                <h1 class="text-xl font-extrabold leading-none text-gray-900">{{ currentUser?.display_name || currentUser?.username }}</h1>
                <p class="mt-1 text-sm text-gray-400">{{ currentUser?.email }}</p>
                <p v-if="currentUser?.departments?.length" class="mt-1 text-xs text-gray-500">
                  {{ currentUser.departments.map(d => d.name).join(' / ') }}
                  <span v-if="currentUser?.position" class="ml-1.5 text-gray-400">{{ currentUser.position }}</span>
                </p>
              </div>
            </div>

            <!-- Key 区域 -->
            <div v-if="mainKey" class="mt-5 rounded-2xl border border-purple-500/[.12] bg-white/80 px-5 py-4 backdrop-blur-[10px]">
              <div class="flex items-center justify-between">
                <div class="flex-1">
                  <div class="text-[11px] font-bold tracking-[1px] text-[#7B61FF]">API KEY</div>
                  <code class="mt-1.5 block break-all text-sm font-bold text-gray-900">{{ displayKey }}</code>
                </div>
                <div class="flex shrink-0 gap-1.5">
                  <button @click="showFullKey = !showFullKey"
                    class="flex items-center justify-center rounded-lg border border-slate-200/60 bg-white p-1.5 text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700">
                    <EyeOff v-if="showFullKey" class="h-4 w-4" />
                    <Eye v-else class="h-4 w-4" />
                  </button>
                  <button @click="handleCopy"
                    class="flex items-center gap-1 rounded-lg border border-purple-200/60 bg-white px-3 py-1.5 text-xs font-medium text-purple-700 transition-colors hover:bg-purple-50">
                    <Check v-if="copied" class="h-3 w-3 text-green-600" />
                    <Copy v-else class="h-3 w-3" />
                    {{ copied ? t('identity.action.copied') : t('identity.action.copy') }}
                  </button>
                </div>
              </div>

              <!-- 底部 meta -->
              <div class="mt-3 flex gap-6 border-t border-slate-100 pt-3">
                <div>
                  <div class="text-[10px] tracking-[1px] text-gray-400">{{ t('identity.card.budget') }}</div>
                  <div class="mt-0.5 text-xs font-bold text-gray-900">{{ budgetDisplay }}</div>
                </div>
                <div>
                  <div class="text-[10px] tracking-[1px] text-gray-400">{{ t('identity.card.models') }}</div>
                  <div class="mt-0.5 text-xs font-bold text-gray-900">{{ mainKey.models.length }}</div>
                </div>
                <div>
                  <div class="text-[10px] tracking-[1px] text-gray-400">MCP</div>
                  <div class="mt-0.5 text-xs font-bold text-gray-900">{{ mainKey.mcps.length }}</div>
                </div>
                <div>
                  <div class="text-[10px] tracking-[1px] text-gray-400">Skill</div>
                  <div class="mt-0.5 text-xs font-bold text-gray-900">{{ mainKey.skills.length }}</div>
                </div>
              </div>
            </div>
            <div v-else class="mt-5 text-center text-sm text-slate-400">
              {{ t('identity.noIdentity') }}
            </div>
          </div>
        </div>
      </section>

      <!-- 用量概览 -->
      <section v-if="kpi" class="mt-6 rounded-2xl border border-slate-200/60 bg-white/70 p-5 backdrop-blur">
        <h2 class="mb-4 text-sm font-medium text-slate-900">{{ t('identity.overview.title') }}</h2>
        <div class="relative">
        <div class="absolute inset-0 z-10 flex select-none items-center justify-center rounded-xl bg-white/40 backdrop-blur-md">
          <span class="rounded-full bg-white/80 px-4 py-2 text-sm font-medium text-slate-600 shadow-sm">
            {{ t('identity.overview.upgradeHint') }}
          </span>
        </div>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div class="rounded-xl bg-slate-50/80 px-4 py-3">
            <div class="text-xs text-slate-400">{{ t('identity.overview.monthBudget') }}</div>
            <div class="mt-1 text-lg font-semibold text-slate-900">{{ budgetDisplay }}</div>
          </div>
          <div class="rounded-xl bg-slate-50/80 px-4 py-3">
            <div class="text-xs text-slate-400">{{ t('identity.overview.spent') }}</div>
            <div class="mt-1 text-lg font-semibold text-slate-900">¥{{ (kpi.total_cost ?? 0).toFixed(2) }}</div>
            <div v-if="budgetUsedPercent !== null" class="mt-0.5 text-xs text-slate-400">{{ budgetUsedPercent.toFixed(1) }}%</div>
          </div>
          <div class="rounded-xl bg-slate-50/80 px-4 py-3">
            <div class="text-xs text-slate-400">{{ t('identity.overview.requests') }}</div>
            <div class="mt-1 text-lg font-semibold text-slate-900">{{ (kpi.total_requests ?? 0).toLocaleString() }}</div>
          </div>
          <div class="rounded-xl bg-slate-50/80 px-4 py-3">
            <div class="text-xs text-slate-400">{{ t('identity.overview.dailyAvg') }}</div>
            <div class="mt-1 text-lg font-semibold text-slate-900">¥{{ dailyAvgCost.toFixed(2) }}</div>
          </div>
        </div>
        <!-- Token 用量 -->
        <div class="mt-3 rounded-xl bg-slate-50/80 px-4 py-3">
          <div class="flex items-baseline gap-2">
            <span class="text-xs text-slate-400">{{ t('identity.overview.tokens') }}</span>
            <span class="text-lg font-semibold text-slate-900">{{ formatBigToken(kpi.total_tokens ?? 0) }}</span>
          </div>
          <div class="mt-2.5 grid grid-cols-2 gap-x-3 gap-y-2 border-t border-slate-200/70 pt-2.5 sm:grid-cols-4">
            <div v-for="item in tokenBreakdown" :key="item.labelKey">
              <div class="flex items-center gap-1.5">
                <span class="h-1.5 w-1.5 shrink-0 rounded-full" :style="{ backgroundColor: item.color }" />
                <span class="text-xs text-slate-400">{{ t(item.labelKey) }}</span>
              </div>
              <div class="mt-0.5 text-sm font-medium text-slate-700">{{ formatBigToken(item.value) }}</div>
            </div>
          </div>
        </div>
        <!-- 预算进度条 -->
        <div v-if="budgetUsedPercent !== null" class="mt-4">
          <div class="flex items-center justify-between text-xs text-slate-400">
            <span>{{ t('identity.overview.budgetUsage') }}</span>
            <span>{{ budgetUsedPercent.toFixed(1) }}%</span>
          </div>
          <div class="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
            <div class="h-full rounded-full transition-all"
              :class="budgetUsedPercent > 100 ? 'bg-red-500' : budgetUsedPercent > 80 ? 'bg-amber-500' : 'bg-purple-500'"
              :style="{ width: `${Math.min(budgetUsedPercent, 100)}%` }" />
          </div>
        </div>
        <!-- 趋势图表 -->
        <div v-if="trend.length" class="mt-5">
          <div class="mb-2 flex justify-end gap-1">
            <button
              v-for="mode in (['cost', 'token'] as const)" :key="mode"
              class="rounded-md px-2.5 py-1 text-xs font-medium transition-colors"
              :class="chartMode === mode
                ? 'bg-purple-50 text-purple-700'
                : 'text-slate-400 hover:bg-slate-50 hover:text-slate-600'"
              @click="chartMode = mode"
            >
              {{ mode === 'cost' ? t('identity.overview.chartCost') : t('identity.overview.chartToken') }}
            </button>
          </div>
          <VChart :option="chartOption" style="height: 200px; width: 100%" autoresize />
        </div>
        </div>
      </section>

      <!-- 我的资源 -->
      <section v-if="mainKey" class="mt-6 space-y-4">
        <div class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 backdrop-blur">
          <div class="mb-3 flex items-center gap-2">
            <Cpu class="h-4 w-4 text-purple-600" />
            <span class="text-sm font-medium text-slate-900">{{ t('identity.resources.model') }}</span>
            <span class="ml-auto text-xs text-slate-400">{{ t('identity.resources.count', { count: mainKey.models.length }) }}</span>
          </div>
          <div v-if="mainKey.models.length" class="flex flex-wrap gap-2">
            <span v-for="m in mainKey.models" :key="m"
              class="flex items-center gap-1.5 rounded-md bg-purple-50 px-2.5 py-1 text-xs font-medium text-purple-700">
              <ProviderIcon :src="getModelIconUrl(m)" :size="14" />
              {{ m }}
            </span>
          </div>
          <p v-else class="text-xs text-slate-400">{{ t('identity.resources.emptyModels') }}</p>
        </div>

        <div class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 backdrop-blur">
          <div class="mb-3 flex items-center gap-2">
            <Server class="h-4 w-4 text-emerald-600" />
            <span class="text-sm font-medium text-slate-900">MCP</span>
            <span class="ml-auto text-xs text-slate-400">{{ t('identity.resources.count', { count: mainKey.mcps.length }) }}</span>
          </div>
          <div v-if="mainKey.mcps.length" class="flex flex-wrap gap-2">
            <span v-for="id in mainKey.mcps" :key="id"
              class="rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">{{ mcpNames[id] || `#${id}` }}</span>
          </div>
          <p v-else class="text-xs text-slate-400">{{ t('identity.resources.emptyMarket') }}</p>
        </div>

        <div class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 backdrop-blur">
          <div class="mb-3 flex items-center gap-2">
            <Sparkles class="h-4 w-4 text-amber-500" />
            <span class="text-sm font-medium text-slate-900">Skill</span>
            <span class="ml-auto text-xs text-slate-400">{{ t('identity.resources.count', { count: mainKey.skills.length }) }}</span>
          </div>
          <div v-if="mainKey.skills.length" class="flex flex-wrap gap-2">
            <span v-for="id in mainKey.skills" :key="id"
              class="rounded-md bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">{{ skillNames[id] || `#${id}` }}</span>
          </div>
          <p v-else class="text-xs text-slate-400">{{ t('identity.resources.emptyMarket') }}</p>
        </div>
      </section>

      <!-- 我的申请 -->
      <section v-if="applications.length" class="mt-6 rounded-2xl border border-slate-200/60 bg-white/70 p-5 backdrop-blur">
        <h2 class="mb-4 text-sm font-medium text-slate-900">{{ t('identity.applications.title') }}</h2>
        <div class="space-y-2">
          <div v-for="app in applications" :key="app.id"
            class="flex items-center gap-3 rounded-lg bg-slate-50/80 px-4 py-2.5">
            <Clock v-if="app.status === 'pending'" class="h-4 w-4 shrink-0 text-amber-500" />
            <CheckCircle2 v-else-if="app.status === 'approved'" class="h-4 w-4 shrink-0 text-green-500" />
            <XCircle v-else class="h-4 w-4 shrink-0 text-red-400" />
            <span class="rounded bg-white px-1.5 py-0.5 text-xs text-slate-500">{{ getTypeLabel(app.resource_type) }}</span>
            <span class="flex-1 truncate text-sm text-slate-900">{{ app.resource_info?.name || `#${app.resource_id}` }}</span>
            <span class="text-xs text-slate-400">{{ getStatusLabel(app.status) }}</span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
