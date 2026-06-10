<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Download } from 'lucide-vue-next'
import * as icons from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import {
  getAgentLogs,
  getAgentLogFilters,
  createExportTask,
  toast,
  type AgentLog,
  type AgentLogFilters,
} from '@aihelms/shared'
import Pagination from '../../../components/Pagination.vue'

const logs = ref<AgentLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const route = useRoute()
const loading = ref(false)
const exporting = ref(false)
const exportNotice = ref('')

function getIconComponent(name: string | undefined) {
  if (!name) return null
  return (icons as Record<string, unknown>)[name] || null
}

const filters = ref<AgentLogFilters>({ users: [], agents: [], platforms: [] })
const filterStartTime = ref('')
const filterEndTime = ref('')
const filterUserId = ref<number | ''>('')
const filterAgentId = ref<number | ''>('')
const filterPlatform = ref('')

async function loadLogs(): Promise<void> {
  loading.value = true
  try {
    const res = await getAgentLogs({
      page: page.value,
      page_size: pageSize.value,
      start_time: filterStartTime.value || undefined,
      end_time: filterEndTime.value || undefined,
      user_id: filterUserId.value === '' ? undefined : Number(filterUserId.value),
      agent_id: filterAgentId.value === '' ? undefined : Number(filterAgentId.value),
      platform: filterPlatform.value || undefined,
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
    filters.value = await getAgentLogFilters()
  } catch {
    /* ignore */
  }
}

function applyRouteFilters(): void {
  const q = route.query
  if (typeof q.start_date === 'string') filterStartTime.value = `${q.start_date}T00:00`
  if (typeof q.end_date === 'string') filterEndTime.value = `${q.end_date}T23:59`
  if (typeof q.user_id === 'string') filterUserId.value = Number(q.user_id)
  if (typeof q.agent_id === 'string') filterAgentId.value = Number(q.agent_id)
}

function handleSearch(): void {
  page.value = 1
  loadLogs()
}

function handleReset(): void {
  filterStartTime.value = ''
  filterEndTime.value = ''
  filterUserId.value = ''
  filterAgentId.value = ''
  filterPlatform.value = ''
  page.value = 1
  loadLogs()
}

function handlePageChange(p: number): void {
  page.value = p
  loadLogs()
}

async function handleExport(): Promise<void> {
  exporting.value = true
  try {
    await createExportTask({
      source: 'usage_logs',
      export_type: 'agent',
      task_name: '智能体使用日志导出',
      params: {
      start_time: filterStartTime.value || undefined,
      end_time: filterEndTime.value || undefined,
      user_id: filterUserId.value === '' ? undefined : Number(filterUserId.value),
      agent_id: filterAgentId.value === '' ? undefined : Number(filterAgentId.value),
      platform: filterPlatform.value || undefined,
    },
    })
    exportNotice.value = '导出任务已创建，请到资源审计 > 导出任务下载表格'
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建导出任务失败')
  } finally {
    exporting.value = false
  }
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return iso.replace('T', ' ').slice(0, 19)
}

onMounted(() => {
  applyRouteFilters()
  loadFilters()
  loadLogs()
})
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <input v-model="filterStartTime" type="datetime-local" class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none" />
      <span class="text-sm text-slate-400">至</span>
      <input v-model="filterEndTime" type="datetime-local" class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none" />
      <select v-model="filterUserId" class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none">
        <option value="">全部用户</option>
        <option v-for="u in filters.users" :key="u.id" :value="u.id">{{ u.display_name || u.username }}</option>
      </select>
      <select v-model="filterAgentId" class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none">
        <option value="">全部智能体</option>
        <option v-for="a in filters.agents" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <select v-model="filterPlatform" class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none">
        <option value="">全部平台</option>
        <option v-for="p in filters.platforms" :key="p" :value="p">{{ p }}</option>
      </select>
      <button class="rounded-lg bg-purple-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-purple-700" @click="handleSearch">查询</button>
      <button class="rounded-lg bg-slate-100 px-4 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="handleReset">重置</button>
      <button
        class="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="exporting"
        @click="handleExport"
      >
        <Download class="h-4 w-4" /> {{ exporting ? '导出中' : '导出' }}
      </button>
    </div>

    <div v-if="exportNotice" class="mb-4 flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
      <span>{{ exportNotice }}</span>
      <RouterLink to="/export-tasks" class="rounded-md border border-emerald-300 bg-white px-3 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100">去下载</RouterLink>
    </div>

    <div v-if="loading" class="py-12 text-center text-sm text-slate-500">加载中...</div>
    <div v-else-if="logs.length === 0" class="py-12 text-center text-sm text-slate-500">暂无智能体使用日志</div>
    <div v-else class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">时间</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">用户</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">部门</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">智能体</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">平台</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">Session ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id" class="border-t border-slate-100">
            <td class="px-4 py-2.5 text-xs text-slate-500">{{ formatTime(log.created_at) }}</td>
            <td class="px-4 py-2.5 text-slate-900">{{ log.user?.display_name || log.user?.username || '—' }}</td>
            <td class="px-4 py-2.5 text-slate-700">{{ log.user?.department_name || '—' }}</td>
            <td class="px-4 py-2.5 text-slate-700">
              <component
                :is="getIconComponent(log.agent?.icon)"
                v-if="log.agent?.icon && getIconComponent(log.agent.icon)"
                class="mr-1 inline h-4 w-4 align-[-2px] text-slate-500"
              />
              {{ log.agent?.name || '—' }}
            </td>
            <td class="px-4 py-2.5 text-slate-700">{{ log.platform || '—' }}</td>
            <td class="px-4 py-2.5 text-xs font-mono text-slate-600">{{ log.session_id || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-if="total > 0" :page="page" :page-size="pageSize" :total="total" @change="handlePageChange" />
  </div>
</template>
