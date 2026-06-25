<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  getIdentityList,
  getActiveModels,
  getMcpServers,
  getSkills,
  getAgents,
  batchUpdateResources,
  toast,
  type IdentityUserItem,
  type ActiveModel,
  type McpServer,
  type Skill,
  type Agent,
  type AiKeyRateLimitMode,
  type BudgetScope,
  type BudgetSubScope,
  type RateLimitItem,
} from '@aihelms/shared'
import KeyResourceBudget from './KeyResourceBudget.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  saved: []
}>()

const step = ref(1)
const isSubmitting = ref(false)
const userSearch = ref('')
const userPage = ref(1)
const userTotal = ref(0)
const userItems = ref<IdentityUserItem[]>([])
const selectedUserIds = ref<Set<number>>(new Set())
const isLoadingUsers = ref(false)
const showRateLimitConfirm = ref(false)

// Resource & budget state
const activeModels = ref<ActiveModel[]>([])
const mcpServers = ref<McpServer[]>([])
const skillList = ref<Skill[]>([])
const agentList = ref<Agent[]>([])
const selectedModels = ref<string[]>([])
const selectedMcps = ref<number[]>([])
const selectedSkills = ref<number[]>([])
const selectedAgents = ref<number[]>([])
const budgetDuration = ref('30d')
const budgetScope = ref<BudgetScope>('unified')
const budgetLimit = ref<number | null>(null)
const budgetModelsTotal = ref<number | null>(null)
const budgetMcpsTotal = ref<number | null>(null)
const budgetModelsPer = ref<BudgetSubScope>('unified')
const budgetMcpsPer = ref<BudgetSubScope>('unified')
const modelBudgets = ref<Record<string, number | null>>({})
const mcpBudgets = ref<Record<string, number | null>>({})
const modelSearch = ref('')
const mcpSearch = ref('')
const skillSearch = ref('')
const agentSearch = ref('')
const updateRateLimit = ref(false)
const rateLimitMode = ref<AiKeyRateLimitMode>('none')
const totalTpmLimit = ref<number | null>(null)
const totalRpmLimit = ref<number | null>(null)
const totalParallelLimit = ref<number | null>(null)
const modelRateLimits = ref<Record<string, { tpm: number | null; rpm: number | null }>>({})

const selectedCount = computed(() => selectedUserIds.value.size)
const rateLimitOptions: { value: AiKeyRateLimitMode; label: string }[] = [
  { value: 'none', label: '不限流' },
  { value: 'total', label: '总限流' },
  { value: 'per_model', label: '分模型限流' },
]

watch(() => props.visible, (v) => {
  if (v) {
    step.value = 1
    selectedUserIds.value = new Set()
    resetResourceState()
    fetchUsers()
    fetchResources()
  }
})

function resetResourceState(): void {
  selectedModels.value = []
  selectedMcps.value = []
  selectedSkills.value = []
  selectedAgents.value = []
  budgetDuration.value = '30d'
  budgetScope.value = 'unified'
  budgetLimit.value = null
  budgetModelsTotal.value = null
  budgetMcpsTotal.value = null
  budgetModelsPer.value = 'unified'
  budgetMcpsPer.value = 'unified'
  modelBudgets.value = {}
  mcpBudgets.value = {}
  updateRateLimit.value = false
  rateLimitMode.value = 'none'
  totalTpmLimit.value = null
  totalRpmLimit.value = null
  totalParallelLimit.value = null
  modelRateLimits.value = {}
}

async function fetchUsers(): Promise<void> {
  isLoadingUsers.value = true
  try {
    const result = await getIdentityList('user', userPage.value, 50, userSearch.value || undefined)
    userItems.value = result.items
    userTotal.value = result.total
  } finally {
    isLoadingUsers.value = false
  }
}

async function fetchResources(): Promise<void> {
  const [models, mcps, sk, ag] = await Promise.all([
    getActiveModels(),
    getMcpServers(1, 200),
    getSkills(1, 200),
    getAgents(1, 200),
  ])
  activeModels.value = models
  mcpServers.value = mcps.items
  skillList.value = sk.items
  agentList.value = ag.items
}

function handleUserSearch(): void {
  userPage.value = 1
  fetchUsers()
}

