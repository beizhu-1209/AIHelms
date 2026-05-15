<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center">
    <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="handleClose" />
    <div class="relative w-[720px] max-h-[85vh] overflow-y-auto bg-white/90 backdrop-blur-xl border border-slate-200/60 rounded-2xl shadow-xl p-6">
      <h2 class="text-lg font-semibold text-slate-800 mb-5">{{ isEdit ? '编辑 Key' : '创建 Key' }}</h2>

      <!-- Key Type -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-700 mb-1">Key 类型</label>
        <select v-model="form.key_type" :disabled="isEdit" class="w-full px-3 py-2 rounded-lg border border-slate-200/60 bg-white/80 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50">
          <option value="personal_main">个人主 Key</option>
          <option value="personal_scene">个人场景 Key</option>
          <option value="dept_main">部门主 Key</option>
          <option value="dept_scene">部门场景 Key</option>
          <option value="project_main">项目主 Key</option>
          <option value="project_scene">项目场景 Key</option>
        </select>
      </div>

      <!-- Scenario -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-700 mb-1">场景（可选）</label>
        <select v-model="form.scenario_id" class="w-full px-3 py-2 rounded-lg border border-slate-200/60 bg-white/80 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50">
          <option :value="null">不选择场景</option>
          <option v-for="s in scenarios" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>

      <!-- Key Name -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-700 mb-1">Key 名称</label>
        <input v-model="form.name" type="text" placeholder="支持模板变量: {username}, {display_name}" class="w-full px-3 py-2 rounded-lg border border-slate-200/60 bg-white/80 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50" />
        <p v-if="isBatchMode" class="mt-1 text-xs text-slate-400">批量创建时可用 {username}、{display_name} 自动替换</p>
      </div>

      <!-- Description -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-700 mb-1">描述</label>
        <input v-model="form.description" type="text" placeholder="Key 用途描述" class="w-full px-3 py-2 rounded-lg border border-slate-200/60 bg-white/80 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50" />
      </div>

      <!-- Owner Selection -->
      <div v-if="!isEdit" class="mb-4">
        <label class="block text-sm font-medium text-slate-700 mb-1">归属</label>
        <div v-if="ownerType === 'user'">
          <button type="button" class="px-4 py-2 rounded-lg border border-slate-200/60 bg-white/80 text-sm hover:bg-slate-50 transition" @click="showUserPicker = true">
            选择用户 <span v-if="selectedUsers.length" class="ml-1 text-purple-600">({{ selectedUsers.length }}人)</span>
          </button>
          <div v-if="selectedUsers.length" class="mt-2 flex flex-wrap gap-1">
            <span v-for="u in selectedUsers" :key="u.id" class="inline-flex items-center px-2 py-0.5 rounded bg-purple-50 text-xs text-purple-700">
              {{ u.display_name || u.username }}
              <button class="ml-1 text-purple-400 hover:text-purple-600" @click="removeUser(u.id)">&times;</button>
            </span>
          </div>
        </div>
        <p v-else class="text-sm text-slate-500">已指定归属（{{ ownerType === 'department' ? '部门' : '项目' }}）</p>
      </div>

      <!-- Model Selection -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-700 mb-1">可用模型</label>
        <div class="border border-slate-200/60 rounded-lg bg-white/80 p-3 max-h-48 overflow-y-auto">
          <input v-model="modelSearch" type="text" placeholder="搜索模型..." class="w-full px-2 py-1.5 mb-2 rounded border border-slate-200/60 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50" />
          <label class="flex items-center gap-2 mb-2 text-sm text-slate-600 cursor-pointer">
            <input type="checkbox" :checked="allModelsSelected" class="rounded text-purple-600" @change="toggleAllModels" /> 全选
          </label>
          <div v-for="m in filteredModels" :key="m.id" class="flex items-center gap-2 py-0.5">
            <input type="checkbox" :value="m.model_id" v-model="form.models" class="rounded text-purple-600" />
            <span class="text-sm text-slate-700">{{ m.name }}</span>
            <span class="text-xs text-slate-400">{{ m.model_id }}</span>
          </div>
        </div>
      </div>

      <!-- Budget Section -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-700 mb-1">预算设置</label>
        <div class="border border-slate-200/60 rounded-lg bg-white/80 p-3 space-y-3">
          <div class="flex items-center gap-3">
            <select v-model="form.budget_duration" class="px-3 py-1.5 rounded-lg border border-slate-200/60 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50">
              <option value="30d">月 (30天)</option>
              <option value="7d">周 (7天)</option>
              <option value="1d">日 (1天)</option>
            </select>
            <div class="flex">
              <button type="button" :class="[!perModelBudget ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600', 'px-3 py-1 rounded-l-lg text-sm transition']" @click="perModelBudget = false">统一预算</button>
              <button type="button" :class="[perModelBudget ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600', 'px-3 py-1 rounded-r-lg text-sm transition']" @click="perModelBudget = true">按模型预算</button>
            </div>
          </div>
          <div v-if="!perModelBudget" class="flex items-center gap-2">
            <span class="text-sm text-slate-600">¥</span>
            <input v-model.number="form.budget_limit" type="number" min="0" placeholder="预算金额" class="w-40 px-3 py-1.5 rounded-lg border border-slate-200/60 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50" />
          </div>
          <div v-else class="space-y-2">
            <div v-for="mid in form.models" :key="mid" class="flex items-center gap-2">
              <span class="text-sm text-slate-700 w-40 truncate">{{ getModelName(mid) }}</span>
              <span class="text-sm text-slate-600">¥</span>
              <input v-model.number="modelBudgets[mid]" type="number" min="0" placeholder="0" class="w-28 px-2 py-1 rounded border border-slate-200/60 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50" />
            </div>
          </div>
          <label class="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input type="checkbox" v-model="form.budget_hard_limit" class="rounded text-purple-600" /> 超出预算立刻禁止使用
          </label>
        </div>
      </div>

      <!-- Rate Limiting -->
      <div class="mb-5">
        <div class="flex items-center gap-2 mb-2">
          <label class="text-sm font-medium text-slate-700">速率限制</label>
          <button type="button" :class="[rateLimitEnabled ? 'bg-purple-600' : 'bg-slate-300', 'relative w-9 h-5 rounded-full transition']" @click="rateLimitEnabled = !rateLimitEnabled">
            <span :class="[rateLimitEnabled ? 'translate-x-4' : 'translate-x-0.5', 'absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform']" />
          </button>
        </div>
        <div v-if="rateLimitEnabled && form.models.length" class="border border-slate-200/60 rounded-lg bg-white/80 p-3 overflow-x-auto">
          <table class="w-full text-sm">
            <thead><tr class="text-slate-500 text-left">
              <th class="pb-2">模型</th><th class="pb-2 px-2">TPM</th><th class="pb-2 px-2">RPM</th><th class="pb-2 px-2">MaxTokens</th>
            </tr></thead>
            <tbody>
              <tr v-for="mid in form.models" :key="mid">
                <td class="py-1 text-slate-700 truncate max-w-[160px]">{{ getModelName(mid) }}</td>
                <td class="py-1 px-2"><input v-model.number="rateLimits[mid].tpm" type="number" min="0" class="w-24 px-2 py-1 rounded border border-slate-200/60 text-sm" /></td>
                <td class="py-1 px-2"><input v-model.number="rateLimits[mid].rpm" type="number" min="0" class="w-24 px-2 py-1 rounded border border-slate-200/60 text-sm" /></td>
                <td class="py-1 px-2"><input v-model.number="rateLimits[mid].max_tokens" type="number" min="0" class="w-24 px-2 py-1 rounded border border-slate-200/60 text-sm" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex justify-end gap-3">
        <button type="button" class="px-4 py-2 rounded-lg border border-slate-200/60 text-sm text-slate-600 hover:bg-slate-50 transition" @click="handleClose">取消</button>
        <button type="button" :disabled="submitting" class="px-5 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-sm font-medium shadow hover:shadow-lg transition disabled:opacity-50" @click="handleSubmit">
          {{ submitting ? '提交中...' : (isEdit ? '保存' : '创建') }}
        </button>
      </div>

      <!-- Result: single key -->
      <div v-if="createdKeyValue" class="mt-4 p-3 rounded-lg bg-green-50 border border-green-200">
        <p class="text-sm text-green-800 font-medium mb-1">Key 创建成功</p>
        <div class="flex items-center gap-2">
          <code class="flex-1 text-xs bg-white px-2 py-1 rounded border border-green-200 break-all">{{ createdKeyValue }}</code>
          <button class="px-2 py-1 text-xs rounded bg-green-600 text-white hover:bg-green-700 transition" @click="copyKey">复制</button>
        </div>
      </div>

      <!-- Result: batch -->
      <div v-if="batchResults" class="mt-4 p-3 rounded-lg bg-blue-50 border border-blue-200">
        <p class="text-sm text-blue-800 font-medium mb-1">批量创建完成：成功 {{ batchSuccessCount }} / 失败 {{ batchFailCount }}</p>
        <div v-if="batchFailures.length" class="mt-1 text-xs text-red-600">
          <p v-for="(f, i) in batchFailures" :key="i">用户ID {{ f.user_id }}: {{ f.error }}</p>
        </div>
      </div>
    </div>

    <!-- User Transfer Picker -->
    <div v-if="showUserPicker" class="fixed inset-0 z-[60] flex items-center justify-center">
      <div class="absolute inset-0 bg-black/30" @click="showUserPicker = false" />
      <div class="relative w-[600px] max-h-[70vh] bg-white/95 backdrop-blur-xl border border-slate-200/60 rounded-2xl shadow-xl p-5">
        <h3 class="text-sm font-semibold text-slate-800 mb-3">选择用户</h3>
        <div class="grid grid-cols-2 gap-4">
          <div class="border border-slate-200/60 rounded-lg p-3">
            <input v-model="userSearch" type="text" placeholder="搜索用户..." class="w-full px-2 py-1.5 mb-2 rounded border border-slate-200/60 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50" />
            <button class="text-xs text-purple-600 mb-2 hover:underline" @click="selectAllVisible">全选</button>
            <div class="max-h-52 overflow-y-auto space-y-1">
              <div v-for="u in availableUsers" :key="u.id" class="flex items-center gap-2 px-2 py-1 rounded hover:bg-slate-50 cursor-pointer" @click="addUser(u)">
                <span class="text-sm text-slate-700">{{ u.display_name || u.username }}</span>
                <span class="text-xs text-slate-400">{{ u.username }}</span>
              </div>
            </div>
          </div>
          <div class="border border-slate-200/60 rounded-lg p-3">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-slate-500">已选 {{ selectedUsers.length }} 人</span>
              <button class="text-xs text-red-500 hover:underline" @click="selectedUsers = []">清空</button>
            </div>
            <div class="max-h-52 overflow-y-auto space-y-1">
              <div v-for="u in selectedUsers" :key="u.id" class="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-50">
                <span class="text-sm text-slate-700">{{ u.display_name || u.username }}</span>
                <button class="text-xs text-red-400 hover:text-red-600" @click="removeUser(u.id)">&times;</button>
              </div>
            </div>
          </div>
        </div>
        <div class="flex justify-end mt-4">
          <button class="px-4 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-sm font-medium shadow transition" @click="showUserPicker = false">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import {
  createAiKey,
  batchCreateAiKeys,
  updateAiKey,
  getActiveModels,
  getUsers,
  getAllKeyScenarios,
  setModelLimits,
  getModelLimits,
} from '@aihelms/shared'
import type {
  AiKey,
  ActiveModel,
  KeyScenario,
  BatchCreateResult,
  RateLimitItem,
  SetModelLimitItem,
} from '@aihelms/shared'

