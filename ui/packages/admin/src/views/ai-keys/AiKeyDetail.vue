<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import {
  getAiKeyById,
  updateAiKey,
  getActiveModels,
  getMcpServers,
  getSkills,
  getAgents,
  getAllKeyScenarios,
  getModelLimits,
  toast,
} from '@aihelms/shared'
import type {
  AiKey,
  ActiveModel,
  McpServer,
  Skill,
  Agent,
  KeyScenario,
  RateLimitItem,
  AiKeyRateLimitMode,
  BudgetScope,
  BudgetSubScope,
} from '@aihelms/shared'
import KeyResourceBudget from './KeyResourceBudget.vue'

const route = useRoute()
const router = useRouter()
const keyId = computed(() => Number(route.params.id))

const loading = ref(true)
const saving = ref(false)
const aiKey = ref<AiKey | null>(null)

const form = reactive({
  key_type: '' as string,
  scenario_id: null as number | null,
  name: '',
  description: '',
  models: [] as string[],
  mcps: [] as number[],
  skills: [] as number[],
  agents: [] as number[],
  budget_duration: '30d',
  budget_scope: 'unified' as BudgetScope,
  budget_limit: null as number | null,
  budget_models_total: null as number | null,
  budget_mcps_total: null as number | null,
  budget_models_per: 'unified' as BudgetSubScope,
  budget_mcps_per: 'unified' as BudgetSubScope,
  budget_hard_limit: false,
})

const scenarios = ref<KeyScenario[]>([])
const models = ref<ActiveModel[]>([])
const mcpServers = ref<McpServer[]>([])
const skills = ref<Skill[]>([])
const agentItems = ref<Agent[]>([])
const modelSearch = ref('')
const mcpSearch = ref('')
const skillSearch = ref('')
const agentSearch = ref('')
const modelBudgets = reactive<Record<string, number | null>>({})
const mcpBudgets = reactive<Record<string, number | null>>({})

interface RateLimitEntry { tpm: number | null; rpm: number | null }
const rateLimitMode = ref<AiKeyRateLimitMode>('none')
const totalTpmLimit = ref<number | null>(null)
const totalRpmLimit = ref<number | null>(null)
const totalParallelLimit = ref<number | null>(null)
const rateLimits = reactive<Record<string, RateLimitEntry>>({})
const rateLimitOptions: { value: AiKeyRateLimitMode; label: string }[] = [
  { value: 'none', label: '不限流' },
  { value: 'total', label: '总限流' },
  { value: 'per_model', label: '分模型限流' },
]

const keyTypeLabels: Record<string, string> = {
  personal_main: '个人主 Key',
  personal_scene: '个人场景 Key',
  dept_main: '部门主 Key',
  dept_scene: '部门场景 Key',
  project_main: '项目主 Key',
  project_scene: '项目场景 Key',
}

function getModelName(modelId: string): string {
  return models.value.find(m => m.model_id === modelId)?.name ?? modelId
}

function getModelDbId(modelId: string): number | undefined {
  return models.value.find(m => m.model_id === modelId)?.id
}

function handleModelBudgetUpdate(modelId: string, value: number | null) {
  modelBudgets[modelId] = value
}

function handleMcpBudgetUpdate(mcpId: number, value: number | null) {
  mcpBudgets[String(mcpId)] = value
}

watch(() => form.models, (ids) => {
  for (const id of ids) {
    if (!rateLimits[id]) {
      rateLimits[id] = { tpm: null, rpm: null }
    }
  }
}, { immediate: true, deep: true })

function buildRateLimits(): RateLimitItem[] | null {
  if (rateLimitMode.value !== 'per_model') return null
  const items: RateLimitItem[] = []
  for (const mid of form.models) {
    const dbId = getModelDbId(mid)
    if (!dbId) continue
    const entry = rateLimits[mid]
    if (entry && (entry.tpm || entry.rpm)) {
      items.push({ model_id: dbId, tpm: entry.tpm, rpm: entry.rpm })
    }
  }
  return items.length > 0 ? items : null
}

function buildModelBudgets(): Record<string, number> | null {
  const result: Record<string, number> = {}
  for (const mid of form.models) {
    const val = modelBudgets[mid]
    if (val && val > 0) result[mid] = val
  }
  return Object.keys(result).length > 0 ? result : null
}

function buildMcpBudgets(): Record<string, number> | null {
  const result: Record<string, number> = {}
  for (const mid of form.mcps) {
    const val = mcpBudgets[String(mid)]
    if (val && val > 0) result[String(mid)] = val
  }
  return Object.keys(result).length > 0 ? result : null
}

