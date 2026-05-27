<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  createMcpServer,
  updateMcpServer,
  type McpServer,
  type McpCategory,
  type CreateMcpServerParams,
} from '@aihelms/shared'
import { toast } from '@aihelms/shared'
import IconPicker from '../../components/IconPicker.vue'

interface Props {
  visible: boolean
  editing: McpServer | null
  categories: McpCategory[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  saved: []
}>()

const form = ref({
  name: '',
  server_name: '',
  url: '',
  transport: 'sse',
  auth_type: 'none',
  auth_value: '',
  description: '',
  instructions: '',
  category: 'general',
  billing_type: 'per_call',
  internal_cost_per_call: 0,
  external_cost_per_call: 0,
  icon_url: '',
  documentation_url: '',
  is_published: false,
  requires_approval: false,
})

const error = ref('')
const saving = ref(false)
const serverNameError = ref('')

function validateServerName() {
  if (form.value.server_name.includes('-')) {
    serverNameError.value = '唯一标识不能包含横杠（-），请使用下划线（_）替代'
  } else {
    serverNameError.value = ''
  }
}

watch(
  () => props.visible,
  (v) => {
    if (v) {
      error.value = ''
      if (props.editing) {
        const s = props.editing
        form.value = {
          name: s.name,
          server_name: s.server_name,
          url: s.url,
          transport: s.transport,
          auth_type: s.auth_type,
          auth_value: '',
          description: s.description,
          instructions: s.instructions,
          category: s.category,
          billing_type: s.billing_type,
          internal_cost_per_call: s.internal_cost_per_call,
          external_cost_per_call: s.external_cost_per_call,
          icon_url: s.icon_url,
          documentation_url: s.documentation_url,
          is_published: s.is_published,
          requires_approval: s.requires_approval,
        }
      } else {
        form.value = {
          name: '',
          server_name: '',
          url: '',
          transport: 'sse',
          auth_type: 'none',
          auth_value: '',
          description: '',
          instructions: '',
          category: 'general',
          billing_type: 'per_call',
          internal_cost_per_call: 0,
          external_cost_per_call: 0,
          icon_url: '',
          documentation_url: '',
          is_published: false,
          requires_approval: false,
        }
      }
    }
  },
)

async function handleSubmit(): Promise<void> {
  error.value = ''
  if (!form.value.name || !form.value.server_name || !form.value.url) {
    error.value = '请填写所有必填项'
    return
  }
  if (form.value.server_name.includes('-')) {
    error.value = '唯一标识不能包含横杠（-），请使用下划线（_）替代'
    return
  }
  saving.value = true
  try {
    const credentials: Record<string, unknown> = {}
    if (form.value.auth_type !== 'none' && form.value.auth_value) {
      credentials.auth_value = form.value.auth_value
    }
    const payload: CreateMcpServerParams = {
      name: form.value.name,
      server_name: form.value.server_name,
      url: form.value.url,
      transport: form.value.transport,
      auth_type: form.value.auth_type,
      credentials: form.value.auth_type !== 'none' ? credentials : undefined,
      description: form.value.description,
      instructions: form.value.instructions,
      category: form.value.category,
      billing_type: form.value.billing_type,
      internal_cost_per_call: Number(form.value.internal_cost_per_call),
      external_cost_per_call: Number(form.value.external_cost_per_call),
      icon_url: form.value.icon_url,
      documentation_url: form.value.documentation_url,
      is_published: form.value.is_published,
      requires_approval: form.value.requires_approval,
    }
    if (props.editing) {
      await updateMcpServer(props.editing.id, payload)
      toast.success('MCP Server 更新成功')
    } else {
      await createMcpServer(payload)
      toast.success('MCP Server 创建成功')
    }
    emit('saved')
  } catch (e) {
    const msg = (e as { message?: string }).message || '保存失败'
    error.value = msg
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
  >
    <div
      class="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl"
    >
      <h3 class="mb-4 text-lg font-semibold text-slate-900">
        {{ editing ? '编辑 MCP Server' : '新建 MCP Server' }}
      </h3>

      <div v-if="error" class="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
        {{ error }}
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">名称 *</label>
          <input
            v-model="form.name"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div>
          <IconPicker v-model="form.icon_url" label="图标" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">唯一标识 *</label>
          <input
            v-model="form.server_name"
            :disabled="!!editing"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none disabled:bg-slate-50"
            :class="{ 'border-red-300': serverNameError }"
            @input="validateServerName"
          />
          <p v-if="serverNameError" class="mt-1 text-xs text-red-500">{{ serverNameError }}</p>
          <p v-else class="mt-1 text-xs text-slate-400">仅支持字母、数字和下划线，不能包含横杠（-）</p>
        </div>
        <div class="col-span-2">
          <label class="mb-1 block text-sm font-medium text-slate-700">URL *</label>
          <input
            v-model="form.url"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            placeholder="https://example.com/mcp/sse"
          />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">传输方式</label>
          <select
            v-model="form.transport"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          >
            <option value="sse">SSE</option>
            <option value="streamableHttp">Streamable HTTP</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">认证方式</label>
          <select
            v-model="form.auth_type"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          >
            <option value="none">无</option>
            <option value="api_key">API Key</option>
            <option value="bearer_token">Bearer Token</option>
            <option value="basic">Basic</option>
          </select>
        </div>
        <div v-if="form.auth_type !== 'none'" class="col-span-2">
          <label class="mb-1 block text-sm font-medium text-slate-700">认证值</label>
          <input
            v-model="form.auth_value"
            type="password"
            placeholder="留空则保留原值"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">分类</label>
          <select
            v-model="form.category"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          >
            <option v-for="cat in categories" :key="cat.id" :value="cat.name">{{ cat.name }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700">计费方式</label>
          <select
            v-model="form.billing_type"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          >
            <option value="per_call">按次计费</option>
            <option value="free">免费</option>
          </select>
        </div>
        <div v-if="form.billing_type !== 'free'">
          <label class="mb-1 block text-sm font-medium text-slate-700">内部单价（每次）</label>
          <input
            v-model.number="form.internal_cost_per_call"
            type="number"
            step="0.000001"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div v-if="form.billing_type !== 'free'">
          <label class="mb-1 block text-sm font-medium text-slate-700">外部单价（每次）</label>
          <input
            v-model.number="form.external_cost_per_call"
            type="number"
            step="0.000001"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div class="col-span-2">
          <label class="mb-1 block text-sm font-medium text-slate-700">描述</label>
          <textarea
            v-model="form.description"
            rows="2"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div class="col-span-2">
          <label class="mb-1 block text-sm font-medium text-slate-700">使用说明</label>
          <textarea
            v-model="form.instructions"
            rows="3"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div class="col-span-2 flex items-center gap-4">
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input
              v-model="form.is_published"
              type="checkbox"
              class="h-4 w-4 rounded border-slate-300"
            />
            发布到用户端
          </label>
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input
              v-model="form.requires_approval"
              type="checkbox"
              :disabled="!form.is_published"
              class="h-4 w-4 rounded border-slate-300 disabled:opacity-50"
            />
            领用前需要审批
          </label>
        </div>
      </div>

      <div class="mt-6 flex justify-end gap-3">
        <button
          class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
          :disabled="saving"
          @click="emit('close')"
        >
          取消
        </button>
        <button
          class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-purple-700 disabled:opacity-50"
          :disabled="saving"
          @click="handleSubmit"
        >
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>
  </div>
</template>
