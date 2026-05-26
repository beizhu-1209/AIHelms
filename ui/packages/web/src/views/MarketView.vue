<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getMyKeys } from '@aihelms/shared'
import { request } from '@aihelms/shared/src/api/request'
import { createResourceApplication } from '@aihelms/shared/src/api/resource-application'
import type { AiKey } from '@aihelms/shared/src/types/ai-key'
import type { Skill } from '@aihelms/shared/src/types/skill'
import type { McpServer } from '@aihelms/shared/src/types/mcp'
import { Server, Sparkles, CheckCircle2, Search, X, ExternalLink } from 'lucide-vue-next'
import * as lucideIcons from 'lucide-vue-next'

type MarketItem = (Skill & { _type: 'skill' }) | (McpServer & { _type: 'mcp' })

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
const mcpTarget = ref<McpServer | null>(null)
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
  if (item._type === 'mcp') return (item as unknown as McpServer).icon_url || ''
  return ''
}

function getSkillIcon(item: MarketItem): string {
  if (item._type === 'skill') return (item as unknown as Skill).icon || ''
  return ''
}

function getLucideIcon(name: string) {
  return (lucideIcons as Record<string, unknown>)[name] || null
}

async function handleCopyPrompt(item: MarketItem) {
  if (item._type !== 'skill') return
  skillTarget.value = item as unknown as Skill
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
}

const showSkillInstallDialog = ref(false)
const skillTarget = ref<Skill | null>(null)
const skillInstallInfo = ref<SkillInstallInfo | null>(null)
const skillInstallLoading = ref(false)
const skillPromptCopied = ref(false)

function handleViewAccess(item: MarketItem) {
  if (item._type !== 'mcp') return
  mcpTarget.value = item as unknown as McpServer
  mcpConnectConfig.value = null
  showMcpAccessDialog.value = true
  loadMcpConfig(item.id)
}

const mcpConnectConfig = ref<{ name: string; description: string; agent_prompt: string; config: Record<string, unknown>; instructions: string; tools: Array<{ name: string; description: string }> } | null>(null)
const mcpConfigLoading = ref(false)
const mcpConfigCopied = ref(false)

