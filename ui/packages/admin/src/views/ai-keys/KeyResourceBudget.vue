<script setup lang="ts">
import { computed, watch } from 'vue'
import type { ActiveModel, McpServer, Skill, Agent, BudgetScope, BudgetSubScope } from '@aihelms/shared'

interface Props {
  models: ActiveModel[]
  mcpServers: McpServer[]
  skills: Skill[]
  agents: Agent[]
  selectedModels: string[]
  selectedMcps: number[]
  selectedSkills: number[]
  selectedAgents: number[]
  budgetDuration: string
  budgetScope: BudgetScope
  budgetLimit: number | null
  budgetModelsTotal: number | null
  budgetMcpsTotal: number | null
  budgetModelsPer: BudgetSubScope
  budgetMcpsPer: BudgetSubScope
  modelBudgets: Record<string, number | null>
  mcpBudgets: Record<string, number | null>
  budgetHardLimit: boolean
  modelSearch: string
  mcpSearch: string
  skillSearch: string
  agentSearch: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:selectedModels': [v: string[]]
  'update:selectedMcps': [v: number[]]
  'update:selectedSkills': [v: number[]]
  'update:selectedAgents': [v: number[]]
  'update:budgetDuration': [v: string]
  'update:budgetScope': [v: BudgetScope]
  'update:budgetLimit': [v: number | null]
  'update:budgetModelsTotal': [v: number | null]
  'update:budgetMcpsTotal': [v: number | null]
  'update:budgetModelsPer': [v: BudgetSubScope]
  'update:budgetMcpsPer': [v: BudgetSubScope]
  'update:budgetHardLimit': [v: boolean]
  'update:modelSearch': [v: string]
  'update:mcpSearch': [v: string]
  'update:skillSearch': [v: string]
  'update:agentSearch': [v: string]
  'updateModelBudget': [modelId: string, value: number | null]
  'updateMcpBudget': [mcpId: number, value: number | null]
}>()

const filteredModels = computed(() => {
  const q = props.modelSearch.toLowerCase()
  if (!q) return props.models
  return props.models.filter(
    (m) => m.name.toLowerCase().includes(q) || m.model_id.toLowerCase().includes(q),
  )
})

const filteredMcps = computed(() => {
  const q = props.mcpSearch.toLowerCase()
  if (!q) return props.mcpServers
  return props.mcpServers.filter(
    (m) => m.name.toLowerCase().includes(q) || m.server_name.toLowerCase().includes(q),
  )
})

const filteredSkills = computed(() => {
  const q = props.skillSearch.toLowerCase()
  if (!q) return props.skills
  return props.skills.filter(
    (s) => s.name.toLowerCase().includes(q) || s.category.toLowerCase().includes(q),
  )
})

const filteredAgents = computed(() => {
  const q = props.agentSearch.toLowerCase()
  if (!q) return props.agents
  return props.agents.filter(
    (a) => a.name.toLowerCase().includes(q) || a.platform.toLowerCase().includes(q),
  )
})

const allModelsSelected = computed(
  () =>
    props.selectedModels.length === props.models.length && props.models.length > 0,
)

const allMcpsSelected = computed(
  () =>
    props.selectedMcps.length === props.mcpServers.length && props.mcpServers.length > 0,
)

const allSkillsSelected = computed(
  () => props.selectedSkills.length === props.skills.length && props.skills.length > 0,
)

const allAgentsSelected = computed(
  () => props.selectedAgents.length === props.agents.length && props.agents.length > 0,
)

function toggleAllModels(): void {
  emit('update:selectedModels', allModelsSelected.value ? [] : props.models.map((m) => m.model_id))
}

function toggleAllMcps(): void {
  emit('update:selectedMcps', allMcpsSelected.value ? [] : props.mcpServers.map((m) => m.id))
}

function toggleAllSkills(): void {
  emit('update:selectedSkills', allSkillsSelected.value ? [] : props.skills.map((s) => s.id))
}

function toggleAllAgents(): void {
  emit('update:selectedAgents', allAgentsSelected.value ? [] : props.agents.map((a) => a.id))
}

function toggleModel(modelId: string): void {
  const next = [...props.selectedModels]
  const idx = next.indexOf(modelId)
  if (idx >= 0) next.splice(idx, 1)
  else next.push(modelId)
  emit('update:selectedModels', next)
}

function toggleMcp(mcpId: number): void {
  const next = [...props.selectedMcps]
  const idx = next.indexOf(mcpId)
  if (idx >= 0) next.splice(idx, 1)
  else next.push(mcpId)
  emit('update:selectedMcps', next)
}

