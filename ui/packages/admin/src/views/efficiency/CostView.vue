<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronDown, RefreshCw } from 'lucide-vue-next'
import { createExportTask, getEfficiencyCost, getEfficiencyCostDetail, getEfficiencyCostDetailScopeUsers, getEfficiencyTopUsers, toast } from '@aihelms/shared'
import ExportTaskNotice from '../../components/ExportTaskNotice.vue'
import ScopePickerDialog from '../../components/ScopePickerDialog.vue'
import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'
import PresetTabs from './components/PresetTabs.vue'
import CostCharts from './components/CostCharts.vue'
import UserTop10Panel from './components/UserTop10Panel.vue'
import CostDetailSection from './components/CostDetailSection.vue'
import { formatCost, formatCostShort, formatNumber, formatChange, presetToRange, submitEfficiencyRefresh, keepRefreshIndicator } from './utils'
import { useScopeFilter } from './useScopeFilter'

import type { AttributionRow, CostComposition, CostKpi, CostTrendItem, DateDetailRow, DetailTab, McpDetailRow, McpToolRow, ModelCredentialRow, ModelDetailRow, PerCapitaItem, ScopeDetailRow, ScopeUserCostRow, UserTop10Row } from './costTypes'

const TIME_PRESETS = [
  { key: 'today', label: '今天' },
  { key: 'yesterday', label: '昨天' },
  { key: 'month', label: '本月' },
  { key: '7d', label: '近7天' },
  { key: '30d', label: '近30天' },
]

const RESOURCE_TYPES = [
  { key: '', label: '全部' },
  { key: 'llm', label: 'LLM' },
  { key: 'mcp', label: 'MCP' },
]

const router = useRouter()

const activePreset = ref('month')
const resourceType = ref('')
const dimension = ref<'department' | 'project'>('department')
const {
  departmentTree,
  handleScopeConfirm,
  isScopePickerOpen,
  loadScopeOptions,
  projectOptions,
  resetScopeSelection,
  selectedScopeIds,
  selectedScopeLabel,
} = useScopeFilter(dimension, loadOverview)
const activeDetailTab = ref<DetailTab>('department')
const customStart = ref('')
const customEnd = ref('')
const isLoading = ref(true)
const isRefreshing = ref(false)
const isDetailLoading = ref(false)
const exporting = ref(false)
const exportNotice = ref('')
const lastUpdatedAt = ref<Date | null>(null)

const kpi = ref<CostKpi>({ total_cost: 0, external_cost: 0, cost_diff: 0, daily_avg_cost: 0, cost_change: null })
const trendData = ref<CostTrendItem[]>([])
const composition = ref<CostComposition>({ by_resource_type: [], by_scope: [] })
const perCapita = ref<PerCapitaItem[]>([])
const scopeDetail = ref<ScopeDetailRow[]>([])
const expandedScopeId = ref<number | null>(null)
const scopeUsers = ref<ScopeUserCostRow[]>([])
const scopeUsersLoading = ref(false)
const topMetric = ref<'cost' | 'tokens' | 'requests'>('cost')
const topRows = ref<UserTop10Row[]>([])
const topLoading = ref(false)
const modelDetail = ref<ModelDetailRow[]>([])
const mcpDetail = ref<McpDetailRow[]>([])
const dateDetail = ref<DateDetailRow[]>([])
const attributionDetail = ref<AttributionRow[]>([])

const dimensionLabel = computed(() => (dimension.value === 'project' ? '项目' : '部门'))
const scopeRows = computed(() => composition.value.by_scope || composition.value.by_department || [])
const dimensionCostNote = '跨部门、跨项目归属的成本会在对应维度重复计算。平台总成本仍按调用记录去重统计。'

const detailTabs = computed(() => [
  { key: 'department' as const, label: `按${dimensionLabel.value}` },
  { key: 'model' as const, label: '按模型' },
  { key: 'mcp' as const, label: '按MCP' },
  { key: 'date' as const, label: '按日期' },
  { key: 'attribution' as const, label: '成本流水' },
])

