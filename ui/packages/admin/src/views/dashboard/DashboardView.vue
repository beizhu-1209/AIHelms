<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BarChart3,
  Bot,
  Brain,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  DollarSign,
  FileText,
  FolderTree,
  GitBranch,
  Key,
  Package,
  Plug,
  RefreshCw,
  Server,
  ShieldCheck,
  UserCheck,
  Users,
  Zap,
} from 'lucide-vue-next'
import { getDashboard, refreshDashboard, toast } from '@aihelms/shared'
import { keepRefreshIndicator } from '../efficiency/utils'
import TooltipIcon from '../../components/TooltipIcon.vue'
import type { DashboardData, PendingItem, ResourceSummary, ServiceStatusItem } from '@aihelms/shared'

const router = useRouter()
const isLoading = ref(true)
const isRefreshing = ref(false)
const data = ref<DashboardData | null>(null)
const period = ref('month')
const customStart = ref('')
const customEnd = ref('')

const periodOptions = [
  { value: 'today', label: '今日' },
  { value: '7d', label: '近7天' },
  { value: 'month', label: '本月' },
  { value: '30d', label: '近30天' },
  { value: 'last_month', label: '上月' },
]



const quickActions = [
  { label: '处理审批', desc: '资源申请待处理', icon: ClipboardCheck, path: '/resource-approval?status=pending' },
  { label: '查看日志', desc: '调用与使用记录', icon: FileText, path: '/logs' },
  { label: 'AI Key管理', desc: '额度、归属、资源范围', icon: Key, path: '/ai-keys' },
  { label: '审计日志', desc: '管理员操作记录', icon: ShieldCheck, path: '/audit' },
  { label: '模型管理', desc: '模型与部署维护', icon: Brain, path: '/models' },
  { label: 'MCP管理', desc: '上游服务与工具', icon: Plug, path: '/mcp' },
]

const RESOURCE_ICONS: Record<string, typeof Package> = {
  model: Package,
  mcp: Plug,
  skill: Zap,
  agent: Brain,
  ai_key: Key,
  user: UserCheck,
  department: FolderTree,
  project: GitBranch,
}

const SERVICE_ICONS: Record<string, typeof Package> = {
  mcp: Plug,
  model: Brain,
  docker: Server,
  efficiency: Clock3,
}

const periodLabel = computed(() => {
  if (period.value === 'custom') return `${customStart.value || '-'} 至 ${customEnd.value || '-'}`
  return periodOptions.find((item) => item.value === period.value)?.label || '本月'
})

const maxTrendRequests = computed(() => {
  const trend = data.value?.requestTrend || []
  return Math.max(...trend.map((point) => point.requests), 1)
})

const trendTicks = computed(() => {
  const max = maxTrendRequests.value
  return [max, Math.round(max * 0.75), Math.round(max * 0.5), Math.round(max * 0.25), 0]
})

const trendBars = computed(() => {
  const heights = ['h-4', 'h-6', 'h-8', 'h-10', 'h-12', 'h-14', 'h-16', 'h-20', 'h-24', 'h-28', 'h-32', 'h-36']
  return (data.value?.requestTrend || []).map((point) => {
    const ratio = point.requests / maxTrendRequests.value
    const index = Math.min(heights.length - 1, Math.max(0, Math.ceil(ratio * (heights.length - 1))))
    return { ...point, heightClass: point.requests > 0 ? heights[index] : 'h-1' }
  })
})

function getQueryParams() {
  const params: { period?: string; start_date?: string; end_date?: string } = {}
  if (period.value === 'custom') {
    params.start_date = customStart.value
    params.end_date = customEnd.value
  } else {
    params.period = period.value
  }
  return params
}


async function loadData() {
  isLoading.value = true
  try {
    data.value = await getDashboard(getQueryParams())
  } finally {
    isLoading.value = false
  }
}

async function handleRefresh() {
  isRefreshing.value = true
  let queued = false
  try {
    const refresh = await refreshDashboard()
    if (refresh.status === 'unavailable' || !(refresh.taskId || refresh.task_id)) {
      throw new Error(refresh.reason || '刷新任务提交失败')
    }
    queued = true
    toast.info('数据更新中，请稍后刷新页面查看', 8000)
  } catch (e) {
    toast.error((e as { message?: string }).message || '刷新失败')
  } finally {
    if (queued) await keepRefreshIndicator()
    isRefreshing.value = false
  }
}

function changePeriod(value: string) {
  period.value = value
  loadData()
}


