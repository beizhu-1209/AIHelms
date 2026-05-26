<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Download, ChevronDown, ChevronUp } from 'lucide-vue-next'
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
import PresetTabs from './components/PresetTabs.vue'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

interface AdoptionKpi {
  coverage_rate: number
  new_active: number
  daily_avg_frequency: number
  heavy_user_ratio: number
}

interface ActiveTrend {
  dates: string[]
  values: number[]
}

interface DepthDistribution {
  light: number
  medium: number
  heavy: number
}

interface HeavyTrend {
  dates: string[]
  ratios: number[]
}

interface DeptCoverageRow {
  name: string
  total_members: number
  active_members: number
  coverage_rate: number
  daily_avg_calls: number
  heavy_user_ratio: number
  change: number
}

interface AgentRow {
  rank: number
  name: string
  platform: string
  department: string
  user_count: number
  monthly_calls: number
  trend: number[]
}

interface ResourceRow {
  name: string
  type: string
  user_count: number
  monthly_calls: number
  department: string
}

interface UnusedUser {
  name: string
  department: string
  position: string
  assigned_key: string
  last_active: string
}

const timePreset = ref('month')
const dimension = ref<'department' | 'project'>('department')
const unusedExpanded = ref(false)

const isLoading = ref(true)
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

const TIME_PRESETS = [
  { key: 'month', label: '本月' },
  { key: '7d', label: '近7天' },
  { key: '30d', label: '近30天' },
]

