<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMyKeys } from '@aihelms/shared'
import { request } from '@aihelms/shared/src/api/request'
import { createResourceApplication } from '@aihelms/shared/src/api/resource-application'
import type { AiKey } from '@aihelms/shared/src/types/ai-key'
import { Cpu, CheckCircle2, Search, Copy, Check, X, Eye, EyeOff } from 'lucide-vue-next'
import ProviderIcon from '../components/ProviderIcon.vue'

const { t } = useI18n()
const openAiClients = ['Workbuddy', 'Qcoder', 'Openclaw', 'Dify', 'FastGPT', 'LobeChat', 'Cherry Studio']
const anthropicClients = ['Claude Code', 'Claude Desktop']

interface ModelItem {
  id: number
  name: string
  model_id: string
  model_id_anthropic: string | null
  category: string
  capabilities: string[]
  description: string
  logo_provider_type: string
  icon_url: string
  base_url: string
  is_published: boolean
  requires_approval: boolean
  deployment_count: number
  has_anthropic_deployment: boolean
}


const models = ref<ModelItem[]>([])
const myModels = ref<string[]>([])
const mainKeyValue = ref('')
const litellmBaseUrl = ref('')
const isLoading = ref(true)
const search = ref('')
const categoryFilter = ref('')
const capabilityFilter = ref('')
const showApplyDialog = ref(false)
const showAccessDialog = ref(false)
const activeModel = ref<ModelItem | null>(null)
const applyReason = ref('')
const applyingId = ref<number | null>(null)
const copied = ref<string | null>(null)
const showKeyFull = ref(false)

const categories = computed(() => {
  const set = new Set(models.value.map(m => m.category).filter(Boolean))
  return Array.from(set).sort()
})

const capabilities = computed(() => {
  const set = new Set(models.value.flatMap(m => m.capabilities || []))
  return Array.from(set).sort()
})

const filtered = computed(() => {
  return models.value.filter(m => {
    if (categoryFilter.value && m.category !== categoryFilter.value) return false
    if (capabilityFilter.value && !(m.capabilities || []).includes(capabilityFilter.value)) return false
    if (search.value) {
      const q = search.value.toLowerCase()
      if (!m.name.toLowerCase().includes(q) && !m.model_id.toLowerCase().includes(q)
        && !m.description?.toLowerCase().includes(q)) return false
    }
    return true
  })
})

function isOwned(modelId: string): boolean { return myModels.value.includes(modelId) }

function handleUse(model: ModelItem): void {
  activeModel.value = model
  showAccessDialog.value = true
}

function handleApply(model: ModelItem): void {
  activeModel.value = model
  applyReason.value = ''
  showApplyDialog.value = true
}

async function submitApply(): Promise<void> {
  if (!activeModel.value) return
  applyingId.value = activeModel.value.id
  try {
    await createResourceApplication({
      resource_type: 'model',
      resource_id: activeModel.value.id,
      reason: applyReason.value,
    })
    showApplyDialog.value = false
  } finally { applyingId.value = null }
}

async function copyText(text: string, key: string): Promise<void> {
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
    copied.value = key
    setTimeout(() => { copied.value = null }, 2000)
  } catch { /* ignore */ }
}

