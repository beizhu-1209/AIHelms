<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Download, ChevronDown, ChevronUp, RefreshCw } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { createExportTask, getEfficiencyAdoption, getEfficiencyAdoptionAgents, getEfficiencyAdoptionResources, getEfficiencyAdoptionScopeUsers, getEfficiencyAdoptionUnusedUsers, toast } from '@aihelms/shared'
import ExportTaskNotice from '../../components/ExportTaskNotice.vue'
import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'
import PresetTabs from './components/PresetTabs.vue'
import AdoptionResourceSections from './components/AdoptionResourceSections.vue'
import { presetToRange, submitEfficiencyRefresh, keepRefreshIndicator } from './utils'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

import type { ActiveTrend, AdoptionKpi, AgentRow, DeptCoverageRow, DepthDistribution, HeavyTrend, ResourceRow, ScopeUserRow, UnusedUser } from './adoptionTypes'

const router = useRouter()

const timePreset = ref('month')
const customStart = ref('')
const customEnd = ref('')
const dimension = ref<'department' | 'project'>('department')
const unusedExpanded = ref(false)
const expandedScopeId = ref<number | null>(null)
const scopeUsers = ref<ScopeUserRow[]>([])
const scopeUsersLoading = ref(false)
const lastUpdatedLabel = ref('--')

const dimensionText = computed(() => (dimension.value === 'project' ? '项目' : '部门'))

const isLoading = ref(true)
const isRefreshing = ref(false)
const exportingKey = ref('')
const exportNotice = ref('')
const kpi = ref<AdoptionKpi | null>(null)
const activeTrend = ref<ActiveTrend | null>(null)
const depthDist = ref<DepthDistribution | null>(null)
const heavyTrend = ref<HeavyTrend | null>(null)
const deptTable = ref<DeptCoverageRow[]>([])
const agents = ref<AgentRow[]>([])
const mcpResources = ref<ResourceRow[]>([])
const skillResources = ref<ResourceRow[]>([])
const unusedUsers = ref<UnusedUser[]>([])

const deptSortKey = ref<keyof DeptCoverageRow>('coverage_rate')
const deptSortAsc = ref(false)

const TIME_PRESETS = [{ key: 'month', label: '本月' }, { key: '7d', label: '近7天' }, { key: '30d', label: '近30天' }]

function getDateParams(): Record<string, string> {
  if (timePreset.value === 'custom' && customStart.value && customEnd.value) {
    return { start_date: customStart.value, end_date: customEnd.value }
  }
  return { period: timePreset.value }
}

