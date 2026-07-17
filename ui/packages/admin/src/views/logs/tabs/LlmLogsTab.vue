<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { Download } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import {
  getLlmLogs,
  getLlmLogById,
  getLlmLogFilters,
  createExportTask,
  toast,
  type LlmLog,
  type LlmLogDetail,
  type LlmLogFilters,
} from '@aihelms/shared'
import Pagination from '../../../components/Pagination.vue'
import SearchableSelect from '../../../components/SearchableSelect.vue'
import LogDrawer from '../components/LogDrawer.vue'

const logs = ref<LlmLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const route = useRoute()
const loading = ref(false)
const exporting = ref(false)
const exportNotice = ref('')

const filters = ref<LlmLogFilters>({ users: [], ai_keys: [], models: [], providers: [], user_key_pairs: [] })
const filterStartTime = ref('')
const filterEndTime = ref('')
const filterUserId = ref<number | ''>('')
const filterAiKeyId = ref<number | ''>('')
const filterModel = ref('')
const filterOnlyActive = ref(false)
const routeModels = ref<string[]>([])
const filterProvider = ref('')
const filterStatus = ref<string>('')

const drawerOpen = ref(false)
const detail = ref<LlmLogDetail | null>(null)

const visibleModelOptions = computed(() => {
  if (!filterOnlyActive.value) return filters.value.models
  return filters.value.models.filter((m) => m.active)
})

const userOptions = computed(() => filters.value.users.map((user) => ({
  value: user.id,
  label: user.display_name || user.username,
  searchText: `${user.username} ${user.department_name || ''}`,
})))

const userById = computed(() => new Map(filters.value.users.map((user) => [user.id, user])))

const keyUserIdsMap = computed(() => {
  const result = new Map<number, Set<number>>()
  for (const pair of filters.value.user_key_pairs) {
    const userIds = result.get(pair.ai_key_id) || new Set<number>()
    userIds.add(pair.user_id)
    result.set(pair.ai_key_id, userIds)
  }
  return result
})

const availableAiKeys = computed(() => {
  if (filterUserId.value === '') return filters.value.ai_keys
  return filters.value.ai_keys.filter((key) => (
    keyUserIdsMap.value.get(key.id)?.has(Number(filterUserId.value))
  ))
})

const aiKeyOptions = computed(() => availableAiKeys.value.map((key) => {
  const userIds = [...(keyUserIdsMap.value.get(key.id) || [])]
  const selectedUser = filterUserId.value === '' ? undefined : userById.value.get(Number(filterUserId.value))
  const userLabel = selectedUser
    ? (selectedUser.display_name || selectedUser.username)
    : userIds.length === 1
      ? (userById.value.get(userIds[0])?.display_name || userById.value.get(userIds[0])?.username || '未知人员')
      : `${userIds.length}人使用`
  const relatedUsers = userIds.map((userId) => {
    const user = userById.value.get(userId)
    return user ? `${user.display_name} ${user.username} ${user.department_name}` : ''
  }).join(' ')
  const token = key.key_token || '无 Token'
  return {
    value: key.id,
    label: `${userLabel} / ${key.name} / ${token}`,
    searchText: `${relatedUsers} ${key.name} ${token}`,
  }
}))

const modelOptions = computed(() => visibleModelOptions.value.map((model) => ({
  value: model.value,
  label: model.value,
})))

watch(visibleModelOptions, (options) => {
  if (filterModel.value && !options.some((m) => m.value === filterModel.value)) {
    filterModel.value = ''
  }
})