function getDateParams(): Record<string, string> {
  if (activePreset.value === 'custom' && customStart.value && customEnd.value) {
    return { start_date: customStart.value, end_date: customEnd.value }
  }
  return { period: activePreset.value }
}

function getBaseParams(): Record<string, string> {
  const params: Record<string, string> = { ...getDateParams(), dimension: dimension.value }
  if (resourceType.value) params.resource_type = resourceType.value
  if (selectedScopeIds.value.length) params.scope_ids = selectedScopeIds.value.join(',')
  return params
}

function getLogDateQuery(): Record<string, string> {
  if (activePreset.value === 'custom' && customStart.value && customEnd.value) {
    return { start_date: customStart.value, end_date: customEnd.value }
  }
  const range = presetToRange(activePreset.value)
  return { start_date: range.start, end_date: range.end }
}


function pushLogs(tab: 'llm' | 'mcp', params: Record<string, string | number | undefined | null>) {
  const query: Record<string, string | number> = { tab, ...getLogDateQuery() }
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query[key] = value
  })
  router.push({ path: '/logs', query })
}

function openModelLogs(row: ModelDetailRow) {
  const routeModels = Array.from(new Set(row.credentials.map((item) => item.route_model).filter(Boolean)))
  if (routeModels.length > 1) {
    pushLogs('llm', { models: routeModels.join(',') })
    return
  }
  pushLogs('llm', { model: routeModels[0] || row.model_id || row.model })
}

function openModelCredentialLogs(row: ModelCredentialRow) {
  pushLogs('llm', { model: row.route_model })
}

function openMcpLogs(row: McpDetailRow) {
  pushLogs('mcp', { server_id: row.server_id || undefined })
}

function openMcpToolLogs(row: McpDetailRow, tool: McpToolRow) {
  pushLogs('mcp', { server_id: row.server_id || undefined, tool_name: tool.tool_name })
}

function openDateLogs(tab: 'llm' | 'mcp', date: string) {
  pushLogs(tab, { start_date: date, end_date: date })
}

function openAttributionLogs(row: AttributionRow) {
  const tab = row.resource_type === 'mcp' ? 'mcp' : 'llm'
  pushLogs(tab, {
    start_date: row.date,
    end_date: row.date,
    user_id: row.user_id || undefined,
    ai_key_id: row.ai_key_id || undefined,
    model: tab === 'llm' ? row.model || row.cost_object : undefined,
    server_id: tab === 'mcp' ? row.server_id || undefined : undefined,
  })
}

