<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMarketV2 } from '@aihelms/shared'
import type { HubMcp, HubSkill } from '@aihelms/shared'
import { request } from '@aihelms/shared/src/api/request'
import { createResourceApplication } from '@aihelms/shared/src/api/resource-application'
import HostedIcon from '@aihelms/shared/src/components/HostedIcon.vue'
import { CheckCircle2, Search, X, ExternalLink, Flame } from 'lucide-vue-next'

const { t } = useI18n()

type MarketItem = (HubSkill & { _type: 'skill' }) | (HubMcp & { _type: 'mcp' })

const items = ref<MarketItem[]>([])
const mySkills = ref<number[]>([])
const myMcps = ref<number[]>([])
const isLoading = ref(true)
const search = ref('')
const typeFilter = ref<'all' | 'skill' | 'mcp'>('all')
const categoryFilter = ref('')
const showApplyDialog = ref(false)
const showMcpAccessDialog = ref(false)
const applyTarget = ref<MarketItem | null>(null)
const mcpTarget = ref<HubMcp | null>(null)
const applyReason = ref('')
const applyingId = ref<number | null>(null)

const categories = computed(() => {
  const base = items.value.filter(i => typeFilter.value === 'all' || i._type === typeFilter.value)
  const set = new Set(base.map(i => i.category).filter(Boolean))
  return Array.from(set).sort()
})

async function copyToClipboard(text: string): Promise<void> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
  } catch { /* ignore */ }
}

const filtered = computed(() => {
  return items.value.filter(item => {
    if (typeFilter.value !== 'all' && item._type !== typeFilter.value) return false
    if (categoryFilter.value && item.category !== categoryFilter.value) return false
    if (search.value) {
      const q = search.value.toLowerCase()
      if (!item.name.toLowerCase().includes(q) && !item.description?.toLowerCase().includes(q)) return false
    }
    return true
  })
})

function isOwned(item: MarketItem): boolean {
  return item._type === 'skill' ? mySkills.value.includes(item.id) : myMcps.value.includes(item.id)
}

function getTags(item: MarketItem): string[] {
  return item.tags?.slice(0, 3) ?? []
}

function getIconUrl(item: MarketItem): string {
  return item.icon_url
}

function getAuthor(item: MarketItem): string {
  return item.author ?? ''
}

function getUsageCount(item: MarketItem): number {
  if (item._type === 'skill') return item.install_count ?? 0
  return item.call_count ?? 0
}

function formatUsageCount(count: number): string {
  if (count >= 1_000_000) return `${Math.floor(count / 100_000) / 10}M`
  if (count >= 10_000) return `${Math.floor(count / 1000)}K`
  if (count >= 1000) return `${Math.floor(count / 100) / 10}K`
  return String(count)
}

async function handleCopyPrompt(item: MarketItem) {
  if (item._type !== 'skill') return
  skillTarget.value = item
  skillInstallInfo.value = null
  showSkillInstallDialog.value = true
  loadSkillInstall(item.id)
}

async function loadSkillInstall(skillId: number) {
  skillInstallLoading.value = true
  try {
    skillInstallInfo.value = await request<SkillInstallInfo>(`/api/v1/skills/${skillId}/install-info`)
  } catch { /* */ }
  finally { skillInstallLoading.value = false }
}

async function copySkillPrompt() {
  if (!skillInstallInfo.value) return
  await copyToClipboard(skillInstallInfo.value.agent_prompt)
  skillPromptCopied.value = true
  setTimeout(() => { skillPromptCopied.value = false }, 2000)
}

interface SkillInstallInfo {
  name: string
  description: string
  agent_prompt: string
  download_url: string
  usage_instructions: string
  author?: string
}

const showSkillInstallDialog = ref(false)
const skillTarget = ref<HubSkill | null>(null)
const skillInstallInfo = ref<SkillInstallInfo | null>(null)
const skillInstallLoading = ref(false)
const skillPromptCopied = ref(false)