async function loadLogs(): Promise<void> {
  loading.value = true
  try {
    const res = await getLlmLogs({
      page: page.value,
      page_size: pageSize.value,
      start_time: filterStartTime.value || undefined,
      end_time: filterEndTime.value || undefined,
      user_id: filterUserId.value === '' ? undefined : Number(filterUserId.value),
      ai_key_id: filterAiKeyId.value === '' ? undefined : Number(filterAiKeyId.value),
      model: routeModels.value.length ? undefined : filterModel.value || undefined,
      models: routeModels.value.length ? routeModels.value.join(',') : undefined,
      provider: filterProvider.value || undefined,
      status: filterStatus.value ? (filterStatus.value as 'success' | 'failure') : undefined,
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
    filters.value = await getLlmLogFilters()
    resetKeyIfMismatched()
  } catch {
    /* ignore */
  }
}

function resetKeyIfMismatched(): void {
  if (filterAiKeyId.value !== '' && !availableAiKeys.value.some((key) => key.id === filterAiKeyId.value)) {
    filterAiKeyId.value = ''
  }
}

function applyRouteFilters(): void {
  const q = route.query
  if (typeof q.start_date === 'string') filterStartTime.value = `${q.start_date}T00:00`
  if (typeof q.end_date === 'string') filterEndTime.value = `${q.end_date}T23:59`
  if (typeof q.user_id === 'string') filterUserId.value = Number(q.user_id)
  if (typeof q.ai_key_id === 'string') filterAiKeyId.value = Number(q.ai_key_id)
  if (typeof q.model === 'string') filterModel.value = q.model
  if (typeof q.models === 'string') routeModels.value = q.models.split(',').map((item) => item.trim()).filter(Boolean)
}

function handleSearch(): void {
  routeModels.value = []
  page.value = 1
  loadLogs()
}

function handleReset(): void {
  filterStartTime.value = ''
  filterEndTime.value = ''
  filterUserId.value = ''
  filterAiKeyId.value = ''
  filterModel.value = ''
  filterOnlyActive.value = false
  routeModels.value = []
  filterProvider.value = ''
  filterStatus.value = ''
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
      export_type: 'llm',
      task_name: '模型调用日志导出',
      params: {
      start_time: filterStartTime.value || undefined,
      end_time: filterEndTime.value || undefined,
      user_id: filterUserId.value === '' ? undefined : Number(filterUserId.value),
      ai_key_id: filterAiKeyId.value === '' ? undefined : Number(filterAiKeyId.value),
      model: routeModels.value.length ? undefined : filterModel.value || undefined,
      models: routeModels.value.length ? routeModels.value.join(',') : undefined,
      provider: filterProvider.value || undefined,
      status: filterStatus.value || undefined,
    },
    })
    exportNotice.value = '导出任务已创建，请到资源审计 > 导出任务下载表格'
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建导出任务失败')
  } finally {
    exporting.value = false
  }
}

async function openDetail(log: LlmLog): Promise<void> {
  try {
    detail.value = await getLlmLogById(log.id)
    drawerOpen.value = true
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载详情失败')
  }
}

function closeDetail(): void {
  drawerOpen.value = false
  setTimeout(() => {
    detail.value = null
  }, 100)
}

function formatTime(val: string | null): string {
  if (!val) return '—'
  return val.slice(0, 19)
}

function isSuccess(status: string): boolean {
  return status === 'success'
}