function toggleUser(userId: number): void {
  const s = new Set(selectedUserIds.value)
  if (s.has(userId)) s.delete(userId)
  else s.add(userId)
  selectedUserIds.value = s
}

function toggleAllVisible(): void {
  const s = new Set(selectedUserIds.value)
  const allSelected = userItems.value.every((item) => s.has(item.user.id))
  if (allSelected) {
    userItems.value.forEach((item) => s.delete(item.user.id))
  } else {
    userItems.value.forEach((item) => s.add(item.user.id))
  }
  selectedUserIds.value = s
}

function handleUpdateModelBudget(modelId: string, value: number | null): void {
  modelBudgets.value = { ...modelBudgets.value, [modelId]: value }
}

function handleUpdateMcpBudget(mcpId: number, value: number | null): void {
  mcpBudgets.value = { ...mcpBudgets.value, [String(mcpId)]: value }
}

function getModelName(modelId: string): string {
  return activeModels.value.find((model) => model.model_id === modelId)?.name ?? modelId
}

function getModelDbId(modelId: string): number | undefined {
  return activeModels.value.find((model) => model.model_id === modelId)?.id
}

function ensureModelRateLimit(modelId: string): { tpm: number | null; rpm: number | null } {
  const existing = modelRateLimits.value[modelId]
  if (existing) return existing
  const next = { tpm: null, rpm: null }
  modelRateLimits.value = { ...modelRateLimits.value, [modelId]: next }
  return next
}

function updateModelRateLimit(
  modelId: string,
  field: 'tpm' | 'rpm',
  event: Event,
): void {
  const value = (event.target as HTMLInputElement).value
  const current = ensureModelRateLimit(modelId)
  modelRateLimits.value = {
    ...modelRateLimits.value,
    [modelId]: {
      ...current,
      [field]: value ? Number(value) : null,
    },
  }
}

function buildRateLimits(): RateLimitItem[] | null {
  if (!updateRateLimit.value || rateLimitMode.value !== 'per_model') return null
  const items: RateLimitItem[] = []
  for (const modelId of selectedModels.value) {
    const dbId = getModelDbId(modelId)
    const limit = modelRateLimits.value[modelId]
    if (dbId && limit && (limit.tpm || limit.rpm)) {
      items.push({ model_id: dbId, tpm: limit.tpm, rpm: limit.rpm })
    }
  }
  return items.length ? items : null
}

function hasResources(item: IdentityUserItem): boolean {
  const k = item.main_key
  if (!k) return false
  return k.models.length > 0 || k.mcps.length > 0 || k.skills.length > 0 || k.agents.length > 0
}

function hasBudget(item: IdentityUserItem): boolean {
  const k = item.main_key
  if (!k) return false
  const hasLimit = k.budget_limit !== null && k.budget_limit !== ''
  const hasModelsTotal = k.budget_models_total !== null && k.budget_models_total !== ''
  const hasMcpsTotal = k.budget_mcps_total !== null && k.budget_mcps_total !== ''
  const hasPerResource = Object.keys(k.model_budgets || {}).length > 0 || Object.keys(k.mcp_budgets || {}).length > 0
  const hasHardLimit = k.budget_hard_limit === true
  return hasLimit || hasModelsTotal || hasMcpsTotal || hasPerResource || hasHardLimit
}

function hasRateLimit(item: IdentityUserItem): boolean {
  return item.main_key?.rate_limit_mode !== undefined && item.main_key.rate_limit_mode !== 'none'
}

function handleSubmitClick(): void {
  if (updateRateLimit.value) {
    showRateLimitConfirm.value = true
    return
  }
  handleSubmit()
}

async function handleConfirmRateLimitSubmit(): Promise<void> {
  showRateLimitConfirm.value = false
  await handleSubmit()
}

