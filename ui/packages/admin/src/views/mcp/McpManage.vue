<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  getMcpServers,
  deleteMcpServer,
  healthCheckMcpServer,
  getMcpCategories,
  createMcpCategory,
  deleteMcpCategory,
  type McpServer,
  type McpCategory,
} from '@aihelms/shared'
import { toast, usePermission } from '@aihelms/shared'
import { Activity, RefreshCw, CheckCircle2, XCircle, HelpCircle, Eye as EyeIcon, EyeOff as EyeOffIcon } from 'lucide-vue-next'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import McpServerForm from './McpServerForm.vue'
import McpToolPanel from './McpToolPanel.vue'

const { hasPermission } = usePermission()

const servers = ref<McpServer[]>([])
const categories = ref<McpCategory[]>([])
const loading = ref(false)
const selectedServer = ref<McpServer | null>(null)
const showForm = ref(false)
const editingServer = ref<McpServer | null>(null)
const deleteTarget = ref<McpServer | null>(null)
const checkingId = ref<number | null>(null)
const selectedCategory = ref<string | null>(null)
const showCategoryForm = ref(false)
const categoryFormName = ref('')
const categoryFormDescription = ref('')
const deleteCategoryTarget = ref<McpCategory | null>(null)
const showAuthValue = ref(false)

const categoriesWithCount = computed(() => {
  const counts = new Map<string, number>()
  for (const s of servers.value) {
    counts.set(s.category, (counts.get(s.category) || 0) + 1)
  }
  return categories.value.map((c) => ({
    ...c,
    count: counts.get(c.name) || 0,
  }))
})

const filteredServers = computed(() => {
  if (!selectedCategory.value) return servers.value
  return servers.value.filter((s) => s.category === selectedCategory.value)
})

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const [serversRes, catsRes] = await Promise.all([
      getMcpServers(1, 200),
      getMcpCategories(),
    ])
    servers.value = serversRes.items
    categories.value = catsRes
    if (selectedServer.value) {
      const refreshed = serversRes.items.find((s) => s.id === selectedServer.value?.id)
      selectedServer.value = refreshed || null
    } else if (serversRes.items.length > 0) {
      selectedServer.value = serversRes.items[0]
    }
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editingServer.value = null
  showForm.value = true
}

function openEdit(): void {
  if (!selectedServer.value) return
  editingServer.value = selectedServer.value
  showForm.value = true
}

async function handleSaved(): Promise<void> {
  showForm.value = false
  await loadData()
}

async function confirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  try {
    await deleteMcpServer(deleteTarget.value.id)
    toast.success('MCP Server 删除成功')
    if (selectedServer.value?.id === deleteTarget.value.id) {
      selectedServer.value = null
    }
    deleteTarget.value = null
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '删除失败')
  }
}

async function handleHealthCheck(): Promise<void> {
  if (!selectedServer.value) return
  const server = selectedServer.value
  checkingId.value = server.id
  try {
    const updated = await healthCheckMcpServer(server.id)
    const idx = servers.value.findIndex((s) => s.id === server.id)
    if (idx >= 0) servers.value[idx] = updated
    selectedServer.value = updated
    if (updated.status === 'healthy') {
      toast.success('健康检查通过')
    } else {
      toast.error(`健康检查失败：${updated.health_check_error || '未知错误'}`)
    }
  } catch (e) {
    toast.error((e as { message?: string }).message || '健康检查失败')
  } finally {
    checkingId.value = null
  }
}

async function handleCreateCategory(): Promise<void> {
  if (!categoryFormName.value.trim()) {
    toast.error('请输入分类名称')
    return
  }
  try {
    await createMcpCategory({
      name: categoryFormName.value.trim(),
      description: categoryFormDescription.value.trim(),
    })
    toast.success('分类创建成功')
    showCategoryForm.value = false
    categoryFormName.value = ''
    categoryFormDescription.value = ''
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建失败')
  }
}

async function confirmDeleteCategory(): Promise<void> {
  if (!deleteCategoryTarget.value) return
  try {
    await deleteMcpCategory(deleteCategoryTarget.value.id)
    toast.success('分类删除成功')
    if (selectedCategory.value === deleteCategoryTarget.value.name) {
      selectedCategory.value = null
    }
    deleteCategoryTarget.value = null
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '删除失败')
  }
}

function statusBgClass(status: string): string {
  if (status === 'healthy') return 'bg-green-50 text-green-600'
  if (status === 'unhealthy') return 'bg-red-50 text-red-600'
  return 'bg-slate-100 text-slate-500'
}

function statusLabel(status: string): string {
  if (status === 'healthy') return '健康'
  if (status === 'unhealthy') return '异常'
  return '未检测'
}

function healthIconColor(status: string): string {
  if (status === 'healthy') return 'text-green-600'
  if (status === 'unhealthy') return 'text-red-600'
  return 'text-slate-500'
}

