<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Download, RefreshCw } from 'lucide-vue-next'
import { createExportTask, getEfficiencyHealth, toast } from '@aihelms/shared'
import TooltipIcon from '../../components/TooltipIcon.vue'
import ExportTaskNotice from '../../components/ExportTaskNotice.vue'
import GlassCard from './components/GlassCard.vue'
import { submitEfficiencyRefresh, keepRefreshIndicator } from './utils'

interface HealthCard {
  key: string
  label: string
  healthy: number
  total: number
  state: 'healthy' | 'warning' | 'danger' | 'unknown'
  description: string
}

interface McpHealthRow {
  id: number
  name: string
  server_name: string
  status: string
  last_check: string | null
  error: string
  is_published: boolean
  tool_count: number
}

interface ModelHealthRow {
  id: number
  name: string
  model_id: string
  category: string
  is_published: boolean
  active_deployments: number
  total_deployments: number
  status: 'healthy' | 'warning' | 'danger' | 'unknown'
  last_update: string | null
}

interface DockerItem {
  name: string
  status: 'healthy' | 'warning' | 'danger' | 'unknown'
  value: string
}

interface DataUpdate {
  last_updated_at: string | null
  latest_summary_date: string | null
  minutes_since_update: number | null
  state: 'healthy' | 'warning' | 'danger' | 'unknown'
}

interface HealthData {
  cards: HealthCard[]
  mcp_servers: McpHealthRow[]
  models: ModelHealthRow[]
  docker: DockerItem[]
  data_update: DataUpdate
  freshness?: { last_updated_at: string | null; last_updated_label: string }
}

const isLoading = ref(true)
const isRefreshing = ref(false)
const exporting = ref(false)
const exportNotice = ref('')
const data = ref<HealthData | null>(null)
const lastUpdatedAt = ref<Date | null>(null)
const lastUpdatedLabel = ref('--')
const activeTab = ref<'mcp' | 'model' | 'docker'>('mcp')