function handleViewAccess(item: MarketItem) {
  if (item._type !== 'mcp') return
  mcpTarget.value = item
  mcpConnectConfig.value = null
  showMcpAccessDialog.value = true
  loadMcpConfig(item.id)
}

interface McpConnectConfig {
  name: string
  description: string
  author?: string
  agent_prompt: string
  config: Record<string, unknown>
  instructions: string
  tools: Array<{ name: string; description: string }>
}

const mcpConnectConfig = ref<McpConnectConfig | null>(null)
const mcpConfigLoading = ref(false)
const mcpConfigCopied = ref(false)

async function loadMcpConfig(serverId: number) {
  mcpConfigLoading.value = true
  try {
    const res = await request<McpConnectConfig>(`/api/v1/mcp/servers/${serverId}/connect-config`)
    mcpConnectConfig.value = res
  } catch { /* */ }
  finally { mcpConfigLoading.value = false }
}

function getSkillDialogAuthor(): string {
  return skillInstallInfo.value?.author ?? skillTarget.value?.author ?? ''
}

function getMcpDialogAuthor(): string {
  return mcpConnectConfig.value?.author ?? mcpTarget.value?.author ?? ''
}

function getSkillDialogUsageCount(): number {
  return skillTarget.value?.install_count ?? 0
}

function getMcpDialogUsageCount(): number {
  return mcpTarget.value?.call_count ?? 0
}

async function copyMcpConfig() {
  if (!mcpConnectConfig.value) return
  const text = mcpConnectConfig.value.agent_prompt + JSON.stringify(mcpConnectConfig.value.config, null, 2)
  await copyToClipboard(text)
  mcpConfigCopied.value = true
  setTimeout(() => { mcpConfigCopied.value = false }, 2000)
}

function handleApply(item: MarketItem) {
  applyTarget.value = item
  applyReason.value = ''
  showApplyDialog.value = true
}

async function submitApply() {
  if (!applyTarget.value) return
  applyingId.value = applyTarget.value.id
  try {
    await createResourceApplication({
      resource_type: applyTarget.value._type,
      resource_id: applyTarget.value.id,
      reason: applyReason.value.trim(),
    })
    showApplyDialog.value = false
  } finally {
    applyingId.value = null
  }
}