async function handleSave() {
  saving.value = true
  try {
    const isUnified = form.budget_scope === 'unified'
    const isPerType = form.budget_scope === 'per_type'
    const budgetLimit = isUnified ? form.budget_limit : null
    const budgetModelsTotal = isPerType && form.budget_models_per === 'unified' ? form.budget_models_total : null
    const budgetMcpsTotal = isPerType && form.budget_mcps_per === 'unified' ? form.budget_mcps_total : null
    const includeModelBudgets = form.budget_scope === 'per_resource' || (isPerType && form.budget_models_per === 'each')
    const includeMcpBudgets = form.budget_scope === 'per_resource' || (isPerType && form.budget_mcps_per === 'each')
    const mBudgets = includeModelBudgets ? buildModelBudgets() : null
    const mcpBgts = includeMcpBudgets ? buildMcpBudgets() : null
    const rLimits = buildRateLimits()

    await updateAiKey(keyId.value, {
      name: form.name,
      description: form.description,
      models: form.models,
      mcps: form.mcps,
      skills: form.skills,
      agents: form.agents,
      budget_limit: budgetLimit,
      budget_hard_limit: false,
      budget_duration: form.budget_duration,
      budget_scope: form.budget_scope,
      budget_models_total: budgetModelsTotal,
      budget_mcps_total: budgetMcpsTotal,
      budget_models_per: form.budget_models_per,
      budget_mcps_per: form.budget_mcps_per,
      model_budgets: mBudgets,
      mcp_budgets: mcpBgts,
      scenario_id: form.scenario_id,
      rate_limit_mode: rateLimitMode.value,
      tpm_limit: totalTpmLimit.value,
      rpm_limit: totalRpmLimit.value,
      max_parallel_requests: totalParallelLimit.value,
      rate_limits: rLimits,
    })


    toast.success('保存成功')
    router.push('/ai-keys')
  } catch (e) {
    toast.error((e as { message?: string }).message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function loadData() {
  loading.value = true
  try {
    const [key, modelsRes, scenariosRes, mcpsRes, skillsRes, agentsRes] = await Promise.all([
      getAiKeyById(keyId.value),
      getActiveModels(),
      getAllKeyScenarios(),
      getMcpServers(1, 200),
      getSkills(1, 200),
      getAgents(1, 200),
    ])

    aiKey.value = key
    models.value = modelsRes
    scenarios.value = scenariosRes
    mcpServers.value = mcpsRes.items
    skills.value = skillsRes.items
    agentItems.value = agentsRes.items

    form.key_type = key.key_type
    form.scenario_id = key.scenario_id ?? null
    form.name = key.name
    form.description = key.description ?? ''
    form.models = key.models ?? []
    form.mcps = key.mcps ?? []
    form.skills = key.skills ?? []
    form.agents = key.agents ?? []
    form.budget_duration = key.budget_duration ?? '30d'
    form.budget_scope = key.budget_scope ?? 'unified'
    form.budget_limit = key.budget_limit ? parseFloat(key.budget_limit) : null
    form.budget_models_total = key.budget_models_total ? parseFloat(key.budget_models_total) : null
    form.budget_mcps_total = key.budget_mcps_total ? parseFloat(key.budget_mcps_total) : null
    form.budget_models_per = key.budget_models_per ?? 'unified'
    form.budget_mcps_per = key.budget_mcps_per ?? 'unified'
    form.budget_hard_limit = key.budget_hard_limit
    rateLimitMode.value = key.rate_limit_mode ?? 'none'
    totalTpmLimit.value = key.tpm_limit
    totalRpmLimit.value = key.rpm_limit
    totalParallelLimit.value = key.max_parallel_requests
    if (key.model_budgets) Object.assign(modelBudgets, key.model_budgets)
    if (key.mcp_budgets) Object.assign(mcpBudgets, key.mcp_budgets)

    const limits = await getModelLimits(key.id)
    if (key.rate_limit_mode === 'per_model' && limits.length > 0) {
      for (const l of limits) {
        rateLimits[l.model_model_id] = { tpm: l.tpm, rpm: l.rpm }
      }
    }
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-5 flex items-center justify-between">
      <button
        class="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
        @click="router.push('/ai-keys')"
      >
        <ArrowLeft class="h-4 w-4" />
        返回列表
      </button>
      <button
        :disabled="saving"
        class="rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-5 py-2 text-sm font-medium text-white shadow transition hover:shadow-lg disabled:opacity-50"
        @click="handleSave"
      >
        {{ saving ? '保存中...' : '保存' }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中...</div>

    <template v-else-if="aiKey">
      <!-- Title -->
      <div class="mb-5 rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
        <div class="mb-1 flex items-center gap-3">
          <h1 class="text-lg font-bold text-slate-900">{{ aiKey.name }}</h1>
          <span class="rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700">
            {{ keyTypeLabels[aiKey.key_type] || aiKey.key_type }}
          </span>
          <span v-if="aiKey.is_active" class="rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">启用</span>
          <span v-else class="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">停用</span>
        </div>
      </div>

      <!-- Basic Info -->
      <div class="mb-5 rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
        <h2 class="mb-4 text-sm font-semibold text-slate-900">基本信息</h2>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">Key 名称</label>
            <input
              v-model="form.name"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">场景</label>
            <select
              v-model="form.scenario_id"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            >
              <option :value="null">不选择场景</option>
              <option v-for="s in scenarios" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">描述</label>
            <input
              v-model="form.description"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
              placeholder="Key 用途描述"
            />
          </div>
        </div>
      </div>

      <!-- Resource & Budget (full width) -->
      <div class="mb-5 rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
        <h2 class="mb-4 text-sm font-semibold text-slate-900">资源与预算</h2>
        <KeyResourceBudget
          :models="models"
          :mcp-servers="mcpServers"
          :skills="skills"
          :agents="agentItems"
          :selected-models="form.models"
          :selected-mcps="form.mcps"
          :selected-skills="form.skills"
          :selected-agents="form.agents"
          :budget-duration="form.budget_duration"
          :budget-scope="form.budget_scope"
          :budget-limit="form.budget_limit"
          :budget-models-total="form.budget_models_total"
          :budget-mcps-total="form.budget_mcps_total"
          :budget-models-per="form.budget_models_per"
          :budget-mcps-per="form.budget_mcps_per"
          :model-budgets="modelBudgets"
          :mcp-budgets="mcpBudgets"
          :model-search="modelSearch"
          :mcp-search="mcpSearch"
          :skill-search="skillSearch"
          :agent-search="agentSearch"
          @update:selected-models="form.models = $event"
          @update:selected-mcps="form.mcps = $event"
          @update:selected-skills="form.skills = $event"
          @update:selected-agents="form.agents = $event"
          @update:budget-duration="form.budget_duration = $event"
          @update:budget-scope="form.budget_scope = $event"
          @update:budget-limit="form.budget_limit = $event"
          @update:budget-models-total="form.budget_models_total = $event"
          @update:budget-mcps-total="form.budget_mcps_total = $event"
          @update:budget-models-per="form.budget_models_per = $event"
          @update:budget-mcps-per="form.budget_mcps_per = $event"
          @update:model-search="modelSearch = $event"
          @update:mcp-search="mcpSearch = $event"
          @update:skill-search="skillSearch = $event"
          @update:agent-search="agentSearch = $event"
          @update-model-budget="handleModelBudgetUpdate"
          @update-mcp-budget="handleMcpBudgetUpdate"
        />
      </div>

      <!-- Rate Limiting -->
      <div class="mb-5 rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
        <h2 class="mb-3 text-sm font-semibold text-slate-900">AI 身份限流</h2>
        <div class="mb-3 grid grid-cols-3 gap-2">
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
        <div v-if="rateLimitMode === 'total'" class="mb-3 grid grid-cols-3 gap-3">
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
        <div v-if="rateLimitMode === 'per_model' && form.models.length" class="overflow-x-auto rounded-lg border border-slate-200/60 bg-white/80 p-3">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-slate-500">
                <th class="pb-2">模型</th>
                <th class="pb-2 px-3">TPM</th>
                <th class="pb-2 px-3">RPM</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="mid in form.models" :key="mid">
                <td class="max-w-[200px] truncate py-1.5 text-slate-700">{{ getModelName(mid) }}</td>
                <td class="px-3 py-1.5"><input v-model.number="rateLimits[mid].tpm" type="number" min="0" class="w-28 rounded border border-slate-200/60 px-2 py-1 text-sm" /></td>
                <td class="px-3 py-1.5"><input v-model.number="rateLimits[mid].rpm" type="number" min="0" class="w-28 rounded border border-slate-200/60 px-2 py-1 text-sm" /></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else-if="rateLimitMode === 'per_model'" class="text-sm text-slate-400">请先选择模型</p>
      </div>
    </template>
  </div>
</template>