async function handleSubmit(): Promise<void> {
  isSubmitting.value = true
  try {
    const mBudgets: Record<string, number> = {}
    for (const [k, v] of Object.entries(modelBudgets.value)) {
      if (v !== null && v !== undefined) mBudgets[k] = v
    }
    const mcBudgets: Record<string, number> = {}
    for (const [k, v] of Object.entries(mcpBudgets.value)) {
      if (v !== null && v !== undefined) mcBudgets[k] = Number(v)
    }
    const result = await batchUpdateResources({
      user_ids: Array.from(selectedUserIds.value),
      models: selectedModels.value,
      mcps: selectedMcps.value,
      skills: selectedSkills.value,
      agents: selectedAgents.value,
      budget_limit: budgetLimit.value,
      budget_hard_limit: false,
      budget_duration: budgetDuration.value,
      budget_scope: budgetScope.value,
      budget_models_total: budgetModelsTotal.value,
      budget_mcps_total: budgetMcpsTotal.value,
      budget_models_per: budgetModelsPer.value,
      budget_mcps_per: budgetMcpsPer.value,
      model_budgets: Object.keys(mBudgets).length ? mBudgets : null,
      mcp_budgets: Object.keys(mcBudgets).length ? mcBudgets : null,
      update_rate_limit: updateRateLimit.value,
      rate_limit_mode: updateRateLimit.value ? rateLimitMode.value : null,
      tpm_limit: updateRateLimit.value ? totalTpmLimit.value : null,
      rpm_limit: updateRateLimit.value ? totalRpmLimit.value : null,
      max_parallel_requests: updateRateLimit.value ? totalParallelLimit.value : null,
      rate_limits: buildRateLimits(),
    })
    const failCount = result.failures.length
    if (failCount > 0) {
      toast.error(`批量设置完成，成功 ${result.successes.length} 个，失败 ${failCount} 个`)
    } else {
      toast.success(`批量设置完成，成功 ${result.successes.length} 个`)
    }
    emit('saved')
  } catch {
    toast.error('批量设置失败')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center">
    <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="emit('close')" />
    <div class="relative flex h-[85vh] w-[900px] flex-col overflow-hidden rounded-2xl border border-slate-200/60 bg-white/95 shadow-xl backdrop-blur-xl">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-slate-200/60 px-6 py-4">
        <div class="flex items-center gap-3">
          <h3 class="text-lg font-semibold text-slate-800">批量设置资源、预算和限流</h3>
          <div class="flex rounded-lg bg-slate-100 p-0.5">
            <span :class="['rounded-md px-3 py-1 text-xs font-medium transition', step === 1 ? 'bg-white text-purple-700 shadow-sm' : 'text-slate-500']">1. 选择用户</span>
            <span :class="['rounded-md px-3 py-1 text-xs font-medium transition', step === 2 ? 'bg-white text-purple-700 shadow-sm' : 'text-slate-500']">2. 配置资源</span>
          </div>
        </div>
        <button class="text-slate-400 hover:text-slate-600" @click="emit('close')">
          <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" /></svg>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- Step 1: Select Users -->
        <div v-if="step === 1" class="space-y-4">
          <div class="flex items-center gap-3">
            <input
              v-model="userSearch"
              type="text"
              placeholder="搜索用户..."
              class="w-64 rounded-xl border border-slate-200/60 bg-white/70 px-4 py-2 text-sm backdrop-blur-xl focus:outline-none focus:ring-2 focus:ring-purple-400/50"
              @keyup.enter="handleUserSearch"
            />
            <button class="rounded-xl border border-slate-200/60 bg-white/70 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-white/90" @click="handleUserSearch">搜索</button>
            <span class="ml-auto text-sm text-slate-500">已选 {{ selectedCount }} 人</span>
          </div>

          <div class="rounded-xl border border-slate-200/60 bg-white/80">
            <div v-if="isLoadingUsers" class="flex items-center justify-center py-12">
              <div class="h-5 w-5 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
            </div>
            <table v-else class="w-full text-sm">
              <thead>
                <tr class="border-b border-slate-200/60 text-left text-slate-500">
                  <th class="w-10 px-4 py-3">
                    <input type="checkbox" class="rounded text-purple-600" :checked="userItems.length > 0 && userItems.every((i) => selectedUserIds.has(i.user.id))" @change="toggleAllVisible" />
                  </th>
                  <th class="px-4 py-3 font-medium">用户</th>
                  <th class="px-4 py-3 font-medium">部门</th>
                  <th class="px-4 py-3 font-medium">已配置</th>
                  <th class="px-4 py-3 font-medium">主 Key 状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in userItems" :key="item.user.id" class="border-b border-slate-100/60 hover:bg-purple-50/30 cursor-pointer" @click="toggleUser(item.user.id)">
                  <td class="px-4 py-2.5">
                    <input type="checkbox" class="rounded text-purple-600" :checked="selectedUserIds.has(item.user.id)" @click.stop @change="toggleUser(item.user.id)" />
                  </td>
                  <td class="px-4 py-2.5 font-medium text-slate-800">{{ item.user.display_name || item.user.username }}</td>
                  <td class="px-4 py-2.5 text-slate-500">{{ item.user.department_name || '-' }}</td>
                  <td class="px-4 py-2.5">
                    <div v-if="item.main_key" class="flex flex-wrap gap-1">
                      <span v-if="hasResources(item)" class="rounded-full bg-purple-50 px-2 py-0.5 text-xs text-purple-600">资源</span>
                      <span v-if="hasBudget(item)" class="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-600">预算</span>
                      <span v-if="hasRateLimit(item)" class="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">限流</span>
                      <span v-if="!hasResources(item) && !hasBudget(item) && !hasRateLimit(item)" class="text-xs text-slate-400">未设置</span>
                    </div>
                    <span v-else class="text-xs text-slate-400">-</span>
                  </td>
                  <td class="px-4 py-2.5">
                    <span v-if="item.main_key" :class="['rounded-full px-2 py-0.5 text-xs', item.main_key.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500']">{{ item.main_key.is_active ? '已启用' : '已禁用' }}</span>
                    <span v-else class="text-xs text-slate-400">未创建</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="!isLoadingUsers && !userItems.length" class="py-12 text-center text-sm text-slate-400">暂无数据</div>
          </div>
          <div v-if="userTotal > 50" class="flex items-center justify-between pt-3">
            <span class="text-xs text-slate-500">共 {{ userTotal }} 人</span>
            <div class="flex gap-1">
              <button :disabled="userPage <= 1" class="rounded-lg border border-slate-200/60 bg-white/70 px-3 py-1 text-xs disabled:opacity-40" @click="userPage--; fetchUsers()">上一页</button>
              <button :disabled="userPage * 50 >= userTotal" class="rounded-lg border border-slate-200/60 bg-white/70 px-3 py-1 text-xs disabled:opacity-40" @click="userPage++; fetchUsers()">下一页</button>
            </div>
          </div>
        </div>

        <!-- Step 2: Configure Resources -->
        <div v-if="step === 2">
          <KeyResourceBudget
            :models="activeModels"
            :mcp-servers="mcpServers"
            :skills="skillList"
            :agents="agentList"
            :selected-models="selectedModels"
            :selected-mcps="selectedMcps"
            :selected-skills="selectedSkills"
            :selected-agents="selectedAgents"
            :budget-duration="budgetDuration"
            :budget-scope="budgetScope"
            :budget-limit="budgetLimit"
            :budget-models-total="budgetModelsTotal"
            :budget-mcps-total="budgetMcpsTotal"
            :budget-models-per="budgetModelsPer"
            :budget-mcps-per="budgetMcpsPer"
            :model-budgets="modelBudgets"
            :mcp-budgets="mcpBudgets"
            :model-search="modelSearch"
            :mcp-search="mcpSearch"
            :skill-search="skillSearch"
            :agent-search="agentSearch"
            @update:selected-models="selectedModels = $event"
            @update:selected-mcps="selectedMcps = $event"
            @update:selected-skills="selectedSkills = $event"
            @update:selected-agents="selectedAgents = $event"
            @update:budget-duration="budgetDuration = $event"
            @update:budget-scope="budgetScope = $event"
            @update:budget-limit="budgetLimit = $event"
            @update:budget-models-total="budgetModelsTotal = $event"
            @update:budget-mcps-total="budgetMcpsTotal = $event"
            @update:budget-models-per="budgetModelsPer = $event"
            @update:budget-mcps-per="budgetMcpsPer = $event"
            @update:model-search="modelSearch = $event"
            @update:mcp-search="mcpSearch = $event"
            @update:skill-search="skillSearch = $event"
            @update:agent-search="agentSearch = $event"
            @update-model-budget="handleUpdateModelBudget"
            @update-mcp-budget="handleUpdateMcpBudget"
          />
          <div class="mt-5 rounded-xl border border-slate-200/60 bg-white/80 p-4">
            <label class="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input v-model="updateRateLimit" type="checkbox" class="rounded text-purple-600" />
              修改 AI 身份限流
            </label>
            <div v-if="updateRateLimit" class="mt-3 space-y-3">
              <div class="grid grid-cols-3 gap-2">
                <button
                  v-for="option in rateLimitOptions"
                  :key="option.value"
                  type="button"
                  :class="[rateLimitMode === option.value ? 'border-purple-400 bg-purple-50 text-purple-700' : 'border-slate-200/60 bg-white text-slate-600', 'rounded-lg border px-3 py-2 text-sm transition']"
                  @click="rateLimitMode = option.value"
                >
                  {{ option.label }}
                </button>
              </div>
              <div v-if="rateLimitMode === 'total'" class="grid grid-cols-3 gap-3">
                <label class="text-xs text-slate-500">TPM
                  <input v-model.number="totalTpmLimit" type="number" min="1" class="mt-1 w-full rounded border border-slate-200/60 px-2 py-1 text-sm" />
                </label>
                <label class="text-xs text-slate-500">RPM
                  <input v-model.number="totalRpmLimit" type="number" min="1" class="mt-1 w-full rounded border border-slate-200/60 px-2 py-1 text-sm" />
                </label>
                <label class="text-xs text-slate-500">最大并发
                  <input v-model.number="totalParallelLimit" type="number" min="1" class="mt-1 w-full rounded border border-slate-200/60 px-2 py-1 text-sm" />
                </label>
              </div>
              <div v-if="rateLimitMode === 'per_model' && selectedModels.length" class="overflow-x-auto rounded-lg border border-slate-200/60">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="bg-slate-50 text-left text-slate-500">
                      <th class="px-3 py-2 font-medium">模型</th>
                      <th class="px-3 py-2 font-medium">TPM</th>
                      <th class="px-3 py-2 font-medium">RPM</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="modelId in selectedModels" :key="modelId" class="border-t border-slate-100">
                      <td class="px-3 py-2 text-slate-700">{{ getModelName(modelId) }}</td>
                      <td class="px-3 py-2"><input :value="ensureModelRateLimit(modelId).tpm ?? ''" type="number" min="1" class="w-28 rounded border border-slate-200/60 px-2 py-1 text-sm" @input="updateModelRateLimit(modelId, 'tpm', $event)" /></td>
                      <td class="px-3 py-2"><input :value="ensureModelRateLimit(modelId).rpm ?? ''" type="number" min="1" class="w-28 rounded border border-slate-200/60 px-2 py-1 text-sm" @input="updateModelRateLimit(modelId, 'rpm', $event)" /></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-else-if="rateLimitMode === 'per_model'" class="text-sm text-slate-400">请先选择模型</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between border-t border-slate-200/60 px-6 py-4">
        <button v-if="step === 2" class="rounded-xl border border-slate-200/60 bg-white/70 px-5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-white/90" @click="step = 1">上一步</button>
        <div v-else />
        <div class="flex items-center gap-3">
          <button class="rounded-xl border border-slate-200/60 bg-white/70 px-5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-white/90" @click="emit('close')">取消</button>
          <button v-if="step === 1" :disabled="selectedCount === 0" class="rounded-xl bg-gradient-to-r from-purple-500 to-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:from-purple-600 hover:to-purple-700 disabled:opacity-40" @click="step = 2">下一步 ({{ selectedCount }} 人)</button>
          <button v-else :disabled="isSubmitting" class="rounded-xl bg-gradient-to-r from-purple-500 to-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:from-purple-600 hover:to-purple-700 disabled:opacity-40" @click="handleSubmitClick">
            {{ isSubmitting ? '提交中...' : '确认提交' }}
          </button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="showRateLimitConfirm"
      title="确认批量修改限流"
      :message="`将修改 ${selectedCount} 个 AI 身份的限流配置，可能影响其生产 API 调用。`"
      confirm-text="确认修改"
      cancel-text="取消"
      @confirm="handleConfirmRateLimitSubmit"
      @cancel="showRateLimitConfirm = false"
    />
  </div>
</template>