function toggleSkill(skillId: number): void {
  const next = [...props.selectedSkills]
  const idx = next.indexOf(skillId)
  if (idx >= 0) next.splice(idx, 1)
  else next.push(skillId)
  emit('update:selectedSkills', next)
}

function toggleAgent(agentId: number): void {
  const next = [...props.selectedAgents]
  const idx = next.indexOf(agentId)
  if (idx >= 0) next.splice(idx, 1)
  else next.push(agentId)
  emit('update:selectedAgents', next)
}

function getModelName(modelId: string): string {
  return props.models.find((m) => m.model_id === modelId)?.name ?? modelId
}

function getMcpName(mcpId: number): string {
  return props.mcpServers.find((m) => m.id === mcpId)?.name ?? `#${mcpId}`
}

watch(
  () => props.budgetScope,
  (scope) => {
    if (scope === 'unified') {
      emit('update:budgetModelsTotal', null)
      emit('update:budgetMcpsTotal', null)
    }
  },
)
</script>

<template>
  <div class="space-y-4">
    <!-- 资源选择 -->
    <div>
      <label class="mb-1 block text-sm font-medium text-slate-700">可用 AI 资源</label>
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <!-- 模型 -->
        <div class="rounded-lg border border-slate-200/60 bg-white/80 p-3">
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs font-medium text-slate-600">模型</span>
            <span class="text-xs text-slate-400">{{ selectedModels.length }} / {{ models.length }}</span>
          </div>
          <input
            :value="modelSearch"
            type="text"
            placeholder="搜索模型..."
            class="mb-2 w-full rounded border border-slate-200/60 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50"
            @input="emit('update:modelSearch', ($event.target as HTMLInputElement).value)"
          />
          <label class="mb-2 flex cursor-pointer items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              :checked="allModelsSelected"
              class="rounded text-purple-600"
              @change="toggleAllModels"
            />
            全选
          </label>
          <div class="max-h-40 overflow-y-auto">
            <div v-for="m in filteredModels" :key="m.id" class="flex items-center gap-2 py-0.5">
              <input
                type="checkbox"
                :checked="selectedModels.includes(m.model_id)"
                class="rounded text-purple-600"
                @change="toggleModel(m.model_id)"
              />
              <span class="truncate text-sm text-slate-700">{{ m.name }}</span>
            </div>
          </div>
        </div>

        <!-- MCP -->
        <div class="rounded-lg border border-slate-200/60 bg-white/80 p-3">
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs font-medium text-slate-600">MCP</span>
            <span class="text-xs text-slate-400">{{ selectedMcps.length }} / {{ mcpServers.length }}</span>
          </div>
          <input
            :value="mcpSearch"
            type="text"
            placeholder="搜索 MCP..."
            class="mb-2 w-full rounded border border-slate-200/60 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50"
            @input="emit('update:mcpSearch', ($event.target as HTMLInputElement).value)"
          />
          <label class="mb-2 flex cursor-pointer items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              :checked="allMcpsSelected"
              class="rounded text-purple-600"
              @change="toggleAllMcps"
            />
            全选
          </label>
          <div class="max-h-40 overflow-y-auto">
            <div v-for="m in filteredMcps" :key="m.id" class="flex items-center gap-2 py-0.5">
              <input
                type="checkbox"
                :checked="selectedMcps.includes(m.id)"
                class="rounded text-purple-600"
                @change="toggleMcp(m.id)"
              />
              <span class="truncate text-sm text-slate-700">{{ m.name }}</span>
            </div>
          </div>
        </div>

        <!-- Skill -->
        <div class="rounded-lg border border-slate-200/60 bg-white/80 p-3">
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs font-medium text-slate-600">Skill</span>
            <span class="text-xs text-slate-400">{{ selectedSkills.length }} / {{ skills.length }}</span>
          </div>
          <input
            :value="skillSearch"
            type="text"
            placeholder="搜索 Skill..."
            class="mb-2 w-full rounded border border-slate-200/60 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50"
            @input="emit('update:skillSearch', ($event.target as HTMLInputElement).value)"
          />
          <label class="mb-2 flex cursor-pointer items-center gap-2 text-xs text-slate-600">
            <input type="checkbox" :checked="allSkillsSelected" class="rounded text-purple-600" @change="toggleAllSkills" />
            全选
          </label>
          <div class="max-h-40 overflow-y-auto">
            <div v-for="s in filteredSkills" :key="s.id" class="flex items-center gap-2 py-0.5">
              <input
                type="checkbox"
                :checked="selectedSkills.includes(s.id)"
                class="rounded text-purple-600"
                @change="toggleSkill(s.id)"
              />
              <span class="truncate text-sm text-slate-700">{{ s.name }}</span>
            </div>
          </div>
        </div>

        <!-- Agent -->
        <div class="rounded-lg border border-slate-200/60 bg-white/80 p-3">
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs font-medium text-slate-600">智能体</span>
            <span class="text-xs text-slate-400">{{ selectedAgents.length }} / {{ agents.length }}</span>
          </div>
          <input
            :value="agentSearch"
            type="text"
            placeholder="搜索智能体..."
            class="mb-2 w-full rounded border border-slate-200/60 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50"
            @input="emit('update:agentSearch', ($event.target as HTMLInputElement).value)"
          />
          <label class="mb-2 flex cursor-pointer items-center gap-2 text-xs text-slate-600">
            <input type="checkbox" :checked="allAgentsSelected" class="rounded text-purple-600" @change="toggleAllAgents" />
            全选
          </label>
          <div class="max-h-40 overflow-y-auto">
            <div v-for="a in filteredAgents" :key="a.id" class="flex items-center gap-2 py-0.5">
              <input
                type="checkbox"
                :checked="selectedAgents.includes(a.id)"
                class="rounded text-purple-600"
                @change="toggleAgent(a.id)"
              />
              <span class="truncate text-sm text-slate-700">{{ a.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 预算 -->
    <div>
      <label class="mb-1 block text-sm font-medium text-slate-700">预算设置</label>
      <div class="space-y-3 rounded-lg border border-slate-200/60 bg-white/80 p-3">
        <div class="flex items-center gap-3">
          <select
            :value="budgetDuration"
            class="rounded-lg border border-slate-200/60 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50"
            @change="emit('update:budgetDuration', ($event.target as HTMLSelectElement).value)"
          >
            <option value="30d">月 (30天)</option>
            <option value="7d">周 (7天)</option>
            <option value="1d">日 (1天)</option>
          </select>
          <div class="flex">
            <button
              type="button"
              class="rounded-l-lg px-3 py-1 text-sm transition"
              :class="budgetScope === 'unified' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600'"
              @click="emit('update:budgetScope', 'unified')"
            >
              统一预算
            </button>
            <button
              type="button"
              class="px-3 py-1 text-sm transition"
              :class="budgetScope === 'per_type' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600'"
              @click="emit('update:budgetScope', 'per_type')"
            >
              分类预算
            </button>
            <button
              type="button"
              class="rounded-r-lg px-3 py-1 text-sm transition"
              :class="budgetScope === 'per_resource' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600'"
              @click="emit('update:budgetScope', 'per_resource')"
            >
              自定义
            </button>
          </div>
        </div>

        <!-- 统一预算 -->
        <div v-if="budgetScope === 'unified'" class="flex items-center gap-2">
          <span class="text-sm text-slate-600">¥</span>
          <input
            :value="budgetLimit"
            type="number"
            min="0"
            placeholder="所有 AI 资源共用预算"
            class="w-40 rounded-lg border border-slate-200/60 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50"
            @input="emit('update:budgetLimit', Number(($event.target as HTMLInputElement).value) || null)"
          />
        </div>

        <!-- 分类预算 -->
        <div v-else-if="budgetScope === 'per_type'" class="space-y-3">
          <!-- 模型部分 -->
          <div class="rounded border border-slate-200/60 p-2">
            <div class="mb-2 flex items-center justify-between">
              <span class="text-xs font-medium text-slate-700">模型预算</span>
              <div class="flex">
                <button
                  type="button"
                  class="rounded-l px-2 py-0.5 text-xs"
                  :class="budgetModelsPer === 'unified' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600'"
                  @click="emit('update:budgetModelsPer', 'unified')"
                >
                  统一
                </button>
                <button
                  type="button"
                  class="rounded-r px-2 py-0.5 text-xs"
                  :class="budgetModelsPer === 'each' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600'"
                  @click="emit('update:budgetModelsPer', 'each')"
                >
                  按模型
                </button>
              </div>
            </div>
            <div v-if="budgetModelsPer === 'unified'" class="flex items-center gap-2">
              <span class="text-sm text-slate-600">¥</span>
              <input
                :value="budgetModelsTotal"
                type="number"
                min="0"
                placeholder="模型总预算"
                class="w-32 rounded border border-slate-200/60 px-2 py-1 text-sm focus:outline-none"
                @input="
                  emit(
                    'update:budgetModelsTotal',
                    Number(($event.target as HTMLInputElement).value) || null,
                  )
                "
              />
            </div>
            <div v-else class="space-y-1">
              <div v-for="mid in selectedModels" :key="mid" class="flex items-center gap-2">
                <span class="w-32 truncate text-xs text-slate-700">{{ getModelName(mid) }}</span>
                <span class="text-xs text-slate-600">¥</span>
                <input
                  :value="modelBudgets[mid] ?? null"
                  type="number"
                  min="0"
                  class="w-24 rounded border border-slate-200/60 px-2 py-0.5 text-xs focus:outline-none"
                  @input="
                    emit('updateModelBudget', mid, Number(($event.target as HTMLInputElement).value) || null)
                  "
                />
              </div>
            </div>
          </div>

          <!-- MCP 部分 -->
          <div class="rounded border border-slate-200/60 p-2">
            <div class="mb-2 flex items-center justify-between">
              <span class="text-xs font-medium text-slate-700">MCP 预算</span>
              <div class="flex">
                <button
                  type="button"
                  class="rounded-l px-2 py-0.5 text-xs"
                  :class="budgetMcpsPer === 'unified' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600'"
                  @click="emit('update:budgetMcpsPer', 'unified')"
                >
                  统一
                </button>
                <button
                  type="button"
                  class="rounded-r px-2 py-0.5 text-xs"
                  :class="budgetMcpsPer === 'each' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600'"
                  @click="emit('update:budgetMcpsPer', 'each')"
                >
                  按 MCP
                </button>
              </div>
            </div>
            <div v-if="budgetMcpsPer === 'unified'" class="flex items-center gap-2">
              <span class="text-sm text-slate-600">¥</span>
              <input
                :value="budgetMcpsTotal"
                type="number"
                min="0"
                placeholder="MCP 总预算"
                class="w-32 rounded border border-slate-200/60 px-2 py-1 text-sm focus:outline-none"
                @input="
                  emit(
                    'update:budgetMcpsTotal',
                    Number(($event.target as HTMLInputElement).value) || null,
                  )
                "
              />
            </div>
            <div v-else class="space-y-1">
              <div v-for="mid in selectedMcps" :key="mid" class="flex items-center gap-2">
                <span class="w-32 truncate text-xs text-slate-700">{{ getMcpName(mid) }}</span>
                <span class="text-xs text-slate-600">¥</span>
                <input
                  :value="mcpBudgets[String(mid)] ?? null"
                  type="number"
                  min="0"
                  class="w-24 rounded border border-slate-200/60 px-2 py-0.5 text-xs focus:outline-none"
                  @input="
                    emit('updateMcpBudget', mid, Number(($event.target as HTMLInputElement).value) || null)
                  "
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 自定义预算（每个资源独立） -->
        <div v-else class="space-y-1">
          <div v-for="mid in selectedModels" :key="`m-${mid}`" class="flex items-center gap-2">
            <span class="w-12 text-xs text-purple-700">模型</span>
            <span class="w-40 truncate text-sm text-slate-700">{{ getModelName(mid) }}</span>
            <span class="text-sm text-slate-600">¥</span>
            <input
              :value="modelBudgets[mid] ?? null"
              type="number"
              min="0"
              class="w-28 rounded border border-slate-200/60 px-2 py-1 text-xs focus:outline-none"
              @input="
                emit('updateModelBudget', mid, Number(($event.target as HTMLInputElement).value) || null)
              "
            />
          </div>
          <div v-for="mid in selectedMcps" :key="`mcp-${mid}`" class="flex items-center gap-2">
            <span class="w-12 text-xs text-blue-700">MCP</span>
            <span class="w-40 truncate text-sm text-slate-700">{{ getMcpName(mid) }}</span>
            <span class="text-sm text-slate-600">¥</span>
            <input
              :value="mcpBudgets[String(mid)] ?? null"
              type="number"
              min="0"
              class="w-28 rounded border border-slate-200/60 px-2 py-1 text-xs focus:outline-none"
              @input="
                emit('updateMcpBudget', mid, Number(($event.target as HTMLInputElement).value) || null)
              "
            />
          </div>
        </div>

        <label class="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            :checked="budgetHardLimit"
            class="rounded text-purple-600"
            @change="emit('update:budgetHardLimit', ($event.target as HTMLInputElement).checked)"
          />
          超出预算立刻禁止使用
        </label>
      </div>
    </div>
  </div>
</template>
