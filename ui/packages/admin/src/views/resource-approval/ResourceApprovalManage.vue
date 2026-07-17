<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  getResourceApplications,
  approveResourceApplication,
  rejectResourceApplication,
  batchApproveResourceApplications,
  batchRejectResourceApplications,
  getUsers,
  type BatchReviewResult,
  type ResourceApplication,
  type User,
} from '@aihelms/shared'
import { toast } from '@aihelms/shared'
import Pagination from '../../components/Pagination.vue'
import SearchableSelect from '../../components/SearchableSelect.vue'

const applications = ref<ResourceApplication[]>([])
const users = ref<User[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const submitting = ref(false)
const filterStatus = ref<string>('pending')
const filterType = ref<string>('')
const filterUserId = ref<number | ''>('')
const selectedApplicantLabel = ref('')
const usersLoading = ref(false)
const selectedIds = ref<Set<number>>(new Set())
let userSearchTimer: ReturnType<typeof setTimeout> | undefined
let userRequestId = 0

const reviewing = ref<ResourceApplication | null>(null)
const reviewAction = ref<'approve' | 'reject'>('approve')
const batchAction = ref<'approve' | 'reject' | null>(null)
const reviewNotes = ref('')

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  model: '模型',
  mcp: 'MCP',
  skill: 'Skill',
  agent: '智能体',
}

const pendingApplications = computed(() =>
  applications.value.filter(app => app.status === 'pending'),
)
const selectedCount = computed(() => selectedIds.value.size)
const allPendingSelected = computed(
  () =>
    pendingApplications.value.length > 0 &&
    pendingApplications.value.every(app => selectedIds.value.has(app.id)),
)
const userOptions = computed(() => users.value.map((user) => ({
  value: user.id,
  label: userName(user),
  searchText: `${user.username} ${user.email || ''}`,
})))