async function loadMcpConfig(serverId: number) {
  mcpConfigLoading.value = true
  try {
    const res = await request<{ name: string; description: string; agent_prompt: string; config: Record<string, unknown>; instructions: string; tools: Array<{ name: string; description: string }> }>(`/api/v1/mcp/servers/${serverId}/connect-config`)
    mcpConnectConfig.value = res
  } catch { /* */ }
  finally { mcpConfigLoading.value = false }
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
    const [skillRes, mcpRes, keysRes] = await Promise.all([
      request<{ items: Skill[] }>('/api/v1/skills/published', { params: { page_size: 100 } }),
      request<{ items: McpServer[] }>('/api/v1/mcp/servers/published', { params: { page_size: 100 } }),
      getMyKeys(),
    ])
    const skillItems: MarketItem[] = (skillRes?.items ?? []).map(s => ({ ...s, _type: 'skill' as const }))
    const mcpItems: MarketItem[] = (mcpRes?.items ?? []).map(m => ({ ...m, _type: 'mcp' as const }))
    items.value = [...skillItems, ...mcpItems]

    const mainKey = keysRes.personal?.find((k: AiKey) => k.key_type === 'personal_main')
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
      <h1 class="text-2xl font-bold text-slate-800">AI 市场</h1>
    </div>

    <!-- Filters -->
    <div class="space-y-4">
      <!-- Type filter + Search -->
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-1 rounded-xl bg-white/70 p-1 backdrop-blur border border-slate-200/60">
          <button
            v-for="opt in [{ key: 'all', label: '全部' }, { key: 'skill', label: 'Skill' }, { key: 'mcp', label: 'MCP' }]"
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
            placeholder="搜索名称或描述..."
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
          全部分类
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
      暂无可用资源
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
            <component
              :is="getLucideIcon(getIconUrl(item) || getSkillIcon(item))"
              v-if="getLucideIcon(getIconUrl(item) || getSkillIcon(item))"
              class="h-5 w-5 text-purple-600"
            />
            <Server v-else-if="item._type === 'mcp'" class="h-5 w-5 text-blue-600" />
            <Sparkles v-else class="h-5 w-5 text-purple-600" />
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
        <h3 class="mb-1 text-sm font-semibold text-slate-800 line-clamp-1">{{ item.name }}</h3>
        <p v-if="item.category" class="mb-2 text-xs text-slate-400">{{ item.category }}</p>

        <!-- Tags -->
        <div v-if="getTags(item).length" class="mb-2 flex flex-wrap gap-1">
          <span
            v-for="tag in getTags(item)"
            :key="tag"
            class="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500"
          >
            {{ tag }}
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
            安装 Skill
          </button>
          <button
            v-else-if="(isOwned(item) || !item.requires_approval) && item._type === 'mcp'"
            class="flex items-center gap-1 rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm transition-transform hover:scale-105"
            @click="handleViewAccess(item)"
          >
            <ExternalLink class="h-3 w-3" />
            查看接入信息
          </button>
          <button
            v-else
            class="rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm transition-transform hover:scale-105"
            @click="handleApply(item)"
          >
            申请使用
          </button>
        </div>
      </div>
    </div>

    <!-- Apply Dialog -->
    <Teleport to="body">
      <div v-if="showApplyDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" @click.self="showApplyDialog = false">
        <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-lg font-semibold text-slate-800">申请使用</h3>
            <button class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" @click="showApplyDialog = false">
              <X class="h-5 w-5" />
            </button>
          </div>
          <p class="mb-3 text-sm text-slate-500">
            申请使用「{{ applyTarget?.name }}」，请填写申请理由：
          </p>
          <textarea
            v-model="applyReason"
            rows="4"
            placeholder="请描述使用场景和理由..."
            class="w-full rounded-xl border border-slate-200/60 bg-white/70 px-4 py-3 text-sm backdrop-blur placeholder:text-slate-400 focus:border-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
          />
          <div class="mt-4 flex justify-end gap-3">
            <button
              class="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
              @click="showApplyDialog = false"
            >
              取消
            </button>
            <button
              class="rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-50"
              :disabled="!applyReason.trim() || applyingId !== null"
              @click="submitApply"
            >
              {{ applyingId !== null ? '提交中...' : '提交申请' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- MCP Access Dialog -->
    <Teleport to="body">
      <div v-if="showMcpAccessDialog && mcpTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" @click.self="showMcpAccessDialog = false">
        <div class="flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl border border-slate-200/60 bg-white/90 shadow-xl backdrop-blur">
          <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <h3 class="text-lg font-semibold text-slate-800">{{ mcpTarget.name }}</h3>
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
                <label class="mb-2 block text-xs font-semibold text-slate-700">安装配置</label>
                <div class="rounded-lg bg-slate-900 p-4">
                  <pre class="whitespace-pre-wrap text-xs leading-relaxed text-green-300">{{ mcpConnectConfig.agent_prompt }}{{ JSON.stringify(mcpConnectConfig.config, null, 2) }}</pre>
                </div>
                <button @click="copyMcpConfig"
                  class="mt-2 rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm">
                  {{ mcpConfigCopied ? '已复制' : '复制安装配置' }}
                </button>
              </div>

              <!-- 包含工具（支持多个） -->
              <div v-if="mcpConnectConfig.tools.length" class="mb-4">
                <label class="mb-2 block text-xs font-semibold text-slate-700">包含工具（{{ mcpConnectConfig.tools.length }}）</label>
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
                <label class="mb-2 block text-xs font-semibold text-slate-700">使用说明</label>
                <div class="rounded-lg bg-slate-50 px-4 py-3 text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">{{ mcpConnectConfig.instructions }}</div>
              </div>
            </template>
          </div>

          <div class="flex justify-end border-t border-slate-100 px-6 py-3">
            <button class="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100" @click="showMcpAccessDialog = false">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Skill Install Dialog -->
    <Teleport to="body">
      <div v-if="showSkillInstallDialog && skillTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" @click.self="showSkillInstallDialog = false">
        <div class="flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl border border-slate-200/60 bg-white/90 shadow-xl backdrop-blur">
          <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <h3 class="text-lg font-semibold text-slate-800">{{ skillTarget.name }}</h3>
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
                <label class="mb-2 block text-xs font-semibold text-slate-700">Agent 安装提示词</label>
                <div class="rounded-lg bg-slate-900 p-4">
                  <pre class="whitespace-pre-wrap text-xs leading-relaxed text-green-300">{{ skillInstallInfo.agent_prompt }}</pre>
                </div>
                <button @click="copySkillPrompt"
                  class="mt-2 rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-1.5 text-xs font-medium text-white shadow-sm">
                  {{ skillPromptCopied ? '已复制' : '复制安装提示词' }}
                </button>
              </div>

              <!-- 使用说明 -->
              <div v-if="skillInstallInfo.usage_instructions">
                <label class="mb-2 block text-xs font-semibold text-slate-700">使用说明</label>
                <div class="rounded-lg bg-slate-50 px-4 py-3 text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">{{ skillInstallInfo.usage_instructions }}</div>
              </div>
            </template>
          </div>

          <div class="flex justify-end border-t border-slate-100 px-6 py-3">
            <button class="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100" @click="showSkillInstallDialog = false">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

