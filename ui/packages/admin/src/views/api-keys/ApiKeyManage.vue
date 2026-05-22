<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Eye, EyeOff, Copy, Check } from 'lucide-vue-next'
import {
  getApiKeys,
  createApiKey,
  updateApiKey,
  deleteApiKey,
  toast,
  usePermission,
  type ApiKey,
} from '@aihelms/shared'
import Pagination from '../../components/Pagination.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()

const keys = ref<ApiKey[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const loading = ref(false)

const createDialogOpen = ref(false)
const createForm = ref({ name: '', description: '', expires_at: '' })
const createSubmitting = ref(false)

const revealedKeys = ref<Set<number>>(new Set())
const copiedKeyId = ref<number | null>(null)

const deleteTarget = ref<ApiKey | null>(null)

async function loadKeys(): Promise<void> {
  loading.value = true
  try {
    const res = await getApiKeys(page.value, pageSize.value, keyword.value)
    keys.value = res.items
    total.value = res.total
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  page.value = 1
  loadKeys()
}

function handlePageChange(p: number): void {
  page.value = p
  loadKeys()
}

function openCreateDialog(): void {
  createForm.value = { name: '', description: '', expires_at: '' }
  createDialogOpen.value = true
}

async function submitCreate(): Promise<void> {
  if (!createForm.value.name.trim()) {
    toast.error('请填写名称')
    return
  }
  createSubmitting.value = true
  try {
    const result = await createApiKey({
      name: createForm.value.name.trim(),
      description: createForm.value.description,
      expires_at: createForm.value.expires_at
        ? new Date(createForm.value.expires_at).toISOString()
        : null,
    })
    createDialogOpen.value = false
    revealedKeys.value.add(result.id)
    await loadKeys()
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建失败')
  } finally {
    createSubmitting.value = false
  }
}

function toggleReveal(id: number): void {
  if (revealedKeys.value.has(id)) {
    revealedKeys.value.delete(id)
  } else {
    revealedKeys.value.add(id)
  }
}

async function handleCopyKey(item: ApiKey): Promise<void> {
  if (!item.raw_key) return
  try {
    await navigator.clipboard.writeText(item.raw_key)
    copiedKeyId.value = item.id
    setTimeout(() => {
      if (copiedKeyId.value === item.id) copiedKeyId.value = null
    }, 2000)
  } catch {
    toast.error('复制失败')
  }
}

function maskKey(item: ApiKey): string {
  if (!item.raw_key) return `${item.key_prefix}***`
  const tail = item.raw_key.slice(-4)
  return `${item.key_prefix}***${tail}`
}

function displayKey(item: ApiKey): string {
  return revealedKeys.value.has(item.id) && item.raw_key ? item.raw_key : maskKey(item)
}

async function handleToggle(item: ApiKey): Promise<void> {
  try {
    await updateApiKey(item.id, { is_active: !item.is_active })
    await loadKeys()
  } catch (e) {
    toast.error((e as { message?: string }).message || '操作失败')
  }
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  try {
    await deleteApiKey(deleteTarget.value.id)
    deleteTarget.value = null
    await loadKeys()
  } catch (e) {
    toast.error((e as { message?: string }).message || '删除失败')
  }
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return iso.replace('T', ' ').slice(0, 19)
}

function isExpired(iso: string | null): boolean {
  if (!iso) return false
  return new Date(iso).getTime() < Date.now()
}

onMounted(loadKeys)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">API Key</h1>
        <p class="mt-1 text-sm text-slate-500">
          管理分发给第三方系统使用的平台 API Key，权限等同管理员
        </p>
      </div>
      <button
        v-if="hasPermission('api_key:create')"
        class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]"
        @click="openCreateDialog"
      >
        新建 API Key
      </button>
    </div>

    <div class="mb-4 flex items-center gap-3">
      <input
        v-model="keyword"
        type="text"
        placeholder="搜索名称或描述"
        class="flex h-10 w-64 rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
        @keyup.enter="handleSearch"
      />
      <button
        class="rounded-lg bg-purple-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-purple-700"
        @click="handleSearch"
      >
        查询
      </button>
    </div>

    <div v-if="loading" class="py-12 text-center text-sm text-slate-500">加载中...</div>
    <div v-else-if="keys.length === 0" class="py-12 text-center text-sm text-slate-500">
      还没有 API Key
    </div>
    <div v-else class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">名称</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">Key</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">状态</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">创建时间</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">最后使用</th>
            <th class="px-4 py-2.5 text-left font-medium text-slate-700">过期时间</th>
            <th class="px-4 py-2.5 text-right font-medium text-slate-700">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in keys" :key="item.id" class="border-t border-slate-100">
            <td class="px-4 py-2.5">
              <div class="font-medium text-slate-900">{{ item.name }}</div>
              <div v-if="item.description" class="mt-0.5 text-xs text-slate-500">
                {{ item.description }}
              </div>
            </td>
            <td class="px-4 py-2.5">
              <div class="flex items-center gap-1.5">
                <code class="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-700">{{ displayKey(item) }}</code>
                <button
                  v-if="item.raw_key"
                  class="text-slate-400 transition-colors hover:text-slate-600"
                  :title="revealedKeys.has(item.id) ? '隐藏' : '显示'"
                  @click="toggleReveal(item.id)"
                >
                  <EyeOff v-if="revealedKeys.has(item.id)" class="h-3.5 w-3.5" />
                  <Eye v-else class="h-3.5 w-3.5" />
                </button>
                <button
                  v-if="item.raw_key"
                  class="text-slate-400 transition-colors hover:text-slate-600"
                  title="复制完整 Key"
                  @click="handleCopyKey(item)"
                >
                  <Check v-if="copiedKeyId === item.id" class="h-3.5 w-3.5 text-green-600" />
                  <Copy v-else class="h-3.5 w-3.5" />
                </button>
              </div>
            </td>
            <td class="px-4 py-2.5">
              <span
                v-if="isExpired(item.expires_at)"
                class="rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-700"
              >
                已过期
              </span>
              <span
                v-else-if="item.is_active"
                class="rounded bg-green-50 px-2 py-0.5 text-xs text-green-700"
              >
                启用
              </span>
              <span v-else class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                禁用
              </span>
            </td>
            <td class="px-4 py-2.5 text-xs text-slate-500">{{ formatTime(item.created_at) }}</td>
            <td class="px-4 py-2.5 text-xs text-slate-500">{{ formatTime(item.last_used_at) }}</td>
            <td class="px-4 py-2.5 text-xs text-slate-500">{{ formatTime(item.expires_at) }}</td>
            <td class="px-4 py-2.5 text-right">
              <div class="flex justify-end gap-2">
                <button
                  v-if="hasPermission('api_key:update')"
                  class="rounded-lg px-3 py-1 text-xs font-medium"
                  :class="item.is_active
                    ? 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    : 'bg-green-50 text-green-700 hover:bg-green-100'"
                  @click="handleToggle(item)"
                >
                  {{ item.is_active ? '禁用' : '启用' }}
                </button>
                <button
                  v-if="hasPermission('api_key:delete')"
                  class="rounded-lg bg-red-50 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
                  @click="deleteTarget = item"
                >
                  删除
                </button>
              </div>
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

    <!-- 创建弹窗 -->
    <div
      v-if="createDialogOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
      @click.self="createDialogOpen = false"
    >
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/95 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">新建 API Key</h3>
        <div class="space-y-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">名称<span class="ml-0.5 text-red-500">*</span></label>
            <input
              v-model="createForm.name"
              type="text"
              placeholder="如：合作方-XX-供应商"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">描述</label>
            <textarea
              v-model="createForm.description"
              rows="2"
              placeholder="可填写用途、对接人等信息"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">过期时间</label>
            <input
              v-model="createForm.expires_at"
              type="datetime-local"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
            <p class="mt-1 text-xs text-slate-400">留空表示永不过期</p>
          </div>
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            :disabled="createSubmitting"
            @click="createDialogOpen = false"
          >
            取消
          </button>
          <button
            class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
            :disabled="createSubmitting"
            @click="submitCreate"
          >
            {{ createSubmitting ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteTarget"
      title="删除 API Key"
      :message="deleteTarget ? `确定删除 Key 「${deleteTarget.name}」？删除后所有使用此 Key 的系统将无法访问平台 API` : ''"
      confirm-text="删除"
      @confirm="handleConfirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>
