<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { X, Copy, Check } from 'lucide-vue-next'
import {
  getAuditLogs,
  getAuditLogFilters,
  toast,
  type AuditLog,
  type AuditLogFilters,
} from '@aihelms/shared'
import Pagination from '../../components/Pagination.vue'

const logs = ref<AuditLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const filters = ref<AuditLogFilters>({ actors: [], actions: [] })

const filterStartTime = ref('')
const filterEndTime = ref('')
const filterUserId = ref<number | ''>('')
const filterMethod = ref<string>('')
const filterStatus = ref<string>('')
const filterAction = ref<string>('')

const detail = ref<AuditLog | null>(null)
const drawerOpen = ref(false)
const copied = ref(false)

const METHODS = ['POST', 'PUT', 'DELETE', 'PATCH']

const METHOD_COLOR: Record<string, string> = {
  POST: 'bg-green-50 text-green-700',
  PUT: 'bg-blue-50 text-blue-700',
  DELETE: 'bg-red-50 text-red-700',
  PATCH: 'bg-amber-50 text-amber-700',
}

const prettySummary = computed<string>(() => {
  if (!detail.value) return ''
  const raw = detail.value.request_summary
  if (!raw) return ''
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
})

async function loadLogs(): Promise<void> {
  loading.value = true
  try {
    const res = await getAuditLogs({
      page: page.value,
      page_size: pageSize.value,
      start_time: filterStartTime.value ? new Date(filterStartTime.value).toISOString() : undefined,
      end_time: filterEndTime.value ? new Date(filterEndTime.value).toISOString() : undefined,
      user_id: filterUserId.value === '' ? undefined : Number(filterUserId.value),
      method: filterMethod.value || undefined,
      status: filterStatus.value ? (filterStatus.value as 'success' | 'failed') : undefined,
      action: filterAction.value || undefined,
    })
    logs.value = res.items
    total.value = res.total
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadFilters(): Promise<void> {
  try {
    filters.value = await getAuditLogFilters()
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载筛选数据失败')
  }
}

function handleSearch(): void {
  page.value = 1
  loadLogs()
}

function handleReset(): void {
  filterStartTime.value = ''
  filterEndTime.value = ''
  filterUserId.value = ''
  filterMethod.value = ''
  filterStatus.value = ''
  filterAction.value = ''
  page.value = 1
  loadLogs()
}

function handlePageChange(newPage: number): void {
  page.value = newPage
  loadLogs()
}

function openDetail(log: AuditLog): void {
  detail.value = log
  drawerOpen.value = true
  copied.value = false
}

function closeDetail(): void {
  drawerOpen.value = false
  setTimeout(() => {
    detail.value = null
  }, 200)
}

function formatTime(iso: string): string {
  if (!iso) return ''
  return iso.replace('T', ' ').slice(0, 19)
}

function isSuccess(code: number): boolean {
  return code >= 200 && code < 300
}

async function handleCopy(): Promise<void> {
  if (!prettySummary.value) return
  try {
    await navigator.clipboard.writeText(prettySummary.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    toast.error('复制失败')
  }
}

onMounted(() => {
  loadFilters()
  loadLogs()
})
</script>

<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-slate-900">管理员日志</h1>
      <p class="mt-1 text-sm text-slate-500">
        记录管理员的写操作（创建、修改、删除等），用于审计与排查
      </p>
    </div>

    <div class="mb-4 flex flex-wrap items-center gap-3">
      <input
        v-model="filterStartTime"
        type="datetime-local"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
      />
      <span class="text-sm text-slate-400">至</span>
      <input
        v-model="filterEndTime"
        type="datetime-local"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
      />
      <select
        v-model="filterUserId"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
      >
        <option value="">全部操作人</option>
        <option v-for="a in filters.actors" :key="a.user_id" :value="a.user_id">
          {{ a.username }}
        </option>
      </select>
      <select
        v-model="filterAction"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
      >
        <option value="">全部操作</option>
        <option v-for="a in filters.actions" :key="a" :value="a">{{ a }}</option>
      </select>
      <select
        v-model="filterMethod"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
      >
        <option value="">全部方法</option>
        <option v-for="m in METHODS" :key="m" :value="m">{{ m }}</option>
      </select>
      <select
        v-model="filterStatus"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
      >
        <option value="">全部状态</option>
        <option value="success">成功</option>
        <option value="failed">失败</option>
      </select>
      <button
        class="rounded-lg bg-purple-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-purple-700"
        @click="handleSearch"
      >
        查询
      </button>
      <button
        class="rounded-lg bg-slate-100 px-4 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200"
        @click="handleReset"
      >
        重置
      </button>
    </div>

    <div v-if="loading" class="py-12 text-center text-sm text-slate-500">加载中...</div>
    <div v-else-if="logs.length === 0" class="py-12 text-center text-sm text-slate-500">
      暂无日志记录
    </div>
    <div v-else class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">时间</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">操作人</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">操作</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">状态</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">IP</th>
            <th class="px-4 py-2.5 text-right font-medium text-slate-700">详情</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="log in logs"
            :key="log.id"
            class="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
            @click="openDetail(log)"
          >
            <td class="px-4 py-2.5 text-xs text-slate-500">{{ formatTime(log.created_at) }}</td>
            <td class="px-4 py-2.5">
              <div class="flex items-center gap-1.5">
                <span class="text-slate-900">{{ log.username || `#${log.user_id}` }}</span>
                <span
                  v-if="log.identity_type === 'api_key'"
                  class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700"
                  title="此操作来自 API Key 调用"
                >
                  API Key
                </span>
              </div>
            </td>
            <td class="px-4 py-2.5 text-slate-700">{{ log.action }}</td>
            <td class="px-4 py-2.5">
              <span
                class="rounded px-2 py-0.5 text-xs"
                :class="isSuccess(log.status_code)
                  ? 'bg-green-50 text-green-700'
                  : 'bg-red-50 text-red-700'"
              >
                {{ isSuccess(log.status_code) ? '成功' : '失败' }} · {{ log.status_code }}
              </span>
            </td>
            <td class="px-4 py-2.5 text-xs text-slate-600">{{ log.ip || '-' }}</td>
            <td class="px-4 py-2.5 text-right">
              <button
                class="rounded-lg bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200"
                @click.stop="openDetail(log)"
              >
                查看
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination
      v-if="total > 0"
      :page="page"
      :page-size="pageSize"
      :total="total"
      @change="handlePageChange"
    />

    <!-- 右侧抽屉：日志详情 -->
    <div
      v-if="detail"
      class="fixed inset-0 z-50 transition-opacity duration-200"
      :class="drawerOpen ? 'opacity-100' : 'pointer-events-none opacity-0'"
    >
      <div class="absolute inset-0 bg-black/30" @click="closeDetail" />
      <aside
        class="absolute right-0 top-0 flex h-full w-full max-w-2xl flex-col bg-white shadow-2xl transition-transform duration-200"
        :class="drawerOpen ? 'translate-x-0' : 'translate-x-full'"
      >
        <!-- header -->
        <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-6 py-4">
          <div class="flex items-center gap-3">
            <span
              class="rounded px-2 py-0.5 text-xs font-semibold"
              :class="METHOD_COLOR[detail.method] || 'bg-slate-100 text-slate-700'"
            >
              {{ detail.method }}
            </span>
            <span
              class="rounded px-2 py-0.5 text-xs"
              :class="isSuccess(detail.status_code)
                ? 'bg-green-50 text-green-700'
                : 'bg-red-50 text-red-700'"
            >
              {{ isSuccess(detail.status_code) ? '成功' : '失败' }} · {{ detail.status_code }}
            </span>
            <span class="text-sm text-slate-500">{{ formatTime(detail.created_at) }}</span>
          </div>
          <button
            class="flex h-8 w-8 items-center justify-center rounded text-slate-500 hover:bg-slate-100"
            aria-label="关闭"
            @click="closeDetail"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <!-- body -->
        <div class="flex-1 overflow-y-auto px-6 py-5">
          <!-- Details -->
          <div class="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">详情</p>
            <div class="flex items-start gap-2 py-1">
              <span class="w-28 shrink-0 text-xs text-slate-500">操作</span>
              <span class="text-xs text-slate-900">{{ detail.action }}</span>
            </div>
            <div class="flex items-start gap-2 py-1">
              <span class="w-28 shrink-0 text-xs text-slate-500">操作人</span>
              <span class="flex items-center gap-1.5 text-xs text-slate-900">
                {{ detail.username }}
                <span class="text-slate-400">(#{{ detail.user_id }})</span>
                <span
                  v-if="detail.identity_type === 'api_key'"
                  class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700"
                >
                  API Key
                </span>
              </span>
            </div>
            <div class="flex items-start gap-2 py-1">
              <span class="w-28 shrink-0 text-xs text-slate-500">路径</span>
              <span class="break-all font-mono text-xs text-slate-700">{{ detail.path }}</span>
            </div>
            <div class="flex items-start gap-2 py-1">
              <span class="w-28 shrink-0 text-xs text-slate-500">耗时</span>
              <span class="text-xs text-slate-900">{{ detail.duration_ms }} ms</span>
            </div>
            <div class="flex items-start gap-2 py-1">
              <span class="w-28 shrink-0 text-xs text-slate-500">IP</span>
              <span class="text-xs text-slate-900">{{ detail.ip || '—' }}</span>
            </div>
            <div class="flex items-start gap-2 py-1">
              <span class="w-28 shrink-0 text-xs text-slate-500">User-Agent</span>
              <span class="break-all text-xs text-slate-700">{{ detail.user_agent || '—' }}</span>
            </div>
          </div>

          <!-- Request body -->
          <div class="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <div class="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2">
              <span class="text-xs font-semibold text-slate-600">请求体（已脱敏）</span>
              <button
                v-if="prettySummary"
                class="flex items-center gap-1 rounded p-1 text-xs text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-700"
                title="复制 JSON"
                @click="handleCopy"
              >
                <Check v-if="copied" class="h-3.5 w-3.5 text-green-600" />
                <Copy v-else class="h-3.5 w-3.5" />
              </button>
            </div>
            <pre
              class="m-0 max-h-[60vh] overflow-auto whitespace-pre-wrap break-all bg-white p-3 font-mono text-xs text-slate-800"
            >{{ prettySummary || '空' }}</pre>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

