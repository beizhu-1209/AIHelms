<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  getMcpTools,
  refreshMcpTools,
  updateToolBilling,
  type McpTool,
} from '@aihelms/shared'
import { toast } from '@aihelms/shared'
import { RefreshCw, Settings, ChevronDown, ChevronRight } from 'lucide-vue-next'

interface Props {
  serverId: number | null
  serverBillingType: string
}

const props = defineProps<Props>()

const tools = ref<McpTool[]>([])
const loading = ref(false)
const refreshing = ref(false)
const editingTool = ref<McpTool | null>(null)
const expandedTools = ref<Set<number>>(new Set())
const billingForm = ref({
  billing_type: 'per_call',
  internal_cost_per_call: 0,
  external_cost_per_call: 0,
  override: false,
})

const serverBillingFree = computed(() => props.serverBillingType === 'free')

watch(
  () => props.serverId,
  (v) => {
    if (v) loadTools()
    else tools.value = []
  },
  { immediate: true },
)

async function loadTools(): Promise<void> {
  if (!props.serverId) return
  loading.value = true
  try {
    tools.value = await getMcpTools(props.serverId)
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载工具失败')
  } finally {
    loading.value = false
  }
}

async function handleRefresh(): Promise<void> {
  if (!props.serverId) return
  refreshing.value = true
  try {
    tools.value = await refreshMcpTools(props.serverId)
    toast.success(`已同步 ${tools.value.length} 个工具`)
  } catch (e) {
    toast.error((e as { message?: string }).message || '同步失败')
  } finally {
    refreshing.value = false
  }
}

function toggleExpand(toolId: number): void {
  if (expandedTools.value.has(toolId)) {
    expandedTools.value.delete(toolId)
  } else {
    expandedTools.value.add(toolId)
  }
}

function openBillingDialog(tool: McpTool): void {
  editingTool.value = tool
  billingForm.value = {
    billing_type: tool.billing_type || 'per_call',
    internal_cost_per_call: Number(tool.internal_cost_per_call ?? 0),
    external_cost_per_call: Number(tool.external_cost_per_call ?? 0),
    override: tool.billing_type !== null,
  }
}

async function saveBilling(): Promise<void> {
  if (!editingTool.value) return
  try {
    if (billingForm.value.override) {
      await updateToolBilling(editingTool.value.id, {
        billing_type: billingForm.value.billing_type,
        internal_cost_per_call: billingForm.value.internal_cost_per_call,
        external_cost_per_call: billingForm.value.external_cost_per_call,
      })
    } else {
      await updateToolBilling(editingTool.value.id, {
        billing_type: undefined,
        internal_cost_per_call: undefined,
        external_cost_per_call: undefined,
      })
    }
    toast.success('计费配置已保存')
    editingTool.value = null
    await loadTools()
  } catch (e) {
    toast.error((e as { message?: string }).message || '保存失败')
  }
}

function effectiveBilling(tool: McpTool): { type: string; internal: number; external: number; inherited: boolean } {
  if (tool.billing_type) {
    return {
      type: tool.billing_type,
      internal: Number(tool.internal_cost_per_call ?? 0),
      external: Number(tool.external_cost_per_call ?? 0),
      inherited: false,
    }
  }
  return {
    type: props.serverBillingType,
    internal: 0,
    external: 0,
    inherited: true,
  }
}
</script>