async function loadData() {
  isLoading.value = true
  const params = { ...getDateParams(), dimension: dimension.value }
  try {
    const [adoptionData, agentData, mcpData, skillData, unusedData] = await Promise.all([
      getEfficiencyAdoption<{
        kpi: AdoptionKpi
        active_trend: ActiveTrend
        depth_distribution: DepthDistribution
        heavy_trend: HeavyTrend
        department_table: DeptCoverageRow[]
        freshness?: { last_updated_label: string }
      }>(params),
      getEfficiencyAdoptionAgents<AgentRow[]>(params),
      getEfficiencyAdoptionResources<ResourceRow[]>({ ...params, type: 'mcp' }),
      getEfficiencyAdoptionResources<ResourceRow[]>({ ...params, type: 'skill' }),
      getEfficiencyAdoptionUnusedUsers<UnusedUser[]>(params),
    ])
    kpi.value = adoptionData.kpi
    activeTrend.value = adoptionData.active_trend
    depthDist.value = adoptionData.depth_distribution
    heavyTrend.value = adoptionData.heavy_trend
    deptTable.value = adoptionData.department_table
    lastUpdatedLabel.value = adoptionData.freshness?.last_updated_label || '--'
    expandedScopeId.value = null
    scopeUsers.value = []
    agents.value = agentData
    mcpResources.value = mcpData
    skillResources.value = skillData
    unusedUsers.value = unusedData
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

function changeDimension(val: 'department' | 'project') {
  dimension.value = val
  loadData()
}

async function refreshData() {
  isRefreshing.value = true
  let queued = false
  try {
    await submitEfficiencyRefresh('adoption')
    queued = true
    toast.info('数据更新中，请稍后刷新页面查看', 8000)
  } catch (e) {
    toast.error((e as { message?: string }).message || '刷新失败')
  } finally {
    if (queued) await keepRefreshIndicator()
    isRefreshing.value = false
  }
}

function getLogDateQuery(): Record<string, string> {
  if (timePreset.value === 'custom' && customStart.value && customEnd.value) {
    return { start_date: customStart.value, end_date: customEnd.value }
  }
  const range = presetToRange(timePreset.value)
  return { start_date: range.start, end_date: range.end }
}

async function toggleScopeUsers(row: DeptCoverageRow) {
  if (expandedScopeId.value === row.id) {
    expandedScopeId.value = null
    scopeUsers.value = []
    return
  }
  expandedScopeId.value = row.id
  scopeUsers.value = []
  scopeUsersLoading.value = true
  try {
    scopeUsers.value = await getEfficiencyAdoptionScopeUsers<ScopeUserRow[]>({
      ...getDateParams(),
      dimension: dimension.value,
      scope_id: String(row.id),
    })
  } finally {
    scopeUsersLoading.value = false
  }
}

function openLogs(tab: 'llm' | 'mcp' | 'skill' | 'agent', params: Record<string, string | number>) {
  router.push({ path: '/logs', query: { tab, ...getLogDateQuery(), ...params } })
}


function toggleDeptSort(key: keyof DeptCoverageRow) {
  if (deptSortKey.value === key) {
    deptSortAsc.value = !deptSortAsc.value
  } else {
    deptSortKey.value = key
    deptSortAsc.value = false
  }
}

const sortedDeptTable = computed(() => {
  const rows = [...deptTable.value]
  rows.sort((a, b) => {
    const av = a[deptSortKey.value]
    const bv = b[deptSortKey.value]
    const cmp = typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv))
    return deptSortAsc.value ? cmp : -cmp
  })
  return rows
})

function deptSortIcon(key: keyof DeptCoverageRow): string {
  if (deptSortKey.value !== key) return ''
  return deptSortAsc.value ? ' ↑' : ' ↓'
}

async function createEfficiencyExport(exportType: string, taskName: string) {
  exportingKey.value = exportType
  try {
    await createExportTask({
      source: 'efficiency',
      export_type: exportType,
      task_name: taskName,
      params: { ...getDateParams(), dimension: dimension.value },
    })
    exportNotice.value = '导出任务已创建，请到资源审计 > 导出任务下载表格'
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建导出任务失败')
  } finally {
    exportingKey.value = ''
  }
}

function exportCoverage() {
  createEfficiencyExport('adoption_scope', `AI使用覆盖-${dimensionText.value}明细`)
}

function exportAgents() {
  createEfficiencyExport('adoption_agents', '智能体使用明细')
}

function exportResources(type: 'mcp' | 'skill') {
  createEfficiencyExport(type === 'mcp' ? 'adoption_mcp' : 'adoption_skill', type === 'mcp' ? 'MCP使用明细' : 'Skill使用明细')
}

function exportUnusedUsers() {
  createEfficiencyExport('adoption_unused_users', '未使用人员明细')
}


const activeTrendOption = computed(() => {
  if (!activeTrend.value) return {}
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 16, right: 16, bottom: 28, left: 50 },
    xAxis: { type: 'category', data: activeTrend.value.dates, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
    series: [{
      type: 'line', data: activeTrend.value.values, smooth: true,
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(99,102,241,0.2)' }, { offset: 1, color: 'rgba(99,102,241,0)' }] } },
      lineStyle: { color: '#6366f1' }, itemStyle: { color: '#6366f1' },
    }],
  }
})

const depthChartOption = computed(() => {
  if (!depthDist.value) return {}
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 8, right: 16, bottom: 24, left: 50 },
    xAxis: { type: 'category', data: ['轻度', '中度', '重度'], axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
    series: [{
      type: 'bar', data: [
        { value: depthDist.value.light, itemStyle: { color: '#a5b4fc' } },
        { value: depthDist.value.medium, itemStyle: { color: '#6366f1' } },
        { value: depthDist.value.heavy, itemStyle: { color: '#4338ca' } },
      ],
      barWidth: '40%', itemStyle: { borderRadius: [4, 4, 0, 0] },
    }],
  }
})