async function refreshData() {
  isRefreshing.value = true
  let queued = false
  try {
    await submitEfficiencyRefresh('health')
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
  try {
    data.value = await getEfficiencyHealth<HealthData & { freshness?: { last_updated_at: string | null; last_updated_label: string } }>()
    lastUpdatedAt.value = data.value.freshness?.last_updated_at ? new Date(data.value.freshness.last_updated_at) : new Date()
    lastUpdatedLabel.value = data.value.freshness?.last_updated_label || formatLastUpdated()
  } finally {
    isLoading.value = false
  }
}

function stateClass(state: string): string {
  if (state === 'healthy') return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  if (state === 'warning') return 'bg-amber-50 text-amber-700 border-amber-200'
  if (state === 'danger') return 'bg-red-50 text-red-700 border-red-200'
  return 'bg-slate-50 text-slate-600 border-slate-200'
}

function stateLabel(state: string): string {
  if (state === 'healthy') return '正常'
  if (state === 'warning') return '需关注'
  if (state === 'danger') return '异常'
  return '未知'
}

function mcpStatusLabel(status: string): string {
  if (['healthy', 'success', 'online', 'ok'].includes(status)) return '正常'
  if (status === 'unhealthy') return '异常'
  return status || '未知'
}

function formatDateTime(value: string | null): string {
  if (!value) return '--'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatLastUpdated(): string {
  if (!lastUpdatedAt.value) return '--'
  const diffMinutes = Math.floor((Date.now() - lastUpdatedAt.value.getTime()) / 60000)
  if (diffMinutes < 1) return '刚刚'
  if (diffMinutes < 60) return `${diffMinutes}分钟前`
  return formatDateTime(lastUpdatedAt.value.toISOString())
}

function formatDataUpdate(): string {
  const minutes = data.value?.data_update.minutes_since_update
  if (minutes === null || minutes === undefined) return '--'
  if (minutes < 60) return `${minutes}分钟前`
  return formatDateTime(data.value?.data_update.last_updated_at ?? null)
}

async function exportActive() {
  exporting.value = true
  try {
    await createExportTask({
      source: 'efficiency',
      export_type: `health_${activeTab.value}`,
      task_name: `AI健康-${activeTab.value}`,
      params: {},
    })
    exportNotice.value = '导出任务已创建，请到资源审计 > 导出任务下载表格'
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建导出任务失败')
  } finally {
    exporting.value = false
  }
}


const cards = computed(() => data.value?.cards ?? [])

onMounted(loadData)
</script>

<template>
  <div class="space-y-4">
    <ExportTaskNotice v-if="exportNotice" />
    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-sm font-semibold text-slate-900">AI健康</span>
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

    <template v-else-if="data">
      <div class="grid grid-cols-4 gap-4">
        <div v-for="card in cards" :key="card.key" class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div class="flex items-center justify-between">
            <span class="text-xs text-slate-500">{{ card.label }}</span>
            <span class="rounded-full border px-2 py-0.5 text-xs" :class="stateClass(card.state)">{{ stateLabel(card.state) }}</span>
          </div>
          <div class="mt-2 flex items-baseline gap-1">
            <span class="text-2xl font-semibold text-slate-900">{{ card.healthy }}</span>
            <span class="text-sm text-slate-400">/ {{ card.total }}</span>
          </div>
          <div class="mt-1 text-xs text-slate-500">{{ card.description }}</div>
        </div>
      </div>

      <GlassCard>
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-1">
            <span class="text-sm font-semibold text-slate-900">健康明细</span>
            <TooltipIcon text="MCP状态来自MCP管理中的健康检查结果；模型状态按是否存在启用部署判断；Docker环境为运行环境检测。" />
          </div>
          <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" @click="exportActive">
            <Download class="h-3.5 w-3.5" /> 导出
          </button>
        </div>

        <div class="mb-3 flex gap-1 rounded-lg bg-slate-100 p-1">
          <button class="rounded-md px-3 py-1.5 text-xs transition-colors" :class="activeTab === 'mcp' ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'" @click="activeTab = 'mcp'">MCP上游</button>
          <button class="rounded-md px-3 py-1.5 text-xs transition-colors" :class="activeTab === 'model' ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'" @click="activeTab = 'model'">模型</button>
          <button class="rounded-md px-3 py-1.5 text-xs transition-colors" :class="activeTab === 'docker' ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'" @click="activeTab = 'docker'">Docker环境</button>
        </div>

        <div class="max-h-[520px] overflow-auto">
          <table v-if="activeTab === 'mcp'" class="min-w-[980px] w-full text-sm">
            <thead class="sticky top-0 z-10 bg-white"><tr class="border-b border-slate-200 text-left text-xs text-slate-400">
              <th class="py-2.5 font-medium">MCP名称</th><th class="py-2.5 font-medium">Server Name</th><th class="py-2.5 text-right font-medium">工具数</th><th class="py-2.5 font-medium">发布</th><th class="py-2.5 font-medium">状态</th><th class="py-2.5 font-medium">最后检查</th><th class="py-2.5 font-medium">错误信息</th>
            </tr></thead>
            <tbody>
              <tr v-for="row in data.mcp_servers" :key="row.id" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="py-3 text-slate-600">{{ row.server_name }}</td>
                <td class="py-3 text-right text-slate-700">{{ row.tool_count }}</td>
                <td class="py-3 text-slate-600">{{ row.is_published ? '是' : '否' }}</td>
                <td class="py-3"><span class="rounded-full border px-2 py-0.5 text-xs" :class="stateClass(['healthy', 'success', 'online', 'ok'].includes(row.status) ? 'healthy' : row.status === 'unhealthy' ? 'danger' : 'unknown')">{{ mcpStatusLabel(row.status) }}</span></td>
                <td class="py-3 text-slate-600">{{ formatDateTime(row.last_check) }}</td>
                <td class="py-3 text-slate-500">{{ row.error || '--' }}</td>
              </tr>
              <tr v-if="data.mcp_servers.length === 0"><td colspan="7" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
            </tbody>
          </table>

          <table v-else-if="activeTab === 'model'" class="min-w-[900px] w-full text-sm">
            <thead class="sticky top-0 z-10 bg-white"><tr class="border-b border-slate-200 text-left text-xs text-slate-400">
              <th class="py-2.5 font-medium">模型</th><th class="py-2.5 font-medium">模型ID</th><th class="py-2.5 font-medium">类型</th><th class="py-2.5 font-medium">发布</th><th class="py-2.5 text-right font-medium">启用部署</th><th class="py-2.5 text-right font-medium">部署总数</th><th class="py-2.5 font-medium">状态</th><th class="py-2.5 font-medium">更新时间</th>
            </tr></thead>
            <tbody>
              <tr v-for="row in data.models" :key="row.id" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="py-3 text-slate-600">{{ row.model_id || '--' }}</td>
                <td class="py-3 text-slate-600">{{ row.category }}</td>
                <td class="py-3 text-slate-600">{{ row.is_published ? '是' : '否' }}</td>
                <td class="py-3 text-right text-slate-700">{{ row.active_deployments }}</td>
                <td class="py-3 text-right text-slate-700">{{ row.total_deployments }}</td>
                <td class="py-3"><span class="rounded-full border px-2 py-0.5 text-xs" :class="stateClass(row.status)">{{ stateLabel(row.status) }}</span></td>
                <td class="py-3 text-slate-600">{{ formatDateTime(row.last_update) }}</td>
              </tr>
              <tr v-if="data.models.length === 0"><td colspan="8" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
            </tbody>
          </table>

          <table v-else class="min-w-[640px] w-full text-sm">
            <thead class="sticky top-0 z-10 bg-white"><tr class="border-b border-slate-200 text-left text-xs text-slate-400">
              <th class="py-2.5 font-medium">检查项</th><th class="py-2.5 font-medium">状态</th><th class="py-2.5 font-medium">结果</th>
            </tr></thead>
            <tbody>
              <tr v-for="row in data.docker" :key="row.name" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                <td class="py-3 font-medium text-slate-800">{{ row.name }}</td>
                <td class="py-3"><span class="rounded-full border px-2 py-0.5 text-xs" :class="stateClass(row.status)">{{ stateLabel(row.status) }}</span></td>
                <td class="py-3 text-slate-600">{{ row.value }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassCard>

      <div class="rounded-xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
        <div class="flex items-center gap-2">
          <span class="font-medium text-slate-900">效能数据更新时间</span>
          <span class="rounded-full border px-2 py-0.5 text-xs" :class="stateClass(data.data_update.state)">{{ stateLabel(data.data_update.state) }}</span>
        </div>
        <div class="mt-2 grid grid-cols-3 gap-4 text-xs text-slate-600">
          <div><span class="text-slate-400">最后更新时间</span><div class="mt-1 text-sm text-slate-900">{{ formatDataUpdate() }}</div></div>
          <div><span class="text-slate-400">最新数据日期</span><div class="mt-1 text-sm text-slate-900">{{ data.data_update.latest_summary_date || '--' }}</div></div>
          <div><span class="text-slate-400">更新时间</span><div class="mt-1 text-sm text-slate-900">{{ formatDateTime(data.data_update.last_updated_at) }}</div></div>
        </div>
      </div>
    </template>
  </div>
</template>