async function loadData() {
  isLoading.value = true
  const params = { period: timePreset.value, dimension: dimension.value }
  try {
    const [adoptionData, agentData, mcpData, skillData, unusedData] = await Promise.all([
      request<{
        kpi: AdoptionKpi
        active_trend: ActiveTrend
        depth_distribution: DepthDistribution
        heavy_trend: HeavyTrend
        department_table: DeptCoverageRow[]
      }>('/api/v1/efficiency/adoption', { params }),
      request<AgentRow[]>('/api/v1/efficiency/adoption/agents', { params }),
      request<ResourceRow[]>('/api/v1/efficiency/adoption/resources', { params: { ...params, type: 'mcp' } }),
      request<ResourceRow[]>('/api/v1/efficiency/adoption/resources', { params: { ...params, type: 'skill' } }),
      request<UnusedUser[]>('/api/v1/efficiency/adoption/unused-users', { params }),
    ])
    kpi.value = adoptionData.kpi
    activeTrend.value = adoptionData.active_trend
    depthDist.value = adoptionData.depth_distribution
    heavyTrend.value = adoptionData.heavy_trend
    deptTable.value = adoptionData.department_table
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

function changeDimension(val: 'department' | 'project') {
  dimension.value = val
  loadData()
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
    <!-- ① Filter bar -->
    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-white/80 bg-white/60 px-4 py-2.5 shadow-sm backdrop-blur-xl">
      <span class="text-xs text-slate-500">时间</span>
      <PresetTabs :model-value="timePreset" :presets="TIME_PRESETS" @update:model-value="changePreset" />
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
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else-if="kpi">
      <!-- ② KPI cards -->
      <div class="grid grid-cols-4 gap-4">
        <KpiCard label="总覆盖率" :value="`${kpi.coverage_rate}%`" change-kind="up-good" />
        <KpiCard label="新增活跃" :value="kpi.new_active.toString()" unit="人" change-kind="up-good" />
        <KpiCard label="日均使用频次" :value="kpi.daily_avg_frequency.toFixed(1)" unit="次/人" change-kind="neutral" />
        <KpiCard label="重度用户占比" :value="`${kpi.heavy_user_ratio}%`" change-kind="up-good" />
      </div>

      <!-- ③ Active users trend -->
      <GlassCard title="活跃用户趋势" tooltip="统计周期内每天有调用的独立用户数。">
        <VChart :option="activeTrendOption" class="h-56 w-full" autoresize />
      </GlassCard>

      <!-- ④ Depth distribution + Heavy user trend -->
      <div class="grid grid-cols-2 gap-4">
        <GlassCard title="使用深度分布" subtitle="轻度(<5次/周) · 中度(5-20次) · 重度(>20次)" tooltip="按用户日均调用次数分档。日均=统计期总调用÷天数。">
          <VChart :option="depthChartOption" class="h-48 w-full" autoresize />
        </GlassCard>
        <GlassCard title="重度用户占比趋势" tooltip="重度用户（日均>20次）占活跃用户的比例。持续增长表明 AI 正从尝鲜转向核心工作流。">
          <VChart :option="heavyTrendOption" class="h-48 w-full" autoresize />
        </GlassCard>
      </div>

      <!-- ⑤ Department coverage table -->
      <GlassCard title="部门覆盖明细" padding="p-0" tooltip="部门维度的 AI 落地情况。日均调用=部门总调用÷活跃人数÷天数。">
        <template #action>
          <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">
            <Download class="h-3.5 w-3.5" /> 导出
          </button>
        </template>
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-left text-slate-500">
                <th class="cursor-pointer px-5 py-3 font-medium" @click="toggleDeptSort('name')">部门{{ deptSortIcon('name') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('total_members')">总人数{{ deptSortIcon('total_members') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('active_members')">活跃人数{{ deptSortIcon('active_members') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('coverage_rate')">覆盖率{{ deptSortIcon('coverage_rate') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('daily_avg_calls')">日均调用{{ deptSortIcon('daily_avg_calls') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('heavy_user_ratio')">重度用户占比{{ deptSortIcon('heavy_user_ratio') }}</th>
                <th class="cursor-pointer px-3 py-3 font-medium text-right" @click="toggleDeptSort('change')">环比{{ deptSortIcon('change') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in sortedDeptTable" :key="row.name" class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
                <td class="px-5 py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="px-3 py-3 text-right text-slate-600">{{ row.total_members }}</td>
                <td class="px-3 py-3 text-right text-slate-600">{{ row.active_members }}</td>
                <td class="px-3 py-3 text-right font-medium text-indigo-600">{{ row.coverage_rate }}%</td>
                <td class="px-3 py-3 text-right text-slate-700">{{ row.daily_avg_calls.toFixed(1) }}</td>
                <td class="px-3 py-3 text-right text-slate-700">{{ row.heavy_user_ratio }}%</td>
                <td class="px-3 py-3 text-right" :class="row.change > 0 ? 'text-emerald-600' : row.change < 0 ? 'text-red-500' : 'text-slate-400'">
                  {{ row.change > 0 ? '+' : '' }}{{ row.change.toFixed(1) }}%
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="sortedDeptTable.length === 0" class="py-10 text-center text-sm text-slate-400">暂无数据</div>
        </div>
      </GlassCard>

      <!-- ⑥ Agent heatmap table -->
      <GlassCard title="智能体热力表" subtitle="按月调用量排序" tooltip="基于智能体使用日志统计。用户数=独立使用人数，调用次数=会话数。">
        <template #action>
          <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">
            <Download class="h-3.5 w-3.5" /> 导出
          </button>
        </template>
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-left text-slate-500">
                <th class="px-5 py-3 font-medium">排名</th>
                <th class="px-3 py-3 font-medium">智能体</th>
                <th class="px-3 py-3 font-medium">平台</th>
                <th class="px-3 py-3 font-medium">归属部门</th>
                <th class="px-3 py-3 font-medium text-right">用户数</th>
                <th class="px-3 py-3 font-medium text-right">月调用</th>
                <th class="px-3 py-3 font-medium">趋势</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="agent in agents" :key="agent.rank" class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
                <td class="px-5 py-3">
                  <span
                    class="inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold"
                    :class="agent.rank <= 3 ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-500'"
                  >{{ agent.rank }}</span>
                </td>
                <td class="px-3 py-3 font-medium text-slate-800">{{ agent.name }}</td>
                <td class="px-3 py-3 text-slate-600">{{ agent.platform }}</td>
                <td class="px-3 py-3 text-slate-600">{{ agent.department }}</td>
                <td class="px-3 py-3 text-right text-slate-700">{{ agent.user_count }}</td>
                <td class="px-3 py-3 text-right font-medium text-slate-900">{{ agent.monthly_calls.toLocaleString() }}</td>
                <td class="px-3 py-3">
                  <svg v-if="agent.trend.length >= 2" width="48" height="16" viewBox="0 0 48 16" class="inline-block">
                    <path
                      :d="agent.trend.map((v, i) => `${i === 0 ? 'M' : 'L'}${(i / (agent.trend.length - 1)) * 48},${16 - (v / Math.max(...agent.trend)) * 16}`).join(' ')"
                      fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                    />
                  </svg>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="agents.length === 0" class="py-10 text-center text-sm text-slate-400">暂无数据</div>
        </div>
      </GlassCard>

      <!-- ⑦ MCP/Skill usage -->
      <!-- MCP 使用情况 -->
      <GlassCard title="MCP 使用情况" padding="p-0" tooltip="基于 MCP 调用日志统计。使用人数=有过调用的独立用户数。">
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-left text-slate-500">
                <th class="px-5 py-3 font-medium">MCP Server</th>
                <th class="px-3 py-3 font-medium text-right">使用人数</th>
                <th class="px-3 py-3 font-medium text-right">月调用</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in mcpResources" :key="i" class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
                <td class="px-5 py-3 font-medium text-slate-800">{{ r.name }}</td>
                <td class="px-3 py-3 text-right text-slate-700">{{ r.user_count }}</td>
                <td class="px-3 py-3 text-right font-medium text-slate-900">{{ r.monthly_calls.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="mcpResources.length === 0" class="py-8 text-center text-sm text-slate-400">暂无数据</div>
        </div>
      </GlassCard>

      <!-- Skill 使用情况 -->
      <GlassCard title="Skill 使用情况" padding="p-0" tooltip="基于 Skill 使用日志统计。安装=执行 install 的独立用户，下载=download 动作次数。">
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-left text-slate-500">
                <th class="px-5 py-3 font-medium">Skill</th>
                <th class="px-3 py-3 font-medium text-right">安装人数</th>
                <th class="px-3 py-3 font-medium text-right">月下载</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in skillResources" :key="i" class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
                <td class="px-5 py-3 font-medium text-slate-800">{{ r.name }}</td>
                <td class="px-3 py-3 text-right text-slate-700">{{ r.user_count }}</td>
                <td class="px-3 py-3 text-right font-medium text-slate-900">{{ r.monthly_calls.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="skillResources.length === 0" class="py-8 text-center text-sm text-slate-400">暂无数据</div>
        </div>
      </GlassCard>

      <!-- ⑧ Unused users (collapsible) -->
      <GlassCard padding="p-0">
        <button
          class="flex w-full items-center justify-between px-5 py-4 text-left"
          @click="unusedExpanded = !unusedExpanded"
        >
          <div>
            <span class="text-sm font-semibold text-slate-900">未使用用户</span>
            <span class="ml-2 text-xs text-slate-400">已分配 Key 但无活跃记录</span>
            <span v-if="unusedUsers.length > 0" class="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
              {{ unusedUsers.length }}
            </span>
          </div>
          <component :is="unusedExpanded ? ChevronUp : ChevronDown" class="h-4 w-4 text-slate-400" />
        </button>
        <div v-if="unusedExpanded" class="border-t border-slate-100">
          <table class="w-full text-xs">
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