onMounted(async () => {
  try {
    const [modelsData, keysData, configData] = await Promise.all([
      request<ModelItem[]>('/api/v1/models/active'),
      getMyKeys(),
      request<{ litellm_base_url: string }>('/api/v1/config/public'),
    ])
    models.value = modelsData
    const mainKey = keysData.personal.find((k: AiKey) => k.key_type === 'personal_main')
    myModels.value = mainKey?.models ?? []
    mainKeyValue.value = mainKey?.key_value || mainKey?.litellm_key_id || ''
    litellmBaseUrl.value = configData.litellm_base_url || ''
  } catch { /* */ }
  finally { isLoading.value = false }
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-6 py-8">
    <div class="mb-6">
      <h1 class="text-xl font-bold text-slate-900">{{ t('modelSquare.title') }}</h1>
      <p class="mt-1 text-sm text-slate-500">{{ t('modelSquare.subtitle') }}</p>
    </div>

    <!-- 搜索 + 分类筛选 -->
    <div class="mb-5 space-y-3">
      <div class="relative">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input v-model="search" type="text" :placeholder="t('modelSquare.search.placeholder')"
          class="h-10 w-full max-w-md rounded-lg border border-slate-200/60 bg-white/70 pl-9 pr-3 text-sm backdrop-blur placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
      </div>
      <div class="flex flex-wrap gap-2">
        <button @click="categoryFilter = ''"
          class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
          :class="!categoryFilter ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'">
          {{ t('modelSquare.filter.all') }}
        </button>
        <button v-for="cat in categories" :key="cat" @click="categoryFilter = cat"
          class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
          :class="categoryFilter === cat ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'">
          {{ cat }}
        </button>
      </div>
      <div v-if="capabilities.length" class="flex flex-wrap gap-2">
        <span class="text-xs text-slate-400 leading-6">{{ t('modelSquare.filter.capability') }}</span>
        <button @click="capabilityFilter = ''"
          class="rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors"
          :class="!capabilityFilter ? 'bg-blue-100 text-blue-700' : 'bg-slate-50 text-slate-500 hover:bg-slate-100'">
          {{ t('modelSquare.filter.all') }}
        </button>
        <button v-for="cap in capabilities" :key="cap" @click="capabilityFilter = cap"
          class="rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors"
          :class="capabilityFilter === cap ? 'bg-blue-100 text-blue-700' : 'bg-slate-50 text-slate-500 hover:bg-slate-100'">
          {{ cap }}
        </button>
      </div>
    </div>

    <!-- 卡片网格 -->
    <div v-if="isLoading" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="i in 6" :key="i" class="h-56 animate-pulse rounded-2xl bg-white/70" />
    </div>
    <div v-else-if="!filtered.length" class="rounded-2xl border border-slate-200/60 bg-white/70 p-12 text-center backdrop-blur">
      <Cpu class="mx-auto h-10 w-10 text-slate-300" />
      <p class="mt-3 text-sm text-slate-400">{{ t('modelSquare.empty') }}</p>
    </div>
    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="model in filtered" :key="model.id"
        class="group flex min-h-[220px] flex-col rounded-2xl border border-slate-200/60 bg-white/70 p-5 backdrop-blur transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-500/5">
        <!-- 头部 -->
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-purple-50 to-blue-50">
            <ProviderIcon :src="model.icon_url" :type="model.logo_provider_type" :size="22" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <h3 class="truncate text-sm font-semibold text-slate-900">{{ model.name }}</h3>
              <CheckCircle2 v-if="isOwned(model.model_id)" class="h-3.5 w-3.5 shrink-0 text-green-500" />
            </div>
            <p class="truncate text-xs text-slate-400">{{ model.model_id }}</p>
          </div>
        </div>

        <!-- 标签 -->
        <div class="mt-3 flex flex-wrap gap-1.5">
          <span class="rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">{{ model.category }}</span>
          <span v-for="cap in model.capabilities?.slice(0, 3)" :key="cap"
            class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{{ cap }}</span>
        </div>

        <!-- 描述 -->
        <p class="mt-2.5 flex-1 text-xs leading-relaxed text-slate-500">{{ model.description || t('modelSquare.fallback.noDescription') }}</p>

        <!-- 底部操作 -->
        <div class="mt-4 border-t border-slate-100 pt-3">
          <button v-if="isOwned(model.model_id) || !model.requires_approval" @click="handleUse(model)"
            class="w-full rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 py-2 text-xs font-medium text-white opacity-0 shadow-sm transition-opacity group-hover:opacity-100">
            {{ t('modelSquare.action.viewAccess') }}
          </button>
          <button v-else @click="handleApply(model)"
            class="w-full rounded-lg border border-purple-200 bg-purple-50 py-2 text-xs font-medium text-purple-700 opacity-0 transition-opacity group-hover:opacity-100">
            {{ t('modelSquare.action.apply') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 接入信息弹窗 -->
    <div v-if="showAccessDialog && activeModel" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" @click.self="showAccessDialog = false">
      <div class="flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl border border-slate-200/60 bg-white shadow-2xl">
        <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div class="flex items-center gap-3">
            <ProviderIcon :src="activeModel.icon_url" :type="activeModel.logo_provider_type" :size="24" />
            <h3 class="text-base font-semibold text-slate-900">{{ activeModel.name }}</h3>
          </div>
          <button @click="showAccessDialog = false" class="rounded-lg p-1 hover:bg-slate-100"><X class="h-4 w-4 text-slate-400" /></button>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          <!-- 模型 ID & 适用场景 -->
          <div class="rounded-lg border border-slate-200/60 p-4">
            <h4 class="mb-3 text-xs font-semibold text-slate-700">{{ t('modelSquare.access.modelId') }}</h4>
            <div class="space-y-3">
              <div class="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2.5">
                <div>
                  <code class="text-sm font-medium text-slate-800">{{ activeModel.model_id }}</code>
                  <p class="mt-0.5 text-xs text-slate-400">
                    {{ t('modelSquare.access.openaiClientsPrefix') }}
                    <template v-for="(client, index) in openAiClients" :key="client">
                      <span v-if="index > 0">, </span><strong class="font-bold text-slate-500">{{ client }}</strong>
                    </template>{{ t('modelSquare.access.openaiClientsSuffix') }}
                  </p>
                </div>
                <button @click="copyText(activeModel.model_id, 'model')" class="shrink-0 text-xs text-purple-600 hover:text-purple-700">
                  {{ copied === 'model' ? t('modelSquare.action.copied') : t('modelSquare.action.copy') }}
                </button>
              </div>
              <div v-if="activeModel.model_id_anthropic" class="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2.5">
                <div>
                  <code class="text-sm font-medium text-slate-800">{{ activeModel.model_id_anthropic }}</code>
                  <p class="mt-0.5 text-xs text-slate-400">
                    {{ t('modelSquare.access.anthropicClientsPrefix') }}
                    <template v-for="(client, index) in anthropicClients" :key="client">
                      <span v-if="index > 0">, </span><strong class="font-bold text-slate-500">{{ client }}</strong>
                    </template>{{ t('modelSquare.access.anthropicClientsSuffix') }}
                  </p>
                </div>
                <button @click="copyText(activeModel.model_id_anthropic, 'model-cc')" class="shrink-0 text-xs text-purple-600 hover:text-purple-700">
                  {{ copied === 'model-cc' ? t('modelSquare.action.copied') : t('modelSquare.action.copy') }}
                </button>
              </div>
            </div>
          </div>
          <div class="rounded-lg bg-slate-50 p-4">
            <div class="mb-1 flex items-center justify-between">
              <span class="text-xs font-medium text-slate-500">API Key</span>
              <div class="flex items-center gap-2">
                <button v-if="mainKeyValue" @click="showKeyFull = !showKeyFull"
                  class="flex items-center justify-center rounded p-0.5 text-slate-400 transition-colors hover:text-slate-600">
                  <EyeOff v-if="showKeyFull" class="h-3.5 w-3.5" />
                  <Eye v-else class="h-3.5 w-3.5" />
                </button>
                <button @click="copyText(mainKeyValue, 'key')" class="text-xs text-purple-600 hover:text-purple-700">
                  {{ copied === 'key' ? t('modelSquare.action.copied') : t('modelSquare.action.copy') }}
                </button>
              </div>
            </div>
            <code class="block break-all text-sm text-slate-800">{{ mainKeyValue ? (showKeyFull ? mainKeyValue : mainKeyValue.slice(0, 8) + '****' + mainKeyValue.slice(-4)) : t('modelSquare.fallback.noKey') }}</code>
          </div>
          <div class="rounded-lg bg-slate-50 p-4">
            <div class="mb-1 flex items-center justify-between">
              <span class="text-xs font-medium text-slate-500">Base URL</span>
              <button @click="copyText(activeModel.base_url || litellmBaseUrl, 'url')" class="text-xs text-purple-600 hover:text-purple-700">
                {{ copied === 'url' ? t('modelSquare.action.copied') : t('modelSquare.action.copy') }}
              </button>
            </div>
            <code class="text-sm text-slate-800">{{ activeModel.base_url || litellmBaseUrl || t('modelSquare.fallback.notConfigured') }}</code>
          </div>


        </div>
      </div>
    </div>

    <!-- 申请弹窗 -->
    <div v-if="showApplyDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white p-6 shadow-2xl">
        <div class="flex items-center justify-between">
          <h3 class="text-base font-semibold text-slate-900">{{ t('modelSquare.apply.title', { name: activeModel?.name || '' }) }}</h3>
          <button @click="showApplyDialog = false" class="rounded-lg p-1 hover:bg-slate-100"><X class="h-4 w-4 text-slate-400" /></button>
        </div>
        <textarea v-model="applyReason" rows="3" :placeholder="t('modelSquare.apply.placeholder')"
          class="mt-4 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
        <div class="mt-4 flex justify-end gap-2">
          <button @click="showApplyDialog = false" class="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">{{ t('common.action.cancel') }}</button>
          <button @click="submitApply" :disabled="applyingId !== null"
            class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-50">
            {{ applyingId ? t('modelSquare.apply.submitting') : t('modelSquare.apply.submit') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