async function loadApplications(): Promise<void> {
  loading.value = true
  try {
    const res = await getResourceApplications(
      page.value,
      pageSize.value,
      filterUserId.value || undefined,
      filterType.value || undefined,
      filterStatus.value || undefined,
    )
    applications.value = res.items
    total.value = res.total
    pruneSelection()
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadUsers(keyword = ''): Promise<void> {
  const requestId = ++userRequestId
  usersLoading.value = true
  try {
    const res = await getUsers(1, 50, keyword.trim() || undefined)
    if (requestId !== userRequestId) return
    users.value = res.items
    const selectedUser = users.value.find((user) => user.id === filterUserId.value)
    if (selectedUser) selectedApplicantLabel.value = userName(selectedUser)
  } catch (e) {
    if (requestId === userRequestId) {
      toast.error((e as { message?: string }).message || '申请人列表加载失败')
    }
  } finally {
    if (requestId === userRequestId) usersLoading.value = false
  }
}

function handleUserSearch(keyword: string): void {
  clearTimeout(userSearchTimer)
  userSearchTimer = setTimeout(() => loadUsers(keyword), 250)
}

function handleApplicantChange(value: number | ''): void {
  if (value === '') {
    selectedApplicantLabel.value = ''
  } else {
    const selectedUser = users.value.find((user) => user.id === value)
    if (selectedUser) selectedApplicantLabel.value = userName(selectedUser)
  }
  handleFilterChange()
}

function openReview(app: ResourceApplication, action: 'approve' | 'reject'): void {
  reviewing.value = app
  reviewAction.value = action
  reviewNotes.value = ''
}

function openBatchReview(action: 'approve' | 'reject'): void {
  if (selectedCount.value === 0) return
  batchAction.value = action
  reviewNotes.value = ''
}

function closeReviewDialog(): void {
  reviewing.value = null
  batchAction.value = null
  reviewNotes.value = ''
}

async function submitReview(): Promise<void> {
  if (!reviewing.value || submitting.value) return
  submitting.value = true
  try {
    if (reviewAction.value === 'approve') {
      await approveResourceApplication(reviewing.value.id, { review_notes: reviewNotes.value })
      toast.success('申请已批准，资源已加入用户主 Key')
    } else {
      await rejectResourceApplication(reviewing.value.id, { review_notes: reviewNotes.value })
      toast.success('申请已拒绝')
    }
    closeReviewDialog()
    clearSelection()
    await loadApplications()
  } catch (e) {
    toast.error((e as { message?: string }).message || '审批失败')
  } finally {
    submitting.value = false
  }
}

async function submitBatchReview(): Promise<void> {
  if (!batchAction.value || submitting.value) return
  const appIds = Array.from(selectedIds.value)
  submitting.value = true
  try {
    const result =
      batchAction.value === 'approve'
        ? await batchApproveResourceApplications({
            app_ids: appIds,
            review_notes: reviewNotes.value,
          })
        : await batchRejectResourceApplications({
            app_ids: appIds,
            review_notes: reviewNotes.value,
          })
    showBatchResult(result)
    closeReviewDialog()
    clearSelection()
    await loadApplications()
  } catch (e) {
    toast.error((e as { message?: string }).message || '批量审批失败')
  } finally {
    submitting.value = false
  }
}

function showBatchResult(result: BatchReviewResult): void {
  const message = `成功 ${result.success.length} 条，失败 ${result.failed.length} 条`
  if (result.failed.length === 0) {
    toast.success(message)
    return
  }
  const detail = result.failed
    .slice(0, 3)
    .map(item => `#${item.id} ${item.reason}`)
    .join('；')
  toast.warning(`${message}：${detail}`, 8000)
}

function handleFilterChange(): void {
  page.value = 1
  clearSelection()
  loadApplications()
}

function handlePageChange(newPage: number): void {
  page.value = newPage
  clearSelection()
  loadApplications()
}

function handleRowSelection(app: ResourceApplication, event: Event): void {
  const target = event.target as HTMLInputElement
  const next = new Set(selectedIds.value)
  if (target.checked && app.status === 'pending') {
    next.add(app.id)
  } else {
    next.delete(app.id)
  }
  selectedIds.value = next
}

function toggleCurrentPage(event: Event): void {
  const target = event.target as HTMLInputElement
  const next = new Set(selectedIds.value)
  pendingApplications.value.forEach(app => {
    if (target.checked) {
      next.add(app.id)
    } else {
      next.delete(app.id)
    }
  })
  selectedIds.value = next
}

function clearSelection(): void {
  selectedIds.value = new Set()
}

function pruneSelection(): void {
  const pendingIds = new Set(pendingApplications.value.map(app => app.id))
  selectedIds.value = new Set([...selectedIds.value].filter(id => pendingIds.has(id)))
}

function statusColor(status: string): string {
  if (status === 'pending') return 'bg-amber-50 text-amber-700'
  if (status === 'approved') return 'bg-green-50 text-green-700'
  if (status === 'rejected') return 'bg-red-50 text-red-700'
  return 'bg-slate-100 text-slate-700'
}

function statusLabel(status: string): string {
  if (status === 'pending') return '待审批'
  if (status === 'approved') return '已批准'
  if (status === 'rejected') return '已拒绝'
  return status
}

function resourceLabel(type: string): string {
  return RESOURCE_TYPE_LABELS[type] || type
}

function resourceName(app: ResourceApplication): string {
  if (app.resource_info) {
    return app.resource_info.name || app.resource_info.model_id || app.resource_info.server_name || `#${app.resource_id}`
  }
  return `#${app.resource_id}`
}

function userName(user: User): string {
  return user.display_name || user.username || `#${user.id}`
}

onMounted(() => {
  loadApplications()
  loadUsers()
})

onBeforeUnmount(() => clearTimeout(userSearchTimer))
</script>

<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-slate-900">AI 资源审批</h1>
      <p class="mt-1 text-sm text-slate-500">
        审批用户对模型、MCP、Skill、智能体等 AI 资源的领用申请，通过后自动加入用户主 Key
      </p>
    </div>

    <div class="mb-4 flex flex-wrap items-center gap-3">
      <select
        v-model="filterType"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
        @change="handleFilterChange"
      >
        <option value="">全部类型</option>
        <option value="model">模型</option>
        <option value="mcp">MCP</option>
        <option value="skill">Skill</option>
        <option value="agent">智能体</option>
      </select>
      <select
        v-model="filterStatus"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none"
        @change="handleFilterChange"
      >
        <option value="">全部状态</option>
        <option value="pending">待审批</option>
        <option value="approved">已批准</option>
        <option value="rejected">已拒绝</option>
      </select>
      <SearchableSelect
        v-model="filterUserId"
        :options="userOptions"
        :selected-label="selectedApplicantLabel"
        :loading="usersLoading"
        remote
        placeholder="全部申请人"
        search-placeholder="输入姓名或账号搜索"
        class="w-52"
        @search="handleUserSearch"
        @change="handleApplicantChange"
      />
      <div class="ml-auto flex items-center gap-2">
        <span class="text-xs text-slate-500">已选 {{ selectedCount }} 项</span>
        <button
          class="rounded-lg bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="selectedCount === 0"
          @click="openBatchReview('approve')"
        >
          批量批准
        </button>
        <button
          class="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="selectedCount === 0"
          @click="openBatchReview('reject')"
        >
          批量拒绝
        </button>
      </div>
    </div>

    <div v-if="loading" class="py-12 text-center text-sm text-slate-500">加载中...</div>
    <div
      v-else-if="applications.length === 0"
      class="py-12 text-center text-sm text-slate-500"
    >
      暂无申请记录
    </div>
    <div v-else class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="w-10 px-4 py-2.5 text-left">
              <input
                type="checkbox"
                class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                :checked="allPendingSelected"
                :disabled="pendingApplications.length === 0"
                @change="toggleCurrentPage"
              />
            </th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">申请人</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">资源类型</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">资源</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">理由</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">状态</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">申请时间</th>
            <th class="px-4 py-2.5 text-right font-medium text-slate-700">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="app in applications" :key="app.id" class="border-t border-slate-100">
            <td class="px-4 py-2.5">
              <input
                type="checkbox"
                class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500 disabled:cursor-not-allowed disabled:opacity-40"
                :checked="selectedIds.has(app.id)"
                :disabled="app.status !== 'pending'"
                @change="handleRowSelection(app, $event)"
              />
            </td>
            <td class="px-4 py-2.5 text-slate-900">
              {{ app.user?.display_name || app.user?.username || `#${app.user_id}` }}
            </td>
            <td class="px-4 py-2.5 text-slate-700">
              <span class="rounded bg-purple-50 px-2 py-0.5 text-xs text-purple-700">
                {{ resourceLabel(app.resource_type) }}
              </span>
            </td>
            <td class="px-4 py-2.5 text-slate-700">{{ resourceName(app) }}</td>
            <td class="px-4 py-2.5 max-w-xs truncate text-xs text-slate-600">
              {{ app.reason || '-' }}
            </td>
            <td class="px-4 py-2.5">
              <span class="rounded px-2 py-0.5 text-xs" :class="statusColor(app.status)">
                {{ statusLabel(app.status) }}
              </span>
            </td>
            <td class="px-4 py-2.5 text-xs text-slate-500">
              {{ app.created_at?.replace('T', ' ').slice(0, 19) }}
            </td>
            <td class="px-4 py-2.5 text-right">
              <div v-if="app.status === 'pending'" class="flex justify-end gap-2">
                <button
                  class="rounded-lg bg-green-50 px-3 py-1 text-xs font-medium text-green-700 hover:bg-green-100"
                  @click="openReview(app, 'approve')"
                >
                  批准
                </button>
                <button
                  class="rounded-lg bg-red-50 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
                  @click="openReview(app, 'reject')"
                >
                  拒绝
                </button>
              </div>
              <span v-else class="text-xs text-slate-400">已处理</span>
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

    <div
      v-if="reviewing"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
    >
      <div
        class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl"
      >
        <h3 class="mb-4 text-lg font-semibold text-slate-900">
          {{ reviewAction === 'approve' ? '批准申请' : '拒绝申请' }}
        </h3>
        <div class="mb-4 rounded-lg bg-slate-50 p-3 text-sm">
          <div class="mb-1 text-slate-700">
            申请人：{{ reviewing.user?.display_name || reviewing.user?.username }}
          </div>
          <div class="mb-1 text-slate-700">
            资源：{{ resourceLabel(reviewing.resource_type) }} - {{ resourceName(reviewing) }}
          </div>
          <div class="text-slate-600 text-xs">理由：{{ reviewing.reason || '-' }}</div>
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-slate-700">审批备注</label>
          <textarea
            v-model="reviewNotes"
            rows="3"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <p v-if="reviewAction === 'approve'" class="mb-4 text-xs text-slate-500">
          批准后将自动把该资源加入用户的个人主 Key，立即生效
        </p>
        <div class="flex justify-end gap-3">
          <button
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            :disabled="submitting"
            @click="closeReviewDialog"
          >
            取消
          </button>
          <button
            class="rounded-lg px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            :class="
              reviewAction === 'approve'
                ? 'bg-green-600 hover:bg-green-700'
                : 'bg-red-600 hover:bg-red-700'
            "
            :disabled="submitting"
            @click="submitReview"
          >
            确认
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="batchAction"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
    >
      <div
        class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl"
      >
        <h3 class="mb-4 text-lg font-semibold text-slate-900">
          {{ batchAction === 'approve' ? '批量批准申请' : '批量拒绝申请' }}
        </h3>
        <div class="mb-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
          将处理当前页已选中的 {{ selectedCount }} 条待审批申请。
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-slate-700">审批备注</label>
          <textarea
            v-model="reviewNotes"
            rows="3"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <p v-if="batchAction === 'approve'" class="mb-4 text-xs text-slate-500">
          批准后将逐条把资源加入对应用户的个人主 Key；失败项会保留为待处理
        </p>
        <div class="flex justify-end gap-3">
          <button
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            :disabled="submitting"
            @click="closeReviewDialog"
          >
            取消
          </button>
          <button
            class="rounded-lg px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            :class="
              batchAction === 'approve'
                ? 'bg-green-600 hover:bg-green-700'
                : 'bg-red-600 hover:bg-red-700'
            "
            :disabled="submitting"
            @click="submitBatchReview"
          >
            确认处理
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