interface Props {
  visible: boolean
  editKey?: AiKey | null
  defaultOwnerType?: 'user' | 'department' | 'project'
  defaultOwnerId?: number
}

const props = withDefaults(defineProps<Props>(), {
  editKey: null,
  defaultOwnerType: 'user',
  defaultOwnerId: undefined,
})

const emit = defineEmits<{ close: []; saved: [] }>()

interface UserItem { id: number; username: string; display_name: string }
interface RateLimitEntry { tpm: number | null; rpm: number | null; max_tokens: number | null }

const isEdit = computed(() => !!props.editKey)
const ownerType = computed(() => props.editKey?.owner_type ?? props.defaultOwnerType ?? 'user')
const isBatchMode = computed(() => !isEdit.value && ownerType.value === 'user' && selectedUsers.value.length > 1)

const form = reactive({
  key_type: 'personal_main' as string,
  scenario_id: null as number | null,
  name: '',
  description: '',
  models: [] as string[],
  budget_duration: '30d',
  budget_limit: null as number | null,
  budget_hard_limit: false,
})

const scenarios = ref<KeyScenario[]>([])
const models = ref<ActiveModel[]>([])
const allUsers = ref<UserItem[]>([])
const selectedUsers = ref<UserItem[]>([])
const modelSearch = ref('')
const userSearch = ref('')
const showUserPicker = ref(false)
const perModelBudget = ref(false)
const modelBudgets = reactive<Record<string, number | null>>({})
const rateLimitEnabled = ref(false)
const rateLimits = reactive<Record<string, RateLimitEntry>>({})
const submitting = ref(false)
const createdKeyValue = ref('')
const batchResults = ref<BatchCreateResult[] | null>(null)