function userLabel(log: LlmLog): string {
  if (!log.user) return '—'
  const dept = log.user.department_name ? ` (${log.user.department_name})` : ''
  return `${log.user.display_name || log.user.username}${dept}`
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
      <SearchableSelect
        v-model="filterUserId"
        :options="userOptions"
        placeholder="全部人员"
        search-placeholder="搜索姓名、账号或部门"
        class="w-44"
        @change="resetKeyIfMismatched"
      />
      <SearchableSelect
        v-model="filterAiKeyId"
        :options="aiKeyOptions"
        placeholder="全部 Key"
        search-placeholder="搜索人员、Key 或 Token"
        class="w-[26rem]"
      />
      <label class="inline-flex items-center gap-1.5 text-sm text-slate-600">
        <input
          v-model="filterOnlyActive"
          type="checkbox"
          class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500"
        />
        仅看在用
      </label>
      <SearchableSelect
        v-model="filterModel"
        :options="modelOptions"
        placeholder="全部模型"
        search-placeholder="搜索模型"
        class="w-52"
      />
      <select
        v-model="filterProvider"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
      >
        <option value="">全部供应商</option>
        <option v-for="p in filters.providers" :key="p" :value="p">{{ p }}</option>
      </select>
      <select
        v-model="filterStatus"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
      >
        <option value="">全部状态</option>
        <option value="success">成功</option>
        <option value="failure">失败</option>
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
    <div v-else-if="logs.length === 0" class="py-12 text-center text-sm text-slate-500">
      暂无模型调用日志
    </div>
    <div v-else class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">时间</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">用户</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">Key</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">模型</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">状态</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">Tokens</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">外部</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">内部</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">耗时</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="log in logs"
            :key="log.id"
            class="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
            @click="openDetail(log)"
          >
            <td class="px-4 py-2.5 text-xs text-slate-500">{{ formatTime(log.started_at) }}</td>
            <td class="px-4 py-2.5 text-slate-900">{{ userLabel(log) }}</td>
            <td class="px-4 py-2.5 text-slate-700 font-mono text-xs">{{ log.ai_key?.key_token || '—' }}</td>
            <td class="px-4 py-2.5 text-slate-700">{{ log.model }}</td>
            <td class="px-4 py-2.5">
              <span
                class="rounded px-2 py-0.5 text-xs"
                :class="isSuccess(log.status)
                  ? 'bg-green-50 text-green-700'
                  : 'bg-red-50 text-red-700'"
              >
                {{ isSuccess(log.status) ? '成功' : '失败' }}
              </span>
            </td>
            <td class="px-4 py-2.5 text-xs text-slate-600">
              <div>输入：{{ log.prompt_tokens }}</div>
              <div>输出：{{ log.completion_tokens }}</div>
              <div>缓存读：{{ log.cache_read_tokens }}</div>
              <div>缓存写：{{ log.cache_creation_tokens }}</div>
            </td>
            <td class="px-4 py-2.5 text-xs text-slate-600">¥{{ log.external_cost }}</td>
            <td class="px-4 py-2.5 text-xs text-slate-600">¥{{ log.internal_cost }}</td>
            <td class="px-4 py-2.5 text-xs text-slate-500">
              {{ log.duration_ms !== null ? log.duration_ms + ' ms' : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination
      v-if="total > 0"
      :page="page"
      v-model:page-size="pageSize"
      :total="total"
      @change="handlePageChange"
    />

    <LogDrawer
      v-if="detail"
      :open="drawerOpen"
      :title="detail.model"
      :subtitle="detail.request_id"
      :header-tag="{
        text: isSuccess(detail.status) ? '成功' : '失败',
        color: isSuccess(detail.status) ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700',
      }"
      :info="[
        { label: '时间', value: formatTime(detail.started_at) },
        { label: '操作人', value: detail.user ? `${detail.user.display_name || detail.user.username} / ${detail.user.department_name || '—'}` : '—' },
        { label: 'Key', value: detail.ai_key?.key_token || '—' },
        { label: '模型', value: detail.model },
        { label: 'Provider', value: detail.provider },
        { label: 'Call Type', value: detail.call_type },
        { label: 'Tokens', value: `输入 ${detail.prompt_tokens} / 输出 ${detail.completion_tokens} / 合计 ${detail.total_tokens}` },
        { label: '缓存读', value: detail.cache_read_tokens },
        { label: '缓存写', value: detail.cache_creation_tokens },
        { label: '外部成本', value: '¥' + detail.external_cost },
        { label: '外部成本细项', value: `输入 ¥${detail.external_input_cost} / 输出 ¥${detail.external_output_cost} / 缓存命中 ¥${detail.external_cache_read_cost} / 缓存创建 ¥${detail.external_cache_creation_cost}` },
        { label: '内部成本', value: '¥' + detail.internal_cost },
        { label: '内部成本细项', value: `输入 ¥${detail.internal_input_cost} / 输出 ¥${detail.internal_output_cost} / 缓存命中 ¥${detail.internal_cache_read_cost} / 缓存创建 ¥${detail.internal_cache_creation_cost}` },
        { label: '耗时', value: detail.duration_ms !== null ? detail.duration_ms + ' ms' : '—' },
        { label: '首 Token', value: detail.ttft_ms !== null ? detail.ttft_ms + ' ms' : '—' },
        { label: 'Session ID', value: detail.session_id, mono: true },
        { label: '错误', value: detail.error_message },
      ]"
      :json-blocks="[
        { label: '请求', value: detail.messages, collapsed: false },
        { label: '返回', value: detail.response, collapsed: false },
        { label: 'Metadata', value: detail.metadata, collapsed: true },
      ]"
      @close="closeDetail"
    />
  </div>
</template>
