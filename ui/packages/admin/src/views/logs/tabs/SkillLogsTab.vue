<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { Download } from 'lucide-vue-next'
import * as icons from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import {
  getSkillLogs,
  getSkillLogFilters,
  createExportTask,
  toast,
  type SkillLog,
  type SkillLogFilters,
} from '@aihelms/shared'
import Pagination from '../../../components/Pagination.vue'
import SearchableSelect from '../../../components/SearchableSelect.vue'

const logs = ref<SkillLog[]>([])
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

const filters = ref<SkillLogFilters>({ users: [], skills: [], actions: [] })
const filterStartTime = ref('')
const filterEndTime = ref('')
const filterUserId = ref<number | ''>('')
const filterSkillId = ref<number | ''>('')
const filterAction = ref('')

const userOptions = computed(() => filters.value.users.map((user) => ({
  value: user.id,
  label: user.display_name || user.username,
  searchText: `${user.username} ${user.department_name || ''}`,
})))

const skillOptions = computed(() => filters.value.skills.map((skill) => ({
  value: skill.id,
  label: skill.name,
  searchText: skill.version,
})))

async function loadLogs(): Promise<void> {
  loading.value = true
  try {
    const res = await getSkillLogs({
      page: page.value,
      page_size: pageSize.value,
      start_time: filterStartTime.value || undefined,
      end_time: filterEndTime.value || undefined,
      user_id: filterUserId.value === '' ? undefined : Number(filterUserId.value),
      skill_id: filterSkillId.value === '' ? undefined : Number(filterSkillId.value),
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
    filters.value = await getSkillLogFilters()
  } catch {
    /* ignore */
  }
}

function applyRouteFilters(): void {
  const q = route.query
  if (typeof q.start_date === 'string') filterStartTime.value = `${q.start_date}T00:00`
  if (typeof q.end_date === 'string') filterEndTime.value = `${q.end_date}T23:59`
  if (typeof q.user_id === 'string') filterUserId.value = Number(q.user_id)
  if (typeof q.skill_id === 'string') filterSkillId.value = Number(q.skill_id)
}

function handleSearch(): void {
  page.value = 1
  loadLogs()
}

function handleReset(): void {
  filterStartTime.value = ''
  filterEndTime.value = ''
  filterUserId.value = ''
  filterSkillId.value = ''
  filterAction.value = ''
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
      export_type: 'skill',
      task_name: 'Skill使用日志导出',
      params: {
      start_time: filterStartTime.value || undefined,
      end_time: filterEndTime.value || undefined,
      user_id: filterUserId.value === '' ? undefined : Number(filterUserId.value),
      skill_id: filterSkillId.value === '' ? undefined : Number(filterSkillId.value),
      action: filterAction.value || undefined,
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

function actionLabel(action: string): string {
  if (action === 'download') return '下载'
  if (action === 'install') return '安装'
  return action
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
      <SearchableSelect
        v-model="filterUserId"
        :options="userOptions"
        placeholder="全部人员"
        search-placeholder="搜索姓名、账号或部门"
        class="w-44"
      />
      <SearchableSelect
        v-model="filterSkillId"
        :options="skillOptions"
        placeholder="全部 Skill"
        search-placeholder="搜索 Skill"
        class="w-52"
      />
      <select v-model="filterAction" class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none">
        <option value="">全部动作</option>
        <option v-for="a in filters.actions" :key="a" :value="a">{{ actionLabel(a) }}</option>
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
    <div v-else-if="logs.length === 0" class="py-12 text-center text-sm text-slate-500">暂无 Skill 使用日志</div>
    <div v-else class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">时间</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">用户</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">部门</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">Skill</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">动作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id" class="border-t border-slate-100">
            <td class="px-4 py-2.5 text-xs text-slate-500">{{ formatTime(log.created_at) }}</td>
            <td class="px-4 py-2.5 text-slate-900">{{ log.user?.display_name || log.user?.username || '—' }}</td>
            <td class="px-4 py-2.5 text-slate-700">{{ log.user?.department_name || '—' }}</td>
            <td class="px-4 py-2.5 text-slate-700">
              <component
                :is="getIconComponent(log.skill?.icon)"
                v-if="log.skill?.icon && getIconComponent(log.skill.icon)"
                class="mr-1 inline h-4 w-4 align-[-2px] text-slate-500"
              />
              {{ log.skill?.name || '—' }}
            </td>
            <td class="px-4 py-2.5">
              <span class="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">{{ actionLabel(log.action) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-if="total > 0" :page="page" v-model:page-size="pageSize" :total="total" @change="handlePageChange" />
  </div>
</template>