const batchSuccessCount = computed(() => batchResults.value?.filter(r => r.success).length ?? 0)
const batchFailCount = computed(() => batchResults.value?.filter(r => !r.success).length ?? 0)
const batchFailures = computed(() => batchResults.value?.filter(r => !r.success) ?? [])

const filteredModels = computed(() => {
  const q = modelSearch.value.toLowerCase()
  if (!q) return models.value
  return models.value.filter(m => m.name.toLowerCase().includes(q) || m.model_id.toLowerCase().includes(q))
})

const allModelsSelected = computed(() => form.models.length === models.value.length && models.value.length > 0)

const availableUsers = computed(() => {
  const selectedIds = new Set(selectedUsers.value.map(u => u.id))
  const q = userSearch.value.toLowerCase()
  return allUsers.value.filter(u => {
    if (selectedIds.has(u.id)) return false
    if (!q) return true
    return u.username.toLowerCase().includes(q) || u.display_name?.toLowerCase().includes(q)
  })
})

function getModelName(modelId: string): string {
  return models.value.find(m => m.model_id === modelId)?.name ?? modelId
}

function getModelDbId(modelId: string): number | undefined {
  return models.value.find(m => m.model_id === modelId)?.id
}

function toggleAllModels() {
  form.models = allModelsSelected.value ? [] : models.value.map(m => m.model_id)
}

