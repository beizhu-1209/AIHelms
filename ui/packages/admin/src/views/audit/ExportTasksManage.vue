<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Download, RefreshCw, RotateCcw, Trash2, XCircle } from 'lucide-vue-next'
import {
  cancelExportTask,
  cleanupExportTasks,
  downloadExportTask,
  getExportTasks,
  retryExportTask,
  toast,
  type ExportOptionItem,
  type ExportTask,
} from '@aihelms/shared'
import Pagination from '../../components/Pagination.vue'

const loading = ref(false)
const downloadingIds = ref<Set<number>>(new Set())
const operatingId = ref<number | null>(null)
const cleaning = ref(false)
const items = ref<ExportTask[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const retentionDays = ref(7)
const sources = ref<ExportOptionItem[]>([])
const statuses = ref<ExportOptionItem[]>([])
const filterSource = ref('')
const filterStatus = ref('')
const lastUpdatedAt = ref<Date | null>(null)
let refreshTimer: number | null = null

async function loadData(silent = false) {
  if (!silent) loading.value = true
  try {
    const res = await getExportTasks({
      page: page.value,
      page_size: pageSize.value,
      source: filterSource.value || undefined,
      status: filterStatus.value || undefined,
    })
    items.value = res.items
    total.value = res.total
    sources.value = res.sources
    statuses.value = res.statuses
    retentionDays.value = res.retention_days || 7
    lastUpdatedAt.value = new Date()
  } finally {
    if (!silent) loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadData()
}

function handleReset() {
  filterSource.value = ''
  filterStatus.value = ''
  page.value = 1
  loadData()
}

function handlePageChange(newPage: number) {
  page.value = newPage
  loadData()
}

function isDownloading(taskId: number): boolean {
  return downloadingIds.value.has(taskId)
}

function setDownloading(taskId: number, downloading: boolean) {
  const next = new Set(downloadingIds.value)
  if (downloading) next.add(taskId)
  else next.delete(taskId)
  downloadingIds.value = next
}

async function handleDownload(task: ExportTask) {
  if (isDownloading(task.id)) return
  setDownloading(task.id, true)
  try {
    await downloadExportTask(task)
  } catch (e) {
    toast.error((e as { message?: string }).message || '下载失败')
  } finally {
    setDownloading(task.id, false)
  }
}

async function handleCancel(task: ExportTask) {
  if (!window.confirm(`确认取消导出任务「${task.task_name}」？`)) return
  operatingId.value = task.id
  try {
    await cancelExportTask(task.id)
    toast.success('导出任务已取消')
    await loadData(true)
  } catch (e) {
    toast.error((e as { message?: string }).message || '取消失败')
  } finally {
    operatingId.value = null
  }
}

async function handleRetry(task: ExportTask) {
  operatingId.value = task.id
  try {
    await retryExportTask(task.id)
    toast.success('导出任务已重新提交')
    page.value = 1
    await loadData(true)
  } catch (e) {
    toast.error((e as { message?: string }).message || '重试失败')
  } finally {
    operatingId.value = null
  }
}

async function handleCleanup() {
  if (!window.confirm(`确认清理 ${retentionDays.value} 天前已结束的导出任务？`)) return
  cleaning.value = true
  try {
    const res = await cleanupExportTasks(retentionDays.value)
    toast.success(`已清理 ${res.deleted_tasks} 个任务`)
    page.value = 1
    await loadData(true)
  } catch (e) {
    toast.error((e as { message?: string }).message || '清理失败')
  } finally {
    cleaning.value = false
  }
}

function statusLabel(status: string): string {
  return statuses.value.find((item) => item.key === status)?.label || status || '--'
}

function sourceLabel(source: string): string {
  return sources.value.find((item) => item.key === source)?.label || source || '--'
}

function statusClass(status: string): string {
  if (status === 'success') return 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100'
  if (status === 'failed') return 'bg-red-50 text-red-700 ring-1 ring-red-100'
  if (status === 'running') return 'bg-blue-50 text-blue-700 ring-1 ring-blue-100'
  if (status === 'pending') return 'bg-amber-50 text-amber-700 ring-1 ring-amber-100'
  if (status === 'canceled') return 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'
  return 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'
}

function formatTime(value: string | null): string {
  if (!value) return '--'
  return value.replace('T', ' ').slice(0, 19)
}

function formatSize(value: number | null): string {
  if (!value) return '--'
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(2)} MB`
  if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${value} B`
}

const hasProcessingTasks = computed(() => items.value.some((task) => ['pending', 'running'].includes(task.status)))

const lastUpdatedLabel = computed(() => {
  if (!lastUpdatedAt.value) return '--'
  const diffMinutes = Math.floor((Date.now() - lastUpdatedAt.value.getTime()) / 60000)
  if (diffMinutes < 1) return '刚刚'
  if (diffMinutes < 60) return `${diffMinutes}分钟前`
  return formatTime(lastUpdatedAt.value.toISOString()).slice(5, 16)
})

onMounted(() => {
  loadData()
  refreshTimer = window.setInterval(() => {
    if (hasProcessingTasks.value) loadData(true)
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
})
</script>

<template>
  <div>
    <div class="mb-6 flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">导出任务</h1>
      </div>
      <div class="flex items-center gap-2 text-xs text-slate-500">
        <span>最后更新时间：{{ lastUpdatedLabel }}</span>
        <button class="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50" @click="loadData()">
          <RefreshCw class="h-4 w-4" /> 更新
        </button>
      </div>
    </div>

    <div class="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <select v-model="filterSource" class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none">
        <option value="">全部来源</option>
        <option v-for="item in sources" :key="item.key" :value="item.key">{{ item.label }}</option>
      </select>
      <select v-model="filterStatus" class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none">
        <option value="">全部状态</option>
        <option v-for="item in statuses" :key="item.key" :value="item.key">{{ item.label }}</option>
      </select>
      <button class="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700" @click="handleSearch">查询</button>
      <button class="rounded-lg bg-slate-100 px-4 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="handleReset">重置</button>
      <button
        class="ml-auto inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="cleaning"
        @click="handleCleanup"
      >
        <Trash2 class="h-4 w-4" /> {{ cleaning ? '清理中' : '清理过期' }}
      </button>
    </div>

    <div v-if="loading" class="py-12 text-center text-sm text-slate-500">加载中...</div>
    <div v-else class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table class="w-full min-w-[1180px] text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">任务名称</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">来源</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">状态</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">创建人</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">创建时间</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">开始时间</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">结束时间</th>
            <th class="px-4 py-2.5 text-right font-medium text-slate-700">导出行数</th>
            <th class="px-4 py-2.5 text-right font-medium text-slate-700">文件大小</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">失败原因</th>
            <th class="px-4 py-2.5 text-right font-medium text-slate-700">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in items" :key="task.id" class="border-t border-slate-100 hover:bg-slate-50">
            <td class="max-w-[220px] px-4 py-2.5">
              <div class="truncate font-medium text-slate-900" :title="task.task_name">{{ task.task_name }}</div>
              <div v-if="task.retry_of_task_id" class="mt-0.5 text-xs text-slate-400">重试自 #{{ task.retry_of_task_id }}</div>
            </td>
            <td class="px-4 py-2.5 text-slate-600">{{ sourceLabel(task.source) }}</td>
            <td class="px-4 py-2.5"><span class="rounded px-2 py-0.5 text-xs" :class="statusClass(task.status)">{{ statusLabel(task.status) }}</span></td>
            <td class="px-4 py-2.5 text-slate-600">{{ task.created_by || '--' }}</td>
            <td class="px-4 py-2.5 text-slate-600">{{ formatTime(task.created_at) }}</td>
            <td class="px-4 py-2.5 text-slate-600">{{ formatTime(task.started_at) }}</td>
            <td class="px-4 py-2.5 text-slate-600">{{ formatTime(task.finished_at || task.canceled_at) }}</td>
            <td class="px-4 py-2.5 text-right text-slate-600">{{ task.row_count }}</td>
            <td class="px-4 py-2.5 text-right text-slate-600">{{ formatSize(task.file_size) }}</td>
            <td class="max-w-[220px] px-4 py-2.5 text-slate-500">
              <span class="block truncate" :title="task.error_message || ''">{{ task.error_message || '--' }}</span>
            </td>
            <td class="px-4 py-2.5 text-right">
              <div class="inline-flex items-center justify-end gap-2">
                <button
                  v-if="task.can_cancel"
                  class="inline-flex items-center gap-1 rounded-lg bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="operatingId === task.id"
                  @click="handleCancel(task)"
                >
                  <XCircle class="h-3.5 w-3.5" /> 取消
                </button>
                <button
                  v-if="task.can_retry"
                  class="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="operatingId === task.id"
                  @click="handleRetry(task)"
                >
                  <RotateCcw class="h-3.5 w-3.5" /> 重试
                </button>
                <button
                  v-if="task.download_url"
                  class="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="isDownloading(task.id)"
                  @click="handleDownload(task)"
                >
                  <Download class="h-3.5 w-3.5" /> {{ isDownloading(task.id) ? '下载中' : '下载' }}
                </button>
                <span v-if="!task.can_cancel && !task.can_retry && !task.download_url" class="text-xs text-slate-400">--</span>
              </div>
            </td>
          </tr>
          <tr v-if="items.length === 0">
            <td colspan="11" class="py-12 text-center text-sm text-slate-500">暂无导出任务</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-if="total > 0" :page="page" v-model:page-size="pageSize" :total="total" @change="handlePageChange" />
  </div>
</template>