function formatResourceName(name: string): string {
  if (name === 'llm') return 'LLM'
  if (name === 'mcp') return 'MCP'
  return name
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

async function refreshData() {
  isRefreshing.value = true
  let queued = false
  try {
    await submitEfficiencyRefresh('cost')
    queued = true
    toast.info('数据更新中，请稍后刷新页面查看', 8000)
  } catch (e) {
    toast.error((e as { message?: string }).message || '刷新失败')
  } finally {
    if (queued) await keepRefreshIndicator()
    isRefreshing.value = false
  }
}

async function loadOverview() {
  isLoading.value = true
  try {
    const res = await getEfficiencyCost<{
      kpi: CostKpi
      trend: CostTrendItem[]
      composition: CostComposition
      per_capita: PerCapitaItem[]
      freshness?: { last_updated_at: string | null; last_updated_label: string }
    }>(getBaseParams())
    kpi.value = res.kpi
    trendData.value = res.trend
    composition.value = res.composition
    perCapita.value = res.per_capita
    lastUpdatedAt.value = res.freshness?.last_updated_at ? new Date(res.freshness.last_updated_at) : new Date()
  } finally {
    isLoading.value = false
  }
  await loadDetail()
  await loadTopUsers()
}

async function loadTopUsers() {
  topLoading.value = true
  try {
    topRows.value = await getEfficiencyTopUsers<UserTop10Row[]>({
      ...getBaseParams(),
      metric: topMetric.value,
    })
  } finally {
    topLoading.value = false
  }
}

function handleTopMetricChange(metric: 'cost' | 'tokens' | 'requests') {
  topMetric.value = metric
  loadTopUsers()
}

async function loadDetail() {
  isDetailLoading.value = true
  try {
    const res = await getEfficiencyCostDetail<{
      department?: ScopeDetailRow[]
      model?: ModelDetailRow[]
      mcp?: McpDetailRow[]
      date?: DateDetailRow[]
      attribution?: AttributionRow[]
      freshness?: { last_updated_at: string | null; last_updated_label: string }
    }>({ ...getBaseParams(), tab: activeDetailTab.value })
    if (res.department) {
      scopeDetail.value = res.department
      expandedScopeId.value = null
      scopeUsers.value = []
    }
    if (res.model) {
      modelDetail.value = res.model
    }
    if (res.mcp) {
      mcpDetail.value = res.mcp
    }
    if (res.date) dateDetail.value = res.date
    if (res.attribution) attributionDetail.value = res.attribution
  } finally {
    isDetailLoading.value = false
  }
}

function handlePresetChange(val: string) {
  activePreset.value = val
  loadOverview()
}

function applyCustomRange() {
  if (customStart.value && customEnd.value) {
    activePreset.value = 'custom'
    loadOverview()
  }
}

function handleResourceChange(val: string) {
  resourceType.value = val
  loadOverview()
}

function handleDimensionChange(val: 'department' | 'project') {
  dimension.value = val
  resetScopeSelection()
  activeDetailTab.value = 'department'
  loadOverview()
}

function handleDetailTabChange(tab: DetailTab) {
  activeDetailTab.value = tab
  expandedScopeId.value = null
  scopeUsers.value = []
  loadDetail()
}

async function toggleScopeUsers(row: ScopeDetailRow) {
  if (row.scope_id === null) return
  if (expandedScopeId.value === row.scope_id) {
    expandedScopeId.value = null
    scopeUsers.value = []
    return
  }
  expandedScopeId.value = row.scope_id
  scopeUsers.value = []
  scopeUsersLoading.value = true
  try {
    const params: Record<string, string> = { ...getDateParams(), dimension: dimension.value, scope_id: String(row.scope_id) }
    if (resourceType.value) params.resource_type = resourceType.value
    scopeUsers.value = await getEfficiencyCostDetailScopeUsers<ScopeUserCostRow[]>(params)
  } finally {
    scopeUsersLoading.value = false
  }
}


async function exportDetail() {
  exporting.value = true
  try {
    await createExportTask({
      source: 'efficiency',
      export_type: `cost_${activeDetailTab.value}`,
      task_name: `成本分析-${detailTabs.value.find((tab) => tab.key === activeDetailTab.value)?.label || '明细'}`,
      params: getBaseParams(),
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
  legend: { data: ['LLM内部', 'LLM外部', 'MCP内部', 'MCP外部'], bottom: 0 },
  grid: { top: 18, right: 20, bottom: 44, left: 64 },
  xAxis: { type: 'category', name: '日期', data: trendData.value.map((d) => d.date), axisLabel: { fontSize: 10 } },
  yAxis: { type: 'value', name: '成本', axisLabel: { formatter: (v: number) => formatCostShort(v), fontSize: 10 } },
  series: [
    { name: 'LLM内部', type: 'line', smooth: true, data: trendData.value.map((d) => d.llm_cost), itemStyle: { color: '#2563eb' }, lineStyle: { color: '#2563eb' } },
    { name: 'LLM外部', type: 'line', smooth: true, data: trendData.value.map((d) => d.llm_external_cost), itemStyle: { color: '#f59e0b' }, lineStyle: { color: '#f59e0b', type: 'dashed' } },
    { name: 'MCP内部', type: 'line', smooth: true, data: trendData.value.map((d) => d.mcp_cost), itemStyle: { color: '#059669' }, lineStyle: { color: '#059669' } },
    { name: 'MCP外部', type: 'line', smooth: true, data: trendData.value.map((d) => d.mcp_external_cost), itemStyle: { color: '#0f766e' }, lineStyle: { color: '#0f766e', type: 'dashed' } },
  ],
}))

const resourceCostOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['内部成本', '外部成本'], bottom: 0 },
  grid: { top: 20, right: 20, bottom: 40, left: 64 },
  xAxis: { type: 'category', name: '资源类型', data: composition.value.by_resource_type.map((d) => formatResourceName(d.name)) },
  yAxis: { type: 'value', name: '成本', axisLabel: { formatter: (v: number) => formatCostShort(v) } },
  series: [
    { name: '内部成本', type: 'bar', data: composition.value.by_resource_type.map((d) => d.internal_cost), itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] } },
    { name: '外部成本', type: 'bar', data: composition.value.by_resource_type.map((d) => d.external_cost), itemStyle: { color: '#f59e0b', borderRadius: [4, 4, 0, 0] } },
  ],
}))