function addUser(user: UserItem) {
  if (!selectedUsers.value.find(u => u.id === user.id)) {
    selectedUsers.value.push(user)
  }
}

function removeUser(id: number) {
  selectedUsers.value = selectedUsers.value.filter(u => u.id !== id)
}

function selectAllVisible() {
  for (const u of availableUsers.value) {
    if (!selectedUsers.value.find(s => s.id === u.id)) selectedUsers.value.push(u)
  }
}

function handleClose() {
  createdKeyValue.value = ''
  batchResults.value = null
  emit('close')
}

function copyKey() {
  navigator.clipboard.writeText(createdKeyValue.value)
}

// Ensure rateLimits entries exist for selected models
watch(() => form.models, (ids) => {
  for (const id of ids) {
    if (!rateLimits[id]) {
      rateLimits[id] = { tpm: null, rpm: null, max_tokens: null }
    }
  }
}, { immediate: true, deep: true })

function buildRateLimits(): RateLimitItem[] | null {
  if (!rateLimitEnabled.value) return null
  const items: RateLimitItem[] = []
  for (const mid of form.models) {
    const dbId = getModelDbId(mid)
    if (!dbId) continue
    const entry = rateLimits[mid]
    if (entry && (entry.tpm || entry.rpm || entry.max_tokens)) {
      items.push({ model_id: dbId, tpm: entry.tpm, rpm: entry.rpm, max_tokens: entry.max_tokens })
    }
  }
  return items.length > 0 ? items : null
}

function buildModelBudgets(): Record<string, number> | null {
  if (!perModelBudget.value) return null
  const result: Record<string, number> = {}
  for (const mid of form.models) {
    const val = modelBudgets[mid]
    if (val && val > 0) result[mid] = val
  }
  return Object.keys(result).length > 0 ? result : null
}