const heavyTrendOption = computed(() => {
  if (!heavyTrend.value) return {}
  return {
    tooltip: { trigger: 'axis', formatter: (p: { value: number }[]) => `${p[0]?.value ?? 0}%` },
    grid: { top: 8, right: 16, bottom: 24, left: 40 },
    xAxis: { type: 'category', data: heavyTrend.value.dates, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10, formatter: '{value}%' } },
    series: [{
      type: 'line', data: heavyTrend.value.ratios, smooth: true,
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(139,92,246,0.25)' }, { offset: 1, color: 'rgba(139,92,246,0)' }] } },
      lineStyle: { color: '#8b5cf6' }, itemStyle: { color: '#8b5cf6' },
    }],
  }
})

onMounted(loadData)
</script>

<template>
  <div class="space-y-4">
    <ExportTaskNotice v-if="exportNotice" />
    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-white/80 bg-white/60 px-4 py-2.5 shadow-sm backdrop-blur-xl">
      <span class="text-xs text-slate-500">时间</span>
      <PresetTabs :model-value="timePreset" :presets="TIME_PRESETS" @update:model-value="changePreset" />
      <div class="flex items-center gap-1.5 text-xs text-slate-500">
        <input v-model="customStart" type="date" class="rounded-md border border-slate-200 bg-white px-2 py-1.5 focus:border-indigo-300 focus:outline-none" />
        <span>至</span>
        <input v-model="customEnd" type="date" class="rounded-md border border-slate-200 bg-white px-2 py-1.5 focus:border-indigo-300 focus:outline-none" />
        <button class="rounded-md border border-slate-200 bg-white px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-50" @click="applyCustomRange">查询</button>
      </div>
      <div class="mx-2 h-4 w-px bg-slate-200"></div>
      <span class="text-xs text-slate-500">维度</span>
      <div class="inline-flex rounded-lg bg-slate-100/80 p-1">
        <button
          v-for="d in [{ k: 'department', l: '按部门' }, { k: 'project', l: '按项目' }]"
          :key="d.k"
          class="rounded-md px-3 py-1 text-xs transition-colors"
          :class="dimension === d.k ? 'bg-white font-medium text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
          @click="changeDimension(d.k as 'department' | 'project')"
        >
          {{ d.l }}
        </button>
      </div>
      <div class="ml-auto flex items-center gap-2 text-xs text-slate-500">
        <span>最后更新时间：{{ lastUpdatedLabel }}</span>
        <button type="button" class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60" :disabled="isRefreshing" @click.prevent="refreshData">
          <RefreshCw class="h-3.5 w-3.5" :class="isRefreshing ? 'animate-spin' : ''" /> {{ isRefreshing ? '更新中' : '点击更新' }}
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else-if="kpi">
      <div class="grid grid-cols-4 gap-4">
        <KpiCard label="总覆盖率" :value="`${kpi.coverage_rate}%`" change-kind="up-good" tooltip="总覆盖率 = 所选时间内至少发生一次 LLM 或 MCP 调用的用户数 ÷ 平台启用用户数。" />
        <KpiCard label="新增活跃" :value="kpi.new_active.toString()" unit="人" change-kind="up-good" tooltip="新增活跃 = 所选时间内活跃、但上一等长周期未活跃的用户数。" />
        <KpiCard label="日均使用频次" :value="kpi.daily_avg_frequency.toFixed(1)" unit="次/人" change-kind="neutral" tooltip="日均使用频次 = 所选时间内总调用次数 ÷ 活跃用户数 ÷ 天数。" />
        <KpiCard label="重度用户占比" :value="`${kpi.heavy_user_ratio}%`" change-kind="up-good" tooltip="重度用户占比 = 所选时间内日均调用达到重度阈值的用户数 ÷ 活跃用户数。" />
      </div>

      <GlassCard title="活跃用户趋势" tooltip="统计周期内每天有调用的独立用户数。">
        <VChart :option="activeTrendOption" class="h-56 w-full" autoresize />
      </GlassCard>

      <div class="grid grid-cols-2 gap-4">
        <GlassCard title="使用深度分布" tooltip="按用户在所选时间内的日均调用次数分档。日均调用 = 用户总调用次数 ÷ 天数。">
          <VChart :option="depthChartOption" class="h-48 w-full" autoresize />
        </GlassCard>
        <GlassCard title="重度用户占比趋势" tooltip="重度用户（日均>20次）占活跃用户的比例。持续增长表明 AI 正从尝鲜转向核心工作流。">
          <VChart :option="heavyTrendOption" class="h-48 w-full" autoresize />
        </GlassCard>
      </div>

      <GlassCard :title="`${dimensionText}覆盖明细`" padding="p-0" tooltip="受顶部时间和视角联动。覆盖率 = 活跃人数 ÷ 总人数；日均调用 = 总调用 ÷ 活跃人数 ÷ 天数。">
        <template #action>
          <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" :disabled="exportingKey === 'adoption_scope'" @click="exportCoverage">
            <Download class="h-3.5 w-3.5" /> 导出
          </button>
        </template>
        <div class="overflow-x-auto">
          <table class="min-w-[1040px] w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-left text-slate-500">
                <th class="cursor-pointer px-5 py-3 font-medium" @click="toggleDeptSort('name')">{{ dimensionText }}{{ deptSortIcon('name') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('total_members')">总人数{{ deptSortIcon('total_members') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('active_members')">活跃人数{{ deptSortIcon('active_members') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('coverage_rate')">覆盖率{{ deptSortIcon('coverage_rate') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('daily_avg_calls')">日均调用{{ deptSortIcon('daily_avg_calls') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('heavy_user_ratio')">重度用户占比{{ deptSortIcon('heavy_user_ratio') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('change')">环比{{ deptSortIcon('change') }}</th>
                <th class="px-5 py-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="row in sortedDeptTable" :key="`${dimension}-${row.id}`">
                <tr class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
                  <td class="px-5 py-3 font-medium text-slate-800">
                    <button class="inline-flex items-center gap-2 text-left hover:text-indigo-600" @click="toggleScopeUsers(row)">
                      <component :is="expandedScopeId === row.id ? ChevronUp : ChevronDown" class="h-3.5 w-3.5 text-slate-400" />
                      <span>{{ row.name }}</span>
                    </button>
                  </td>
                  <td class="px-3 py-3 text-right text-slate-600">{{ row.total_members }}</td>
                  <td class="px-3 py-3 text-right text-slate-600">{{ row.active_members }}</td>
                  <td class="px-3 py-3 text-right font-medium text-indigo-600">{{ row.coverage_rate }}%</td>
                  <td class="px-3 py-3 text-right text-slate-700">{{ row.daily_avg_calls.toFixed(1) }}</td>
                  <td class="px-3 py-3 text-right text-slate-700">{{ row.heavy_user_ratio }}%</td>
                  <td class="px-3 py-3 text-right" :class="row.change > 0 ? 'text-emerald-600' : row.change < 0 ? 'text-red-500' : 'text-slate-400'">
                    {{ row.change > 0 ? '+' : '' }}{{ row.change.toFixed(1) }}%
                  </td>
                  <td class="px-5 py-3 text-right">
                    <button class="rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" @click="toggleScopeUsers(row)">
                      人员明细
                    </button>
                  </td>
                </tr>
                <tr v-if="expandedScopeId === row.id" class="border-b border-slate-100">
                  <td colspan="8" class="bg-slate-50/70 px-5 py-4">
                    <div v-if="scopeUsersLoading" class="py-8 text-center text-sm text-slate-400">加载中...</div>
                    <div v-else class="max-h-[320px] overflow-auto rounded-lg border border-slate-100 bg-white">
                      <table class="min-w-[920px] w-full text-xs">
                        <thead>
                          <tr class="border-b border-slate-100 text-left text-slate-500">
                            <th class="px-4 py-2.5 font-medium">姓名</th>
                            <th class="px-3 py-2.5 font-medium">部门</th>
                            <th class="px-3 py-2.5 font-medium">职位</th>
                            <th class="px-3 py-2.5 font-medium text-right">总调用</th>
                            <th class="px-3 py-2.5 font-medium text-right">LLM 调用</th>
                            <th class="px-3 py-2.5 font-medium text-right">MCP 调用</th>
                            <th class="px-3 py-2.5 font-medium">最后活跃</th>
                            <th class="px-4 py-2.5 font-medium text-right">操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="user in scopeUsers" :key="user.id" class="border-b border-slate-50 last:border-0">
                            <td class="px-4 py-2.5 font-medium text-slate-800">{{ user.name || user.username }}</td>
                            <td class="px-3 py-2.5 text-slate-600">{{ user.department || '-' }}</td>
                            <td class="px-3 py-2.5 text-slate-500">{{ user.position || '-' }}</td>
                            <td class="px-3 py-2.5 text-right font-medium text-slate-800">{{ user.total_calls.toLocaleString() }}</td>
                            <td class="px-3 py-2.5 text-right text-slate-600">{{ user.llm_calls.toLocaleString() }}</td>
                            <td class="px-3 py-2.5 text-right text-slate-600">{{ user.mcp_calls.toLocaleString() }}</td>
                            <td class="px-3 py-2.5 text-slate-500">{{ user.last_active || '-' }}</td>
                            <td class="px-4 py-2.5 text-right">
                              <div class="inline-flex gap-1.5">
                                <button class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 hover:bg-slate-50" @click="openLogs('llm', { user_id: user.id })">LLM 日志</button>
                                <button class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 hover:bg-slate-50" @click="openLogs('mcp', { user_id: user.id })">MCP 日志</button>
                              </div>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                      <div v-if="scopeUsers.length === 0" class="py-8 text-center text-sm text-slate-400">暂无人员明细</div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
          <div v-if="sortedDeptTable.length === 0" class="py-10 text-center text-sm text-slate-400">暂无数据</div>
        </div>
      </GlassCard>

      <AdoptionResourceSections
        :agents="agents"
        :mcp-resources="mcpResources"
        :skill-resources="skillResources"
        :exporting-key="exportingKey"
        @open-logs="openLogs"
        @export-agents="exportAgents"
        @export-resources="exportResources"
      />

      <GlassCard padding="p-0">
        <div class="flex w-full items-center justify-between px-5 py-4 text-left">
          <button class="min-w-0 text-left" @click="unusedExpanded = !unusedExpanded">
            <span class="text-sm font-semibold text-slate-900">未使用用户</span>
            <span class="ml-2 text-xs text-slate-400">所选时间内无活跃记录</span>
            <span v-if="unusedUsers.length > 0" class="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
              {{ unusedUsers.length }}
            </span>
          </button>
          <div class="flex items-center gap-3">
            <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" @click="exportUnusedUsers">
              <Download class="h-3.5 w-3.5" /> 导出
            </button>
            <button class="rounded-md p-1 hover:bg-slate-100" @click="unusedExpanded = !unusedExpanded">
              <component :is="unusedExpanded ? ChevronUp : ChevronDown" class="h-4 w-4 text-slate-400" />
            </button>
          </div>
        </div>
        <div v-if="unusedExpanded" class="max-h-[420px] overflow-auto border-t border-slate-100">
          <table class="min-w-[760px] w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-left text-slate-500">
                <th class="px-5 py-3 font-medium">姓名</th>
                <th class="px-3 py-3 font-medium">部门</th>
                <th class="px-3 py-3 font-medium">职位</th>
                <th class="px-3 py-3 font-medium">已分配 Key</th>
                <th class="px-3 py-3 font-medium">最后活跃</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(u, i) in unusedUsers" :key="i" class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
                <td class="px-5 py-3 font-medium text-slate-800">{{ u.name }}</td>
                <td class="px-3 py-3 text-slate-600">{{ u.department }}</td>
                <td class="px-3 py-3 text-slate-600">{{ u.position }}</td>
                <td class="px-3 py-3 text-slate-500 font-mono text-[10px]">{{ u.assigned_key }}</td>
                <td class="px-3 py-3 text-slate-500">{{ u.last_active || '从未使用' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="unusedUsers.length === 0" class="py-8 text-center text-sm text-slate-400">所有用户均有活跃记录</div>
        </div>
      </GlassCard>
    </template>

    <div v-else class="py-20 text-center text-sm text-slate-400">加载失败，请刷新重试</div>
  </div>
</template>
