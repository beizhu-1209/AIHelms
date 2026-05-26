<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getResourceApplications,
  approveResourceApplication,
  rejectResourceApplication,
  type ResourceApplication,
} from '@aihelms/shared'
import { toast } from '@aihelms/shared'
import Pagination from '../../components/Pagination.vue'

const applications = ref<ResourceApplication[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const filterStatus = ref<string>('pending')
const filterType = ref<string>('')

const reviewing = ref<ResourceApplication | null>(null)
const reviewAction = ref<'approve' | 'reject'>('approve')
const reviewNotes = ref('')

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  model: '模型',
  mcp: 'MCP',
  skill: 'Skill',
  agent: '智能体',
}

async function loadApplications(): Promise<void> {
  loading.value = true
  try {
    const res = await getResourceApplications(
      page.value,
      pageSize.value,
      undefined,
      filterType.value || undefined,
      filterStatus.value || undefined,
    )
    applications.value = res.items
    total.value = res.total
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

function openReview(app: ResourceApplication, action: 'approve' | 'reject'): void {
  reviewing.value = app
  reviewAction.value = action
  reviewNotes.value = ''
}

async function submitReview(): Promise<void> {
  if (!reviewing.value) return
  try {
    if (reviewAction.value === 'approve') {
      await approveResourceApplication(reviewing.value.id, { review_notes: reviewNotes.value })
      toast.success('申请已批准，资源已加入用户主 Key')
    } else {
      await rejectResourceApplication(reviewing.value.id, { review_notes: reviewNotes.value })
      toast.success('申请已拒绝')
    }
    reviewing.value = null
    await loadApplications()
  } catch (e) {
    toast.error((e as { message?: string }).message || '审批失败')
  }
}

function handleFilterChange(): void {
  page.value = 1
  loadApplications()
}

function handlePageChange(newPage: number): void {
  page.value = newPage
  loadApplications()
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

onMounted(loadApplications)
</script>

<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-slate-900">AI 资源审批</h1>
      <p class="mt-1 text-sm text-slate-500">
        审批用户对模型、MCP、Skill、智能体等 AI 资源的领用申请，通过后自动加入用户主 Key
      </p>
    </div>

    <div class="mb-4 flex items-center gap-3">
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
      :page-size="pageSize"
      :total="total"
      @change="handlePageChange"
    />

    <!-- Review dialog -->
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
            @click="reviewing = null"
          >
            取消
          </button>
          <button
            class="rounded-lg px-4 py-2 text-sm font-medium text-white"
            :class="
              reviewAction === 'approve'
                ? 'bg-green-600 hover:bg-green-700'
                : 'bg-red-600 hover:bg-red-700'
            "
            @click="submitReview"
          >
            确认
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