function applyCustomRange() {
  if (!customStart.value || !customEnd.value) {
    toast.error('请选择完整的开始和结束日期')
    return
  }
  period.value = 'custom'
  loadData()
}

function handleNavigate(path: string) {
  router.push(path)
}

function getResourceIcon(item: ResourceSummary) {
  return RESOURCE_ICONS[item.icon] || Package
}

function getServiceIcon(item: ServiceStatusItem) {
  return SERVICE_ICONS[item.key] || Server
}

function serviceStateClass(state: ServiceStatusItem['state']) {
  if (state === 'healthy') return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  if (state === 'danger') return 'border-red-200 bg-red-50 text-red-700'
  if (state === 'warning') return 'border-amber-200 bg-amber-50 text-amber-700'
  return 'border-slate-200 bg-slate-50 text-slate-500'
}

function approvalTitle(item: PendingItem) {
  return `${item.applicant || '未知用户'} 申请 ${item.resourceTypeLabel || item.resourceType || '资源'}`
}

function formatMoney(value: number) {
  return `¥${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

function formatNumber(value: number) {
  return value.toLocaleString()
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-5">
    <div class="overflow-hidden rounded-xl border border-slate-200/70 bg-white/80 shadow-sm backdrop-blur-xl">
      <div class="border-b border-slate-200/70 px-5 py-4">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Dashboard</h1>
          </div>
          <div class="flex flex-col items-end gap-2 text-xs text-slate-500">
            <span v-if="data" class="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1">最后更新时间：{{ data.lastUpdatedLabel }}</span>
            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded-md bg-purple-600 px-3 py-1.5 font-medium text-white shadow-sm hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isRefreshing"
              @click.prevent="handleRefresh"
            >
              <RefreshCw class="h-3.5 w-3.5" :class="isRefreshing ? 'animate-spin' : ''" />
              {{ isRefreshing ? '更新中' : '点击更新' }}
            </button>
          </div>
        </div>
      </div>

      <div class="space-y-4 bg-slate-50/70 px-5 py-4">
        <div class="flex flex-wrap items-center gap-3">
          <div class="inline-flex rounded-lg bg-white p-1 shadow-sm ring-1 ring-slate-200">
            <button
              v-for="item in periodOptions"
              :key="item.value"
              class="rounded-md px-3 py-1.5 text-xs font-medium transition"
              :class="period === item.value ? 'bg-purple-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'"
              @click="changePeriod(item.value)"
            >
              {{ item.label }}
            </button>
          </div>
          <div class="flex items-center gap-1.5 text-xs text-slate-500">
            <input v-model="customStart" type="date" class="rounded-md border border-slate-200 bg-white px-2 py-1.5 focus:border-purple-500 focus:outline-none" />
            <span>至</span>
            <input v-model="customEnd" type="date" class="rounded-md border border-slate-200 bg-white px-2 py-1.5 focus:border-purple-500 focus:outline-none" />
            <button class="rounded-md border border-slate-200 bg-white px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-100" @click="applyCustomRange">查询</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-purple-500 border-t-transparent"></div>
    </div>

    <template v-else-if="data">
      <div class="grid grid-cols-4 gap-4">
        <button class="group rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md" @click="handleNavigate('/efficiency')">
          <div class="flex items-center justify-between">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50"><Users class="h-5 w-5 text-blue-600" /></div>
            <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-500">{{ periodLabel }}</span>
          </div>
          <div class="mt-4 text-2xl font-semibold text-slate-950">{{ formatNumber(data.status.activeUsers) }}<span class="ml-1 text-sm font-normal text-slate-500">人</span></div>
          <div class="mt-1 flex items-center gap-1 text-xs text-slate-500">活跃用户 <TooltipIcon text="所选时间内至少发生过一次 LLM 或 MCP 调用的去重用户数。" :focusable="false" width-class="w-72" /></div>
          <div class="mt-3 text-xs" :class="data.status.activeUsersChange >= 0 ? 'text-emerald-600' : 'text-red-500'">较上一周期 {{ data.status.activeUsersChange >= 0 ? '+' : '' }}{{ data.status.activeUsersChange }}</div>
        </button>

        <button class="group rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md" @click="handleNavigate('/logs')">
          <div class="flex items-center justify-between">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50"><Activity class="h-5 w-5 text-indigo-600" /></div>
            <BarChart3 class="h-4 w-4 text-slate-300 group-hover:text-indigo-500" />
          </div>
          <div class="mt-4 text-2xl font-semibold text-slate-950">{{ formatNumber(data.status.totalRequests) }}<span class="ml-1 text-sm font-normal text-slate-500">次</span></div>
          <div class="mt-1 flex items-center gap-1 text-xs text-slate-500">调用次数 <TooltipIcon text="所选时间内 LLM 调用次数 + MCP 工具调用次数，不包含 Skill 下载/安装。" :focusable="false" width-class="w-72" /></div>
          <div class="mt-3 text-xs text-slate-400">LLM {{ formatNumber(data.status.llmRequests) }} / MCP {{ formatNumber(data.status.mcpRequests) }}</div>
        </button>

        <button class="group rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-amber-200 hover:shadow-md" @click="handleNavigate('/efficiency/cost')">
          <div class="flex items-center justify-between">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50"><DollarSign class="h-5 w-5 text-amber-600" /></div>
            <span class="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700">成本</span>
          </div>
          <div class="mt-4 text-2xl font-semibold text-slate-950">{{ formatMoney(data.status.internalCost) }}</div>
          <div class="mt-1 flex items-center gap-1 text-xs text-slate-500">平台成本 <TooltipIcon text="所选时间内 AIHelms 平台日志计算出的内部计费成本。" :focusable="false" width-class="w-72" /></div>
          <div class="mt-3 text-xs text-slate-400">外部 {{ formatMoney(data.status.externalCost) }} / 差额 {{ formatMoney(data.status.costDiff) }}</div>
        </button>

        <button class="group rounded-xl border bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md" :class="data.status.pendingCount > 0 ? 'border-red-200 hover:border-red-300' : 'border-slate-200 hover:border-emerald-200'" @click="handleNavigate('/resource-approval?status=pending')">
          <div class="flex items-center justify-between">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg" :class="data.status.pendingCount > 0 ? 'bg-red-50' : 'bg-emerald-50'">
              <AlertCircle v-if="data.status.pendingCount > 0" class="h-5 w-5 text-red-600" />
              <CheckCircle2 v-else class="h-5 w-5 text-emerald-600" />
            </div>
            <span class="rounded-md px-2 py-1 text-xs font-medium" :class="data.status.pendingCount > 0 ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">审批</span>
          </div>
          <div class="mt-4 text-2xl font-semibold" :class="data.status.pendingCount > 0 ? 'text-red-700' : 'text-slate-950'">{{ data.status.pendingCount }}<span class="ml-1 text-sm font-normal text-slate-500">件</span></div>
          <div class="mt-1 flex items-center gap-1 text-xs text-slate-500">待审批申请 <TooltipIcon text="只统计资源使用申请中待审批状态的资源使用申请，管理员点击后进入审批管理处理。" :focusable="false" width-class="w-72" /></div>
          <div class="mt-3 text-xs text-slate-400">点击进入资源审批</div>
        </button>
      </div>

      <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-slate-900">资源概览</h3>
          <Package class="h-4 w-4 text-slate-400" />
        </div>
        <div class="grid grid-cols-8 gap-3">
          <button v-for="resource in data.resources" :key="resource.name" class="rounded-lg border border-slate-100 bg-slate-50 px-3 py-3 text-left transition hover:border-purple-200 hover:bg-purple-50" @click="handleNavigate(resource.linkPath)">
            <div class="mb-3 flex items-center justify-between">
              <component :is="getResourceIcon(resource)" class="h-4 w-4 text-slate-500" />
              <ArrowRight class="h-3.5 w-3.5 text-slate-300" />
            </div>
            <div class="truncate text-xs text-slate-500">{{ resource.name }}</div>
            <div class="mt-1 text-lg font-semibold text-slate-900">{{ resource.total }}</div>
            <div class="mt-0.5 truncate text-xs text-slate-400">
              <template v-if="resource.active !== null">{{ resource.active }} {{ resource.activeLabel }}</template>
              <template v-else>总数</template>
            </div>
          </button>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-slate-900">快捷操作</h3>
            <Bot class="h-4 w-4 text-slate-400" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <button v-for="action in quickActions" :key="action.label" class="flex items-center gap-3 rounded-lg border border-slate-100 bg-white px-3 py-3 text-left hover:border-purple-200 hover:bg-purple-50" @click="handleNavigate(action.path)">
              <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                <component :is="action.icon" class="h-4 w-4" />
              </div>
              <div class="min-w-0">
                <div class="truncate text-sm font-medium text-slate-800">{{ action.label }}</div>
                <div class="mt-0.5 truncate text-xs text-slate-400">{{ action.desc }}</div>
              </div>
            </button>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-slate-900">服务状态</h3>
            <ShieldCheck class="h-4 w-4 text-slate-400" />
          </div>
          <div class="space-y-3">
            <button v-for="item in data.serviceStatus" :key="item.key" class="flex w-full items-center justify-between rounded-lg border px-4 py-3 text-left" :class="serviceStateClass(item.state)" @click="item.key === 'mcp' ? handleNavigate('/mcp') : item.key === 'model' ? handleNavigate('/models') : undefined">
              <span class="flex items-center gap-3">
                <span class="flex h-8 w-8 items-center justify-center rounded-md bg-white/70"><component :is="getServiceIcon(item)" class="h-4 w-4" /></span>
                <span>
                  <span class="block text-sm font-medium">{{ item.label }}</span>
                  <span class="block text-xs opacity-80">{{ item.description }}</span>
                </span>
              </span>
              <span class="text-sm font-semibold">{{ item.healthy }}/{{ item.total }}</span>
            </button>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-5 gap-4">
        <div class="col-span-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-4 flex items-start justify-between">
            <h3 class="flex items-center gap-1 text-sm font-semibold text-slate-900">调用趋势 <TooltipIcon text="X 轴展示所选时间范围内的小时或日期；Y 轴展示调用次数，单位为次。" width-class="w-72" /></h3>
            <div class="text-right text-xs text-slate-400">
              <div>X轴：{{ period === 'today' ? '小时' : '日期' }}</div>
              <div>Y轴：调用次数（次）</div>
            </div>
          </div>
          <div class="grid grid-cols-[3rem_1fr] gap-3">
            <div class="flex h-44 flex-col justify-between text-right text-[10px] text-slate-400">
              <span v-for="tick in trendTicks" :key="tick">{{ formatNumber(tick) }}</span>
            </div>
            <div class="border-l border-b border-slate-200 pl-3 pb-4">
              <div class="flex h-40 items-end gap-1.5">
                <div v-for="point in trendBars" :key="point.label" class="group relative flex flex-1 flex-col items-center justify-end">
                  <div class="w-full rounded-t bg-indigo-400 transition group-hover:bg-indigo-500" :class="point.heightClass"></div>
                  <div class="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-slate-900 px-2 py-1 text-xs text-white opacity-0 shadow transition group-hover:opacity-100">{{ point.label }}：{{ formatNumber(point.requests) }}次</div>
                </div>
              </div>
              <div class="mt-2 flex justify-between text-[10px] text-slate-400">
                <span>{{ data.requestTrend[0]?.label }}</span>
                <span>{{ data.requestTrend[Math.floor(data.requestTrend.length / 2)]?.label }}</span>
                <span>{{ data.requestTrend[data.requestTrend.length - 1]?.label }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="col-span-2 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-slate-900">最新待审批</h3>
            <button class="text-xs font-medium text-purple-600 hover:text-purple-700" @click="handleNavigate('/resource-approval?status=pending')">查看全部</button>
          </div>
          <div v-if="data.pendingApprovalsList.length === 0" class="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 py-8 text-sm text-slate-500">
            <CheckCircle2 class="mb-2 h-7 w-7 text-emerald-500" />
            暂无待审批申请
          </div>
          <div v-else class="overflow-hidden rounded-lg border border-slate-100">
            <table class="w-full text-xs">
              <thead class="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th class="px-3 py-2 font-medium">申请人</th>
                  <th class="px-3 py-2 font-medium">申请资源</th>
                  <th class="px-3 py-2 font-medium">类型</th>
                  <th class="px-3 py-2 font-medium">时间</th>
                  <th class="px-3 py-2 font-medium text-right">动作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in data.pendingApprovalsList" :key="item.id || item.createdAt || item.resourceName" class="border-t border-slate-100 hover:bg-slate-50">
                  <td class="px-3 py-2 text-slate-700">{{ item.applicant || '未知用户' }}</td>
                  <td class="max-w-[8rem] truncate px-3 py-2 text-slate-700" :title="item.resourceName || item.reason">{{ item.resourceName || item.reason || '-' }}</td>
                  <td class="px-3 py-2 text-slate-500">{{ item.resourceTypeLabel || item.resourceType || '-' }}</td>
                  <td class="px-3 py-2 text-slate-500">{{ item.timeAgo }}</td>
                  <td class="px-3 py-2 text-right"><button class="font-medium text-purple-600 hover:text-purple-700" @click="handleNavigate(item.linkUrl)">处理</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