<template>
  <div>
    <div class="mb-3 flex items-center justify-between">
      <h3 class="text-sm font-semibold text-slate-900">工具列表（{{ tools.length }}）</h3>
      <button
        class="flex items-center gap-1.5 rounded-md bg-purple-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-purple-500 disabled:opacity-50"
        :disabled="refreshing || !serverId"
        @click="handleRefresh"
      >
        <RefreshCw class="h-3 w-3" :class="refreshing ? 'animate-spin' : ''" />
        {{ refreshing ? '同步中...' : '同步工具' }}
      </button>
    </div>

    <div v-if="loading" class="py-8 text-center text-sm text-slate-500">加载中...</div>
    <div v-else-if="tools.length === 0" class="py-8 text-center text-sm text-slate-500">
      暂无工具，点击「同步工具」获取
    </div>
    <div v-else class="space-y-2">
      <div
        v-for="tool in tools"
        :key="tool.id"
        class="overflow-hidden rounded-lg border border-slate-200 bg-white"
      >
        <!-- 行头 -->
        <div class="flex items-center gap-3 px-3 py-2.5">
          <button
            class="shrink-0 rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            @click="toggleExpand(tool.id)"
          >
            <ChevronDown v-if="expandedTools.has(tool.id)" class="h-4 w-4" />
            <ChevronRight v-else class="h-4 w-4" />
          </button>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="font-mono text-sm font-medium text-slate-900">{{ tool.tool_name }}</span>
              <span
                v-if="tool.billing_type"
                class="rounded bg-purple-50 px-1.5 py-0.5 text-[10px] text-purple-700"
              >
                独立计费
              </span>
              <span v-else class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                继承 Server
              </span>
            </div>
            <p class="mt-0.5 truncate text-xs text-slate-500">
              {{ tool.description || '无描述' }}
            </p>
          </div>
          <div class="shrink-0 text-right text-xs">
            <template v-if="effectiveBilling(tool).type === 'free'">
              <span class="text-green-600">免费</span>
            </template>
            <template v-else>
              <span class="text-slate-700">
                ¥{{ effectiveBilling(tool).internal }} / ¥{{ effectiveBilling(tool).external }}
              </span>
              <span class="ml-1 text-[10px] text-slate-400">内/外</span>
            </template>
          </div>
          <button
            class="shrink-0 rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            title="计费配置"
            @click="openBillingDialog(tool)"
          >
            <Settings class="h-3.5 w-3.5" />
          </button>
        </div>

        <!-- 展开详情 -->
        <div v-if="expandedTools.has(tool.id)" class="border-t border-slate-100 bg-slate-50 px-3 py-2.5">
          <div class="mb-2">
            <span class="text-xs font-medium text-slate-600">说明：</span>
            <p class="mt-1 whitespace-pre-wrap text-xs text-slate-700">
              {{ tool.description || '该工具没有提供说明' }}
            </p>
          </div>
          <div v-if="tool.input_schema && Object.keys(tool.input_schema).length > 0">
            <span class="text-xs font-medium text-slate-600">参数 Schema：</span>
            <pre class="mt-1 max-h-40 overflow-auto rounded bg-white p-2 text-[10px] text-slate-700">{{ JSON.stringify(tool.input_schema, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- Tool billing dialog -->
    <div
      v-if="editingTool"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
    >
      <div
        class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl"
      >
        <h3 class="mb-4 text-lg font-semibold text-slate-900">
          {{ editingTool.tool_name }} - 计费配置
        </h3>

        <div class="mb-4 flex items-center gap-2">
          <input
            id="override"
            v-model="billingForm.override"
            type="checkbox"
            class="h-4 w-4 rounded border-slate-300"
          />
          <label for="override" class="text-sm text-slate-700">
            为此工具配置独立计费（不勾选则继承 Server 级配置：{{ serverBillingFree ? '免费' : '按次计费' }}）
          </label>
        </div>

        <div v-if="billingForm.override" class="space-y-3">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">计费方式</label>
            <select
              v-model="billingForm.billing_type"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            >
              <option value="per_call">按次计费</option>
              <option value="free">免费</option>
            </select>
          </div>
          <div v-if="billingForm.billing_type !== 'free'">
            <label class="mb-1 block text-sm font-medium text-slate-700">内部单价（每次）</label>
            <input
              v-model.number="billingForm.internal_cost_per_call"
              type="number"
              step="0.000001"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div v-if="billingForm.billing_type !== 'free'">
            <label class="mb-1 block text-sm font-medium text-slate-700">外部单价（每次）</label>
            <input
              v-model.number="billingForm.external_cost_per_call"
              type="number"
              step="0.000001"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <button
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
            @click="editingTool = null"
          >
            取消
          </button>
          <button
            class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-purple-700"
            @click="saveBilling"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