const scopeCostOption = computed(() => {
  const rows = scopeRows.value.slice(0, 12)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['内部成本', '外部成本'], bottom: 0 },
    grid: { top: 20, right: 20, bottom: 52, left: 64 },
    xAxis: { type: 'category', name: dimensionLabel.value, data: rows.map((d) => d.name), axisLabel: { interval: 0, rotate: 25, fontSize: 10 } },
    yAxis: { type: 'value', name: '成本', axisLabel: { formatter: (v: number) => formatCostShort(v) } },
    series: [
      { name: '内部成本', type: 'bar', data: rows.map((d) => d.internal_cost), itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] } },
      { name: '外部成本', type: 'bar', data: rows.map((d) => d.external_cost), itemStyle: { color: '#f59e0b', borderRadius: [4, 4, 0, 0] } },
    ],
  }
})

const perCapitaOption = computed(() => {
  const sorted = [...perCapita.value].sort((a, b) => a.per_capita_cost - b.per_capita_cost).slice(-12)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 10, right: 36, bottom: 10, left: 104 },
    xAxis: { type: 'value', name: '成本', axisLabel: { formatter: (v: number) => formatCostShort(v), fontSize: 10 } },
    yAxis: { type: 'category', name: dimensionLabel.value, data: sorted.map((d) => d.name || d.department || ''), axisLabel: { fontSize: 10 } },
    series: [{ type: 'bar', data: sorted.map((d) => d.per_capita_cost), itemStyle: { color: '#64748b', borderRadius: [0, 4, 4, 0] }, barMaxWidth: 20 }],
  }
})

onMounted(() => {
  loadScopeOptions()
  loadOverview()
})
</script>