async function handleSubmit() {
  submitting.value = true
  createdKeyValue.value = ''
  batchResults.value = null

  try {
    const budgetLimit = perModelBudget.value ? null : form.budget_limit
    const mBudgets = buildModelBudgets()
    const rLimits = buildRateLimits()

    if (isEdit.value) {
      await updateAiKey(props.editKey!.id, {
        name: form.name,
        description: form.description,
        models: form.models,
        budget_limit: budgetLimit,
        budget_hard_limit: form.budget_hard_limit,
        budget_duration: form.budget_duration,
        model_budgets: mBudgets,
        scenario_id: form.scenario_id,
        rate_limits: rLimits,
      })
      if (rateLimitEnabled.value) {
        const limitItems: SetModelLimitItem[] = []
        for (const mid of form.models) {
          const dbId = getModelDbId(mid)
          if (!dbId) continue
          const entry = rateLimits[mid]
          if (entry) {
            limitItems.push({ model_id: dbId, tpm: entry.tpm, rpm: entry.rpm, max_tokens: entry.max_tokens })
          }
        }
        if (limitItems.length) await setModelLimits(props.editKey!.id, limitItems)
      }
      emit('saved')
    } else if (isBatchMode.value) {
      const res = await batchCreateAiKeys({
        user_ids: selectedUsers.value.map(u => u.id),
        key_type: form.key_type as 'personal_main' | 'personal_scene',
        name_template: form.name,
        description: form.description,
        models: form.models,
        budget_limit: budgetLimit,
        budget_hard_limit: form.budget_hard_limit,
        budget_duration: form.budget_duration,
        model_budgets: mBudgets,
        scenario_id: form.scenario_id,
        rate_limits: rLimits,
      })
      batchResults.value = res
      emit('saved')
    } else {
      const ownerId = ownerType.value === 'user' ? selectedUsers.value[0]?.id : props.defaultOwnerId!
      const res = await createAiKey({
        name: form.name,
        key_type: form.key_type,
        owner_type: ownerType.value,
        owner_id: ownerId,
        description: form.description,
        models: form.models,
        budget_limit: budgetLimit,
        budget_hard_limit: form.budget_hard_limit,
        budget_duration: form.budget_duration,
        model_budgets: mBudgets,
        scenario_id: form.scenario_id,
        rate_limits: rLimits,
      })
      createdKeyValue.value = res.key_value ?? ''
      emit('saved')
    }
  } finally {
    submitting.value = false
  }
}

// Reset form when dialog opens in create mode
watch(() => props.visible, (visible) => {
  if (visible && !props.editKey) {
    const ownerMap: Record<string, string> = {
      user: 'personal_scene',
      department: 'dept_scene',
      project: 'project_scene',
    }
    form.key_type = ownerMap[props.defaultOwnerType ?? 'user'] ?? 'personal_scene'
    form.scenario_id = null
    form.name = ''
    form.description = ''
    form.models = []
    form.budget_duration = '30d'
    form.budget_limit = null
    form.budget_hard_limit = false
    perModelBudget.value = false
    rateLimitEnabled.value = false
    selectedUsers.value = []
    createdKeyValue.value = ''
    batchResults.value = null
  }
})

// Populate form in edit mode
watch(() => props.editKey, async (key) => {
  if (key) {
    form.key_type = key.key_type
    form.scenario_id = key.scenario_id ?? null
    form.name = key.name
    form.description = key.description ?? ''
    form.models = key.models ?? []
    form.budget_duration = key.budget_duration ?? '30d'
    form.budget_limit = key.budget_limit ? parseFloat(key.budget_limit) : null
    form.budget_hard_limit = key.budget_hard_limit
    if (key.model_budgets && Object.keys(key.model_budgets).length > 0) {
      perModelBudget.value = true
      Object.assign(modelBudgets, key.model_budgets)
    }
    // Load existing rate limits
    const limits = await getModelLimits(key.id)
    if (limits.length > 0) {
      rateLimitEnabled.value = true
      for (const l of limits) {
        const mid = l.model_model_id
        rateLimits[mid] = { tpm: l.tpm, rpm: l.rpm, max_tokens: l.max_tokens }
      }
    }
  }
}, { immediate: true })

onMounted(async () => {
  const [modelsRes, scenariosRes, usersRes] = await Promise.all([
    getActiveModels(),
    getAllKeyScenarios(),
    getUsers(1, 200),
  ])
  models.value = modelsRes
  scenarios.value = scenariosRes
  allUsers.value = usersRes.items.map(u => ({ id: u.id, username: u.username, display_name: u.display_name }))
})
</script>