async function loadData() {
  isLoading.value = true
  try {
    const data = await getMarketV2()
    const skillRes = data.skills
    const mcpRes = data.mcp
    const skillItems: MarketItem[] = (skillRes?.items ?? []).map(s => ({ ...s, _type: 'skill' as const }))
    const mcpItems: MarketItem[] = (mcpRes?.items ?? []).map(m => ({ ...m, _type: 'mcp' as const }))
    items.value = [...skillItems, ...mcpItems]

    const mainKey = data.keys.personal.main_key
    mySkills.value = mainKey?.skills ?? []
    myMcps.value = mainKey?.mcps ?? []
  } finally {
    isLoading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="mx-auto max-w-6xl px-6 py-8 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-slate-800">{{ t('market.title') }}</h1>
    </div>

    <!-- Filters -->
    <div class="space-y-4">
      <!-- Type filter + Search -->
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-1 rounded-xl bg-white/70 p-1 backdrop-blur border border-slate-200/60">
          <button
            v-for="opt in [{ key: 'all', label: t('market.filter.all') }, { key: 'skill', label: 'Skill' }, { key: 'mcp', label: 'MCP' }]"
            :key="opt.key"
            class="rounded-lg px-4 py-1.5 text-sm font-medium transition-all"
            :class="typeFilter === opt.key
              ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900'"
            @click="typeFilter = opt.key as 'all' | 'skill' | 'mcp'"
          >
            {{ opt.label }}
          </button>
        </div>
        <div class="relative flex-1 max-w-xs">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            v-model="search"
            type="text"
            :placeholder="t('market.search.placeholder')"
            class="w-full rounded-xl border border-slate-200/60 bg-white/70 py-2 pl-9 pr-4 text-sm backdrop-blur placeholder:text-slate-400 focus:border-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
          />
        </div>
      </div>
      <!-- Category tags -->
      <div v-if="categories.length" class="flex flex-wrap items-center gap-2">
        <button
          class="rounded-lg px-3 py-1 text-xs font-medium transition-all"
          :class="!categoryFilter
            ? 'bg-purple-100 text-purple-700'
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          @click="categoryFilter = ''"
        >
          {{ t('market.filter.allCategories') }}
        </button>
        <button
          v-for="cat in categories"
          :key="cat"
          class="rounded-lg px-3 py-1 text-xs font-medium transition-all"
          :class="categoryFilter === cat
            ? 'bg-purple-100 text-purple-700'
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          @click="categoryFilter = cat"
        >
          {{ cat }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
    </div>

    <!-- Empty -->
    <div v-else-if="!filtered.length" class="py-20 text-center text-slate-400">
      {{ t('market.empty') }}
    </div>

    <!-- Card Grid -->
    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <div
        v-for="item in filtered"
        :key="`${item._type}-${item.id}`"
        class="group relative flex min-h-[200px] flex-col rounded-2xl border border-slate-200/60 bg-white/70 p-5 backdrop-blur transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-purple-500/5"
      >
        <!-- Icon + Type badge -->
        <div class="mb-3 flex items-start justify-between">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-100 to-blue-100">
            <HostedIcon :src="getIconUrl(item)" :size="20" :alt="item.name" />
          </div>
          <div class="flex items-center gap-1.5">
            <CheckCircle2 v-if="isOwned(item)" class="h-4 w-4 text-green-500" />
            <span
              class="rounded-md px-2 py-0.5 text-xs font-medium"
              :class="item._type === 'skill' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'"
            >
              {{ item._type === 'skill' ? 'Skill' : 'MCP' }}
            </span>
          </div>
        </div>

        <!-- Name + Category -->
          <div class="mb-1 flex items-start justify-between gap-3">
            <h3 class="min-w-0 flex-1 text-sm font-semibold text-slate-800 line-clamp-1">{{ item.name }}</h3>
            <span v-if="getAuthor(item)" class="max-w-[6em] shrink-0 truncate text-xs text-slate-400">{{ getAuthor(item) }}</span>
          </div>
        <p v-if="item.category" class="mb-2 text-xs text-slate-400">{{ item.category }}</p>

        <!-- Tags -->
          <div class="mb-2 flex items-start justify-between gap-2">
            <div v-if="getTags(item).length" class="flex min-w-0 flex-wrap gap-1">
              <span
                v-for="tag in getTags(item)"
                :key="tag"
                class="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500"
              >
                {{ tag }}
              </span>
            </div>
            <div v-else class="min-w-0" />
            <span class="flex shrink-0 items-center gap-1 pt-0.5 text-xs text-slate-400 tabular-nums">
              <Flame class="h-3.5 w-3.5 text-orange-500" />
              {{ formatUsageCount(getUsageCount(item)) }}
            </span>
          </div>
        <!-- Description -->
        <p class="flex-1 text-xs leading-relaxed text-slate-500 line-clamp-3">{{ item.description }}</p>
        <!-- Hover actions -->
        <div class="absolute inset-x-0 bottom-0 flex items-center justify-center rounded-b-2xl bg-gradient-to-t from-white/90 to-transparent px-5 pb-4 pt-8 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
          <button
            v-if="(isOwned(item) || !item.requires_approval) && item._type === 'skill'"
            class="rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm transition-transform hover:scale-105"
            @click="handleCopyPrompt(item)"
          >
            {{ t('market.action.installSkill') }}
          </button>
          <button
            v-else-if="(isOwned(item) || !item.requires_approval) && item._type === 'mcp'"
            class="flex items-center gap-1 rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm transition-transform hover:scale-105"
            @click="handleViewAccess(item)"
          >
            <ExternalLink class="h-3 w-3" />
            {{ t('market.action.viewAccess') }}
          </button>
          <button
            v-else
            class="rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm transition-transform hover:scale-105"
            @click="handleApply(item)"
          >
            {{ t('market.action.apply') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Apply Dialog -->
    <Teleport to="body">
      <div v-if="showApplyDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" @click.self="showApplyDialog = false">
        <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-lg font-semibold text-slate-800">{{ t('market.apply.title') }}</h3>
            <button class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" @click="showApplyDialog = false">
              <X class="h-5 w-5" />
            </button>
          </div>
          <p class="mb-3 text-sm text-slate-500">
            {{ t('market.apply.description', { name: applyTarget?.name || '' }) }}
          </p>
          <textarea
            v-model="applyReason"
            rows="4"
            :placeholder="t('market.apply.placeholder')"
            class="w-full rounded-xl border border-slate-200/60 bg-white/70 px-4 py-3 text-sm backdrop-blur placeholder:text-slate-400 focus:border-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
          />
          <div class="mt-4 flex justify-end gap-3">
            <button
              class="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
              @click="showApplyDialog = false"
            >
              {{ t('common.action.cancel') }}
            </button>
            <button
              class="rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-50"
              :disabled="!applyReason.trim() || applyingId !== null"
              @click="submitApply"
            >
              {{ applyingId !== null ? t('market.apply.submitting') : t('market.apply.submit') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- MCP Access Dialog -->
    <Teleport to="body">
      <div v-if="showMcpAccessDialog && mcpTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" @click.self="showMcpAccessDialog = false">
        <div class="flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl border border-slate-200/60 bg-white/90 shadow-xl backdrop-blur">
            <div class="flex items-center justify-between gap-4 border-b border-slate-100 px-6 py-4">
              <div class="flex min-w-0 items-center gap-2">
                <h3 class="truncate text-lg font-semibold text-slate-800">{{ mcpTarget.name }}</h3>
                <span v-if="getMcpDialogAuthor()" class="max-w-[6em] shrink-0 truncate text-xs text-slate-400">{{ getMcpDialogAuthor() }}</span>
                <span class="flex shrink-0 items-center gap-1 text-xs text-slate-400 tabular-nums">
                  <Flame class="h-3.5 w-3.5 text-orange-500" />
                  {{ formatUsageCount(getMcpDialogUsageCount()) }}
                </span>
              </div>
            <button class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" @click="showMcpAccessDialog = false">
              <X class="h-5 w-5" />
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-6 py-5">
            <!-- 加载中 -->
            <div v-if="mcpConfigLoading" class="flex items-center justify-center py-10">
              <div class="h-6 w-6 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
            </div>

            <template v-else-if="mcpConnectConfig">
              <!-- 介绍 -->
              <p v-if="mcpConnectConfig.description" class="mb-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-600">{{ mcpConnectConfig.description }}</p>

              <!-- 安装配置 -->
              <div class="mb-4">
                <label class="mb-2 block text-xs font-semibold text-slate-700">{{ t('market.install.config') }}</label>
                <div class="rounded-lg bg-slate-900 p-4">
                  <pre class="whitespace-pre-wrap text-xs leading-relaxed text-green-300">{{ mcpConnectConfig.agent_prompt }}{{ JSON.stringify(mcpConnectConfig.config, null, 2) }}</pre>
                </div>
                <button @click="copyMcpConfig"
                  class="mt-2 rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm">
                  {{ mcpConfigCopied ? t('market.install.copied') : t('market.install.copyConfig') }}
                </button>
              </div>

              <!-- 包含工具（支持多个） -->
              <div v-if="mcpConnectConfig.tools.length" class="mb-4">
                <label class="mb-2 block text-xs font-semibold text-slate-700">{{ t('market.install.tools', { count: mcpConnectConfig.tools.length }) }}</label>
                <div class="space-y-2 rounded-lg bg-slate-50 p-3">
                  <div v-for="tool in mcpConnectConfig.tools" :key="tool.name" class="flex items-baseline gap-2">
                    <span class="inline-block h-1.5 w-1.5 shrink-0 translate-y-[-1px] rounded-full bg-purple-400" />
                    <div class="min-w-0 flex-1">
                      <span class="text-xs font-medium text-slate-800">{{ tool.name }}</span>
                      <span v-if="tool.description" class="ml-1.5 text-xs text-slate-500">{{ tool.description }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 使用说明 -->
              <div v-if="mcpConnectConfig.instructions">
                <label class="mb-2 block text-xs font-semibold text-slate-700">{{ t('market.install.instructions') }}</label>
                <div class="rounded-lg bg-slate-50 px-4 py-3 text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">{{ mcpConnectConfig.instructions }}</div>
              </div>
            </template>
          </div>

          <div class="flex justify-end border-t border-slate-100 px-6 py-3">
            <button class="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100" @click="showMcpAccessDialog = false">{{ t('market.action.close') }}</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Skill Install Dialog -->
    <Teleport to="body">
      <div v-if="showSkillInstallDialog && skillTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" @click.self="showSkillInstallDialog = false">
        <div class="flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl border border-slate-200/60 bg-white/90 shadow-xl backdrop-blur">
            <div class="flex items-center justify-between gap-4 border-b border-slate-100 px-6 py-4">
              <div class="flex min-w-0 items-center gap-2">
                <h3 class="truncate text-lg font-semibold text-slate-800">{{ skillTarget.name }}</h3>
                <span v-if="getSkillDialogAuthor()" class="max-w-[6em] shrink-0 truncate text-xs text-slate-400">{{ getSkillDialogAuthor() }}</span>
                <span class="flex shrink-0 items-center gap-1 text-xs text-slate-400 tabular-nums">
                  <Flame class="h-3.5 w-3.5 text-orange-500" />
                  {{ formatUsageCount(getSkillDialogUsageCount()) }}
                </span>
              </div>
            <button class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" @click="showSkillInstallDialog = false">
              <X class="h-5 w-5" />
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-6 py-5">
            <div v-if="skillInstallLoading" class="flex items-center justify-center py-10">
              <div class="h-6 w-6 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
            </div>

            <template v-else-if="skillInstallInfo">
              <!-- 介绍 -->
              <p v-if="skillInstallInfo.description" class="mb-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-600">{{ skillInstallInfo.description }}</p>

              <!-- Agent Prompt -->
              <div class="mb-4">
                <label class="mb-2 block text-xs font-semibold text-slate-700">{{ t('market.skill.agentPrompt') }}</label>
                <div class="rounded-lg bg-slate-900 p-4">
                  <pre class="whitespace-pre-wrap text-xs leading-relaxed text-green-300">{{ skillInstallInfo.agent_prompt }}</pre>
                </div>
                <button @click="copySkillPrompt"
                  class="mt-2 rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm">
                  {{ skillPromptCopied ? t('market.install.copied') : t('market.skill.copyPrompt') }}
                </button>
              </div>

              <!-- 使用说明 -->
              <div v-if="skillInstallInfo.usage_instructions">
                <label class="mb-2 block text-xs font-semibold text-slate-700">{{ t('market.install.instructions') }}</label>
                <div class="rounded-lg bg-slate-50 px-4 py-3 text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">{{ skillInstallInfo.usage_instructions }}</div>
              </div>
            </template>
          </div>

          <div class="flex justify-end border-t border-slate-100 px-6 py-3">
            <button class="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100" @click="showSkillInstallDialog = false">{{ t('market.action.close') }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