<template>
  <div class="space-y-4">
    <ExportTaskNotice v-if="exportNotice" />
    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-xs text-slate-500">时间</span>
        <PresetTabs :model-value="activePreset" :presets="TIME_PRESETS" @update:model-value="handlePresetChange" />
        <div class="flex items-center gap-1.5">
          <input v-model="customStart" type="date" class="rounded-md border border-slate-200 px-2 py-1 text-xs" />
          <span class="text-xs text-slate-400">~</span>
          <input v-model="customEnd" type="date" class="rounded-md border border-slate-200 px-2 py-1 text-xs" />
          <button class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 hover:bg-slate-50" @click="applyCustomRange">查询</button>
        </div>
        <span class="text-xs text-slate-500">资源类型</span>
        <div class="inline-flex rounded-lg bg-slate-100 p-1">
          <button v-for="rt in RESOURCE_TYPES" :key="rt.key" class="rounded-md px-3 py-1 text-xs transition-colors" :class="resourceType === rt.key ? 'bg-white font-medium text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'" @click="handleResourceChange(rt.key)">{{ rt.label }}</button>
        </div>
        <span class="text-xs text-slate-500">归属维度</span>
        <div class="inline-flex rounded-lg bg-slate-100 p-1">
          <button class="rounded-md px-3 py-1 text-xs transition-colors" :class="dimension === 'department' ? 'bg-white font-medium text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'" @click="handleDimensionChange('department')">部门</button>
          <button class="rounded-md px-3 py-1 text-xs transition-colors" :class="dimension === 'project' ? 'bg-white font-medium text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'" @click="handleDimensionChange('project')">项目</button>
        </div>
        <button type="button" class="inline-flex min-w-[152px] items-center justify-between gap-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 hover:bg-slate-50" @click="isScopePickerOpen = true">
          <span class="truncate">{{ selectedScopeLabel }}</span>
          <ChevronDown class="h-3.5 w-3.5 text-slate-400" />
        </button>
        <div class="ml-auto flex items-center gap-2 text-xs text-slate-500">
          <span>最后更新时间：{{ formatLastUpdated() }}</span>
          <button type="button" class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60" :disabled="isRefreshing" @click.prevent="refreshData">
            <RefreshCw class="h-3.5 w-3.5" :class="isRefreshing ? 'animate-spin' : ''" /> {{ isRefreshing ? '更新中' : '点击更新' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
    </div>

    <template v-if="!isLoading">
      <div class="grid grid-cols-4 gap-4">
        <KpiCard label="内部成本" :value="formatCost(kpi.total_cost)" :change="kpi.cost_change" change-kind="up-bad" tooltip="所选时间内平台计费口径的内部成本合计。公式：LLM内部成本 + MCP内部成本。" />
        <KpiCard label="外部成本" :value="formatCost(kpi.external_cost)" change-kind="neutral" change-text="" tooltip="外部成本 = 所选时间内平台已记录的供应商侧成本合计。" />
        <KpiCard label="成本差额" :value="formatCost(kpi.cost_diff)" change-kind="neutral" :value-color="kpi.cost_diff >= 0 ? 'text-emerald-600' : 'text-red-600'" change-text="" tooltip="内部成本 - 外部成本。正数表示平台计费高于外部成本，负数表示平台计费低于外部成本。" />
        <KpiCard label="日均内部成本" :value="formatCost(kpi.daily_avg_cost)" change-kind="neutral" change-text="" tooltip="内部成本 / 所选自然日天数。" />
      </div>

      <CostCharts
        :trend-chart-option="trendChartOption"
        :resource-cost-option="resourceCostOption"
        :scope-cost-option="scopeCostOption"
        :per-capita-option="perCapitaOption"
        :dimension-label="dimensionLabel"
        :dimension-cost-note="dimensionCostNote"
      />

      <UserTop10Panel
        :metric="topMetric"
        :rows="topRows"
        :loading="topLoading"
        @metric-change="handleTopMetricChange"
      />

      <CostDetailSection
        :active-detail-tab="activeDetailTab"
        :detail-tabs="detailTabs"
        :is-detail-loading="isDetailLoading"
        :exporting="exporting"
        :dimension-label="dimensionLabel"
        :scope-detail="scopeDetail"
        :model-detail="modelDetail"
        :mcp-detail="mcpDetail"
        :date-detail="dateDetail"
        :attribution-detail="attributionDetail"
        :expanded-scope-id="expandedScopeId"
        :scope-users="scopeUsers"
        :scope-users-loading="scopeUsersLoading"
        @tab-change="handleDetailTabChange"
        @export-detail="exportDetail"
        @toggle-scope-users="toggleScopeUsers"
        @open-model-logs="openModelLogs"
        @open-model-credential-logs="openModelCredentialLogs"
        @open-mcp-logs="openMcpLogs"
        @open-mcp-tool-logs="openMcpToolLogs"
        @open-date-logs="openDateLogs"
        @open-attribution-logs="openAttributionLogs"
      />
    </template>
    <ScopePickerDialog v-model:open="isScopePickerOpen" v-model="selectedScopeIds" :dimension="dimension" :department-tree="departmentTree" :project-options="projectOptions" @confirm="handleScopeConfirm" />
  </div>
</template>