const transportLabels: Record<string, string> = {
  sse: 'SSE',
  http: 'HTTP',
  streamable_http: 'Streamable HTTP',
  streamableHttp: 'Streamable HTTP',
}

onMounted(loadData)
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex flex-1 gap-4 overflow-hidden">
      <!-- 左侧：分类导航 + Server 列表 -->
      <div
        class="w-80 shrink-0 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl"
      >
        <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
          <h3 class="text-sm font-semibold text-slate-900">MCP Server</h3>
          <button
            v-if="hasPermission('mcp:create')"
            class="rounded-md bg-purple-600 px-2.5 py-1 text-xs font-medium text-white transition-all hover:bg-purple-500"
            @click="openCreate"
          >
            新建
          </button>
        </div>

        <!-- 分类导航 -->
        <div class="border-b border-slate-100 px-2 py-1.5">
          <div class="mb-1 flex items-center justify-between px-1">
            <span class="text-xs font-medium text-slate-400">分类</span>
            <button
              v-if="hasPermission('mcp:create')"
              class="text-xs text-purple-500 transition-colors hover:text-purple-600"
              @click="showCategoryForm = true"
            >
              +新建
            </button>
          </div>
          <button
            class="mb-0.5 w-full rounded-md px-3 py-1.5 text-left text-xs font-medium transition-colors"
            :class="!selectedCategory ? 'bg-purple-50 text-purple-700' : 'text-slate-500 hover:bg-slate-50'"
            @click="selectedCategory = null"
          >
            全部 ({{ servers.length }})
          </button>
          <div
            v-for="cat in categoriesWithCount"
            :key="cat.id"
            class="group mb-0.5 flex items-center justify-between rounded-md px-3 py-1.5 text-xs font-medium transition-colors"
            :class="selectedCategory === cat.name ? 'bg-purple-50 text-purple-700' : 'text-slate-500 hover:bg-slate-50'"
          >
            <button class="flex-1 text-left" @click="selectedCategory = cat.name">
              {{ cat.name }} ({{ cat.count }})
            </button>
            <button
              v-if="hasPermission('mcp:delete')"
              class="hidden text-red-400 hover:text-red-600 group-hover:block"
              @click="deleteCategoryTarget = cat"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Server 列表 -->
        <div class="overflow-y-auto p-2" style="max-height: calc(100vh - 14rem)">
          <div v-if="loading" class="py-8 text-center text-sm text-slate-400">加载中...</div>
          <div v-else-if="filteredServers.length === 0" class="py-8 text-center text-sm text-slate-400">
            暂无 MCP Server
          </div>
          <div
            v-for="server in filteredServers"
            :key="server.id"
            class="mb-1 flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 transition-colors"
            :class="selectedServer?.id === server.id ? 'bg-purple-50 ring-1 ring-purple-200' : 'hover:bg-slate-50'"
            @click="selectedServer = server"
          >
            <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100">
              <CheckCircle2 v-if="server.status === 'healthy'" class="h-5 w-5 text-green-600" />
              <XCircle v-else-if="server.status === 'unhealthy'" class="h-5 w-5 text-red-600" />
              <HelpCircle v-else class="h-5 w-5 text-slate-400" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span
                  class="truncate text-sm font-medium"
                  :class="selectedServer?.id === server.id ? 'text-purple-700' : 'text-slate-900'"
                >
                  {{ server.name }}
                </span>
              </div>
              <div class="mt-0.5 flex items-center gap-1.5">
                <span class="rounded bg-blue-50 px-1 py-0.5 text-[10px] text-blue-600">
                  {{ transportLabels[server.transport] || server.transport }}
                </span>
                <span
                  v-if="server.is_published"
                  class="rounded bg-green-50 px-1 py-0.5 text-[10px] text-green-600"
                >
                  已发布
                </span>
                <span
                  v-if="server.requires_approval"
                  class="rounded bg-amber-50 px-1 py-0.5 text-[10px] text-amber-600"
                >
                  需审批
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：详情 + 工具管理 -->
      <div
        class="flex-1 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl"
      >
        <template v-if="selectedServer">
          <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
            <div class="flex items-center gap-3">
              <h3 class="text-sm font-semibold text-slate-900">{{ selectedServer.name }}</h3>
              <span class="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">
                {{ selectedServer.server_name }}
              </span>
              <span class="rounded px-1.5 py-0.5 text-xs" :class="statusBgClass(selectedServer.status)">
                {{ statusLabel(selectedServer.status) }}
              </span>
              <span
                v-if="!selectedServer.litellm_synced"
                class="rounded bg-amber-50 px-1.5 py-0.5 text-xs text-amber-600"
                :title="selectedServer.litellm_sync_error || ''"
              >
                未同步
              </span>
            </div>
            <div class="flex gap-1.5">
              <button
                class="flex items-center gap-1 rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium transition-colors hover:bg-slate-200"
                :class="healthIconColor(selectedServer.status)"
                @click="handleHealthCheck"
              >
                <Activity v-if="checkingId !== selectedServer.id" class="h-3 w-3" />
                <RefreshCw v-else class="h-3 w-3 animate-spin" />
                健康检查
              </button>
              <button
                v-if="hasPermission('mcp:update')"
                class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200"
                @click="openEdit"
              >
                编辑
              </button>
              <button
                v-if="hasPermission('mcp:delete')"
                class="rounded-md bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-100"
                @click="deleteTarget = selectedServer"
              >
                删除
              </button>
            </div>
          </div>
          <div class="overflow-y-auto p-4" style="max-height: calc(100vh - 10rem)">
            <!-- 基本信息 -->
            <div class="mb-4 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              <div class="col-span-2">
                <span class="text-slate-500">URL：</span>
                <span class="font-mono text-slate-700">{{ selectedServer.url }}</span>
              </div>
              <div>
                <span class="text-slate-500">传输方式：</span>
                <span class="text-slate-700">{{ transportLabels[selectedServer.transport] || selectedServer.transport }}</span>
              </div>
              <div>
                <span class="text-slate-500">认证方式：</span>
                <span class="text-slate-700">{{ selectedServer.auth_type === 'none' ? '无' : selectedServer.auth_type }}</span>
              </div>
              <div v-if="selectedServer.auth_type !== 'none'" class="col-span-2">
                <span class="text-slate-500">认证值：</span>
                <span class="font-mono text-slate-700">
                  {{ showAuthValue ? (selectedServer.credentials?.auth_value || '-') : '••••••••' }}
                </span>
                <button class="ml-1 text-slate-400 hover:text-slate-600" @click="showAuthValue = !showAuthValue">
                  <component :is="showAuthValue ? EyeOffIcon : EyeIcon" class="inline h-3.5 w-3.5" />
                </button>
              </div>
              <div>
                <span class="text-slate-500">分类：</span>
                <span class="text-slate-700">{{ selectedServer.category }}</span>
              </div>
              <div>
                <span class="text-slate-500">计费方式：</span>
                <span class="text-slate-700">
                  {{ selectedServer.billing_type === 'free' ? '免费' : '按次计费' }}
                </span>
              </div>
              <div v-if="selectedServer.billing_type !== 'free'">
                <span class="text-slate-500">单价（内/外）：</span>
                <span class="text-slate-700">
                  ¥{{ selectedServer.internal_cost_per_call }} /
                  ¥{{ selectedServer.external_cost_per_call }}
                </span>
              </div>
              <div>
                <span class="text-slate-500">发布：</span>
                <span class="text-slate-700">{{ selectedServer.is_published ? '已发布' : '未发布' }}</span>
              </div>
              <div>
                <span class="text-slate-500">领用方式：</span>
                <span class="text-slate-700">
                  {{ selectedServer.requires_approval ? '需审批' : '直接领用' }}
                </span>
              </div>
              <div v-if="selectedServer.description" class="col-span-2">
                <span class="text-slate-500">描述：</span>
                <span class="text-slate-700">{{ selectedServer.description }}</span>
              </div>
            </div>

            <!-- 工具列表 -->
            <McpToolPanel
              :server-id="selectedServer.id"
              :server-billing-type="selectedServer.billing_type"
            />
          </div>
        </template>
        <template v-else>
          <div class="flex h-full items-center justify-center text-sm text-slate-400">
            请从左侧选择 MCP Server 查看详情
          </div>
        </template>
      </div>
    </div>

    <!-- Server form dialog -->
    <McpServerForm
      :visible="showForm"
      :editing="editingServer"
      :categories="categories"
      @close="showForm = false"
      @saved="handleSaved"
    />

    <!-- Delete server confirm -->
    <ConfirmDialog
      :visible="!!deleteTarget"
      title="删除 MCP Server"
      :message="`确认删除 ${deleteTarget?.name}？此操作不可恢复。`"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />

    <!-- Delete category confirm -->
    <ConfirmDialog
      :visible="!!deleteCategoryTarget"
      title="删除分类"
      :message="`确认删除分类 ${deleteCategoryTarget?.name}？该分类下的 Server 不会被删除，但需要重新设置分类。`"
      @confirm="confirmDeleteCategory"
      @cancel="deleteCategoryTarget = null"
    />

    <!-- 新建分类 -->
    <div
      v-if="showCategoryForm"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
    >
      <div class="w-full max-w-sm rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">新建分类</h3>
        <div class="mb-3">
          <label class="mb-1 block text-sm font-medium text-slate-700">名称</label>
          <input
            v-model="categoryFormName"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            placeholder="如：search / data / code"
          />
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-slate-700">描述（可选）</label>
          <input
            v-model="categoryFormDescription"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div class="flex justify-end gap-3">
          <button
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            @click="showCategoryForm = false"
          >
            取消
          </button>
          <button
            class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
            @click="handleCreateCategory"
          >
            创建
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
