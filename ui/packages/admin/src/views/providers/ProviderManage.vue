<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  getProviders,
  createProvider,
  updateProvider,
  deleteProvider,
  getCredentials,
  createCredential,
  updateCredential,
  deleteCredential,
  type Provider,
  type Credential,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import ProviderIcon from '../../components/ProviderIcon.vue'

const { hasPermission } = usePermission()

// --- Providers ---
const providers = ref<Provider[]>([])
const selectedProvider = ref<Provider | null>(null)
const showProviderForm = ref(false)
const isEditingProvider = ref(false)
const editingProviderId = ref<number | null>(null)
const deleteProviderTarget = ref<Provider | null>(null)
const providerError = ref('')

const formName = ref('')
const formType = ref('openai')
const formFormats = ref<string[]>([])
const formDescription = ref('')

// --- Credentials ---
const providerCredentials = ref<Credential[]>([])
const showCredForm = ref(false)
const isEditingCred = ref(false)
const editingCredId = ref<number | null>(null)
const deleteCredTarget = ref<Credential | null>(null)
const credError = ref('')

const credFormName = ref('')
const credFormFormat = ref('')
const credFormApiBase = ref('')
const credFormApiKey = ref('')
// 高级设置
const credFormBillingType = ref('token')
const credFormTokenPricingMode = ref('unified')
const credFormInputCost = ref('')
const credFormOutputCost = ref('')
const credFormCacheReadCost = ref('')
const credFormCostPerCall = ref('')
const credFormMonthlyQuota = ref('')
const credFormRpm = ref('')
const credFormTpm = ref('')
const credFormMaxParallel = ref('')
const showCredAdvanced = ref(false)

const providerTypes = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'azure', label: 'Azure' },
  { value: 'google', label: 'Google' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'bedrock', label: 'AWS Bedrock' },
  { value: 'vertex_ai', label: 'Vertex AI' },
  { value: 'volcengine', label: '火山引擎' },
  { value: 'dashscope', label: '百炼' },
  { value: 'zhipu', label: '智谱' },
  { value: 'moonshot', label: 'Moonshot' },
  { value: 'minimax', label: 'MiniMax' },
  { value: 'vllm', label: 'vLLM' },
  { value: 'sglang', label: 'SGLang' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'lmstudio', label: 'LM Studio' },
  { value: 'other', label: '其他' },
]

const accessFormats = [
  { value: 'openai', label: 'OpenAI', needsKey: true },
  { value: 'anthropic', label: 'Anthropic', needsKey: true },
  { value: 'lmstudio', label: 'LM Studio', needsKey: true },
  { value: 'ollama', label: 'Ollama', needsKey: false },
]

const availableFormats = computed(() => {
  if (!selectedProvider.value) return []
  const formats = (selectedProvider.value.config?.supported_formats as string[]) || []
  return accessFormats.filter(f => formats.includes(f.value))
})

const selectedFormatNeedsKey = computed(() => {
  const fmt = accessFormats.find(f => f.value === credFormFormat.value)
  return fmt?.needsKey !== false
})

function getProviderTypeLabel(type: string): string {
  const item = providerTypes.find(t => t.value === type)
  return item?.label || type
}

function getFormatLabel(format: string): string {
  const item = accessFormats.find(f => f.value === format)
  return item?.label || format
}

function toggleFormat(value: string): void {
  const idx = formFormats.value.indexOf(value)
  if (idx >= 0) {
    formFormats.value.splice(idx, 1)
  } else {
    formFormats.value.push(value)
  }
}

// --- Provider methods ---
async function fetchProviders(): Promise<void> {
  const result = await getProviders(1, 100)
  providers.value = result.items
}

function handleSelectProviderItem(provider: Provider): void {
  selectedProvider.value = provider
  fetchProviderCredentials(provider.id)
}

async function fetchProviderCredentials(providerId: number): Promise<void> {
  const result = await getCredentials(1, 100, providerId)
  providerCredentials.value = result.items
}

function handleCreateProvider(): void {
  isEditingProvider.value = false
  editingProviderId.value = null
  formName.value = ''
  formType.value = 'openai'
  formFormats.value = []
  formDescription.value = ''
  providerError.value = ''
  showProviderForm.value = true
}

function handleEditProvider(): void {
  if (!selectedProvider.value) return
  isEditingProvider.value = true
  editingProviderId.value = selectedProvider.value.id
  formName.value = selectedProvider.value.name
  formType.value = selectedProvider.value.provider_type
  formFormats.value = [...((selectedProvider.value.config?.supported_formats as string[]) || [])]
  formDescription.value = selectedProvider.value.description || ''
  providerError.value = ''
  showProviderForm.value = true
}

async function handleSubmitProvider(): Promise<void> {
  providerError.value = ''
  if (!formName.value) {
    providerError.value = '请输入供应商名称'
    return
  }
  if (formFormats.value.length === 0) {
    providerError.value = '请至少选择一种接入格式'
    return
  }
  try {
    const params = {
      name: formName.value,
      provider_type: formType.value,
      description: formDescription.value || undefined,
      config: { supported_formats: formFormats.value },
    }
    if (isEditingProvider.value && editingProviderId.value) {
      await updateProvider(editingProviderId.value, params)
    } else {
      await createProvider(params)
    }
    showProviderForm.value = false
    await fetchProviders()
    if (selectedProvider.value && isEditingProvider.value) {
      selectedProvider.value = providers.value.find(p => p.id === selectedProvider.value?.id) || null
    }
  } catch (e) {
    providerError.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleToggleProvider(provider: Provider): Promise<void> {
  await updateProvider(provider.id, { is_active: !provider.is_active })
  await fetchProviders()
}

async function handleConfirmDeleteProvider(): Promise<void> {
  if (!deleteProviderTarget.value) return
  try {
    await deleteProvider(deleteProviderTarget.value.id)
    if (selectedProvider.value?.id === deleteProviderTarget.value.id) {
      selectedProvider.value = null
      providerCredentials.value = []
    }
    deleteProviderTarget.value = null
    await fetchProviders()
  } catch (e) {
    providerError.value = e instanceof Error ? e.message : '删除失败'
    deleteProviderTarget.value = null
  }
}

// --- Credential methods ---

function handleCreateCred(): void {
  if (!selectedProvider.value) return
  isEditingCred.value = false
  editingCredId.value = null
  credFormName.value = ''
  credFormFormat.value = availableFormats.value.length === 1 ? availableFormats.value[0].value : ''
  credFormApiBase.value = ''
  credFormApiKey.value = ''
  credFormBillingType.value = 'token'
  credFormTokenPricingMode.value = 'unified'
  credFormInputCost.value = ''
  credFormOutputCost.value = ''
  credFormCacheReadCost.value = ''
  credFormCostPerCall.value = ''
  credFormMonthlyQuota.value = ''
  credFormRpm.value = ''
  credFormTpm.value = ''
  credFormMaxParallel.value = ''
  showCredAdvanced.value = false
  credError.value = ''
  showCredForm.value = true
}

function handleEditCred(cred: Credential): void {
  isEditingCred.value = true
  editingCredId.value = cred.id
  credFormName.value = cred.credential_name
  credFormFormat.value = (cred.credential_info?.format as string) || (cred.credential_info?.custom_llm_provider as string) || ''
  credFormApiBase.value = (cred.credential_info?.api_base as string) || ''
  credFormApiKey.value = ''
  const info = cred.credential_info || {}
  credFormBillingType.value = (info.billing_type as string) || 'token'
  credFormTokenPricingMode.value = (info.token_pricing_mode as string) || 'unified'
  credFormInputCost.value = info.input_cost_per_token ? String(info.input_cost_per_token) : ''
  credFormOutputCost.value = info.output_cost_per_token ? String(info.output_cost_per_token) : ''
  credFormCacheReadCost.value = info.cache_read_cost_per_token ? String(info.cache_read_cost_per_token) : ''
  credFormCostPerCall.value = info.cost_per_call ? String(info.cost_per_call) : ''
  credFormMonthlyQuota.value = info.monthly_call_quota ? String(info.monthly_call_quota) : ''
  credFormRpm.value = info.rpm ? String(info.rpm) : ''
  credFormTpm.value = info.tpm ? String(info.tpm) : ''
  credFormMaxParallel.value = info.max_parallel_requests ? String(info.max_parallel_requests) : ''
  showCredAdvanced.value = !!(credFormRpm.value || credFormTpm.value || credFormInputCost.value || credFormCostPerCall.value)
  credError.value = ''
  showCredForm.value = true
}

function getLitellmProvider(format: string): string {
  if (format === 'lmstudio') return 'openai'
  return format
}

async function handleSubmitCred(): Promise<void> {
  credError.value = ''
  if (!credFormName.value) {
    credError.value = '请输入凭证名称'
    return
  }
  if (!credFormFormat.value) {
    credError.value = '请选择接入格式'
    return
  }
  if (!credFormApiBase.value) {
    credError.value = '请填写 API Base'
    return
  }
  if (selectedFormatNeedsKey.value && !credFormApiKey.value && !isEditingCred.value) {
    credError.value = '请填写 API Key'
    return
  }

  const credValues: Record<string, string> = {}
  if (credFormApiKey.value) credValues.api_key = credFormApiKey.value
  if (credFormApiBase.value) credValues.api_base = credFormApiBase.value

  const credInfo: Record<string, unknown> = {
    custom_llm_provider: getLitellmProvider(credFormFormat.value),
    format: credFormFormat.value,
    api_base: credFormApiBase.value,
    billing_type: credFormBillingType.value,
  }
  if (credFormBillingType.value === 'token') {
    credInfo.token_pricing_mode = credFormTokenPricingMode.value
    if (credFormTokenPricingMode.value === 'unified') {
      if (credFormInputCost.value) credInfo.input_cost_per_token = Number(credFormInputCost.value)
      if (credFormOutputCost.value) credInfo.output_cost_per_token = Number(credFormOutputCost.value)
      if (credFormCacheReadCost.value) credInfo.cache_read_cost_per_token = Number(credFormCacheReadCost.value)
    }
  } else if (credFormBillingType.value === 'per_call') {
    if (credFormCostPerCall.value) credInfo.cost_per_call = Number(credFormCostPerCall.value)
  } else if (credFormBillingType.value === 'monthly_quota') {
    if (credFormMonthlyQuota.value) credInfo.monthly_call_quota = Number(credFormMonthlyQuota.value)
  }
  if (credFormRpm.value) credInfo.rpm = Number(credFormRpm.value)
  if (credFormTpm.value) credInfo.tpm = Number(credFormTpm.value)
  if (credFormMaxParallel.value) credInfo.max_parallel_requests = Number(credFormMaxParallel.value)

  try {
    if (isEditingCred.value && editingCredId.value) {
      const params: Record<string, unknown> = { credential_info: credInfo }
      if (Object.keys(credValues).length > 0) params.credential_values = credValues
      await updateCredential(editingCredId.value, params)
    } else {
      await createCredential({
        credential_name: credFormName.value,
        credential_values: credValues,
        provider_id: selectedProvider.value!.id,
        credential_info: credInfo,
      })
    }
    showCredForm.value = false
    if (selectedProvider.value) await fetchProviderCredentials(selectedProvider.value.id)
  } catch (e) {
    credError.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleToggleCred(cred: Credential): Promise<void> {
  await updateCredential(cred.id, { is_active: !cred.is_active })
  if (selectedProvider.value) await fetchProviderCredentials(selectedProvider.value.id)
}

async function handleConfirmDeleteCred(): Promise<void> {
  if (!deleteCredTarget.value) return
  try {
    await deleteCredential(deleteCredTarget.value.id)
    deleteCredTarget.value = null
    if (selectedProvider.value) await fetchProviderCredentials(selectedProvider.value.id)
  } catch (e) {
    credError.value = e instanceof Error ? e.message : '删除失败'
    deleteCredTarget.value = null
  }
}

onMounted(() => {
  fetchProviders()
})
</script>

<template>
  <div class="flex h-full gap-4 overflow-hidden">
    <!-- 左侧：供应商列表 -->
    <div class="w-80 shrink-0 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
        <h3 class="text-sm font-semibold text-slate-900">供应商</h3>
        <button
          v-if="hasPermission('user:update')"
          class="rounded-md bg-purple-600 px-2.5 py-1 text-xs font-medium text-white transition-all hover:bg-purple-500"
          @click="handleCreateProvider"
        >
          新建
        </button>
      </div>
      <div class="overflow-y-auto p-2" style="max-height: calc(100vh - 10rem)">
        <div
          v-for="provider in providers"
          :key="provider.id"
          class="group mb-1 flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 transition-colors"
          :class="selectedProvider?.id === provider.id ? 'bg-purple-50 ring-1 ring-purple-200' : 'hover:bg-slate-50'"
          @click="handleSelectProviderItem(provider)"
        >
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100">
            <ProviderIcon :type="provider.provider_type" :size="20" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-sm font-medium text-slate-900">{{ provider.name }}</span>
              <span
                v-if="!provider.is_active"
                class="shrink-0 rounded bg-slate-100 px-1 py-0.5 text-[10px] text-slate-400"
              >禁用</span>
            </div>
            <div class="mt-0.5 flex items-center gap-2 text-xs text-slate-400">
              <span>{{ getProviderTypeLabel(provider.provider_type) }}</span>
              <span v-if="provider.credential_count" class="text-purple-500">{{ provider.credential_count }} 凭证</span>
            </div>
          </div>
        </div>
        <div v-if="providers.length === 0" class="py-8 text-center text-sm text-slate-400">暂无供应商</div>
      </div>
    </div>

    <!-- 右侧：凭证管理 -->
    <div class="flex-1 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <template v-if="selectedProvider">
        <!-- 供应商信息头 -->
        <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
          <div class="flex items-center gap-3">
            <span class="text-sm font-semibold text-slate-900">{{ selectedProvider.name }}</span>
            <span class="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">{{ getProviderTypeLabel(selectedProvider.provider_type) }}</span>
            <span
              v-for="fmt in ((selectedProvider.config?.supported_formats as string[]) || [])"
              :key="fmt"
              class="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600"
            >{{ getFormatLabel(fmt) }}</span>
          </div>
          <div class="flex gap-2">
            <button
              v-if="hasPermission('user:update')"
              class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200"
              @click="handleEditProvider"
            >
              编辑
            </button>
            <button
              class="rounded-full px-2 py-0.5 text-xs font-medium transition-colors"
              :class="selectedProvider.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
              @click="handleToggleProvider(selectedProvider)"
            >
              {{ selectedProvider.is_active ? '启用' : '禁用' }}
            </button>
            <button
              v-if="hasPermission('user:delete')"
              class="rounded-md bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-100"
              @click="deleteProviderTarget = selectedProvider"
            >
              删除
            </button>
            <button
              v-if="hasPermission('user:update')"
              class="rounded-md bg-purple-600 px-2.5 py-1 text-xs font-medium text-white transition-all hover:bg-purple-500"
              @click="handleCreateCred"
            >
              新建凭证
            </button>
          </div>
        </div>

        <!-- 凭证列表 -->
        <div class="overflow-y-auto p-4" style="max-height: calc(100vh - 14rem)">
          <div v-if="providerCredentials.length > 0" class="space-y-3">
            <div
              v-for="cred in providerCredentials"
              :key="cred.id"
              class="rounded-xl border border-slate-200/60 bg-white p-4 transition-shadow hover:shadow-sm"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-slate-900">{{ cred.credential_name }}</span>
                    <span class="rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-600">
                      {{ getFormatLabel((cred.credential_info?.format as string) || (cred.credential_info?.custom_llm_provider as string) || '-') }}
                    </span>
                    <span
                      class="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      :class="cred.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-400'"
                    >
                      {{ cred.is_active ? '启用' : '禁用' }}
                    </span>
                  </div>
                  <div v-if="cred.credential_info?.api_base" class="mt-1.5 text-xs text-slate-500">
                    {{ cred.credential_info.api_base }}
                  </div>
                  <div v-if="cred.deployment_count" class="mt-1 text-xs text-slate-400">
                    被 {{ cred.deployment_count }} 个渠道引用
                  </div>
                </div>
                <div class="flex shrink-0 items-center gap-2">
                  <button
                    class="rounded-full px-2 py-0.5 text-xs font-medium transition-colors"
                    :class="cred.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                    @click="handleToggleCred(cred)"
                  >
                    {{ cred.is_active ? '启用' : '禁用' }}
                  </button>
                  <button
                    v-if="hasPermission('user:update')"
                    class="text-xs text-purple-500 transition-colors hover:text-purple-600"
                    @click="handleEditCred(cred)"
                  >
                    编辑
                  </button>
                  <button
                    v-if="hasPermission('user:delete')"
                    class="text-xs text-red-500 transition-colors hover:text-red-600"
                    @click="deleteCredTarget = cred"
                  >
                    删除
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="py-8 text-center text-sm text-slate-400">暂无凭证，点击右上角「新建凭证」添加</div>
        </div>
      </template>
      <template v-else>
        <div class="flex h-full items-center justify-center text-sm text-slate-400">请选择左侧供应商</div>
      </template>
    </div>

    <!-- 供应商表单弹窗 -->
    <div v-if="showProviderForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ isEditingProvider ? '编辑供应商' : '新建供应商' }}</h3>
        <form @submit.prevent="handleSubmitProvider">
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">名称</label>
            <input v-model="formName" placeholder="如：Anthropic 官方" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">类型</label>
            <select v-model="formType" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
              <option v-for="t in providerTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">接入格式 <span class="text-red-400">*</span></label>
            <p class="mb-2 text-xs text-slate-400">选择该供应商支持的接入协议（可多选）</p>
            <div class="flex flex-wrap gap-2">
              <label
                v-for="fmt in accessFormats"
                :key="fmt.value"
                class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors"
                :class="formFormats.includes(fmt.value) ? 'border-purple-300 bg-purple-50 text-purple-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50'"
              >
                <input
                  type="checkbox"
                  :checked="formFormats.includes(fmt.value)"
                  class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
                  @change="toggleFormat(fmt.value)"
                />
                {{ fmt.label }}
              </label>
            </div>
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">描述</label>
            <input v-model="formDescription" placeholder="可选" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <p v-if="providerError" class="mb-3 text-sm text-red-500">{{ providerError }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showProviderForm = false">取消</button>
            <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]">保存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 凭证表单弹窗 -->
    <div v-if="showCredForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ isEditingCred ? '编辑凭证' : '新建凭证' }}</h3>
        <form @submit.prevent="handleSubmitCred">
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">凭证名称</label>
            <input
              v-model="credFormName"
              :disabled="isEditingCred"
              placeholder="唯一标识，如 anthropic-prod"
              class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20 disabled:bg-slate-50 disabled:text-slate-500"
            />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">接入格式 <span class="text-red-400">*</span></label>
            <div v-if="availableFormats.length > 1" class="flex flex-wrap gap-2">
              <button
                v-for="fmt in availableFormats"
                :key="fmt.value"
                type="button"
                class="rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors"
                :class="credFormFormat === fmt.value ? 'border-purple-300 bg-purple-50 text-purple-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50'"
                @click="credFormFormat = fmt.value"
              >{{ fmt.label }}</button>
            </div>
            <div v-else-if="availableFormats.length === 1" class="rounded-lg bg-purple-50 px-3 py-1.5 text-sm font-medium text-purple-700">
              {{ availableFormats[0].label }}
            </div>
            <div v-else class="text-sm text-slate-400">该供应商未配置接入格式</div>
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">API Base <span class="text-red-400">*</span></label>
            <input
              v-model="credFormApiBase"
              placeholder="如 https://api.openai.com/v1"
              class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <div v-if="selectedFormatNeedsKey" class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">API Key <span v-if="!isEditingCred" class="text-red-400">*</span></label>
            <input
              v-model="credFormApiKey"
              type="password"
              :placeholder="isEditingCred ? '留空不修改' : '填写 API Key'"
              class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>

          <!-- 高级设置 -->
          <div class="mb-4">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100"
              @click="showCredAdvanced = !showCredAdvanced"
            >
              <span class="text-xs transition-transform" :class="showCredAdvanced ? 'rotate-90' : ''">▶</span>
              高级设置
              <span class="text-xs text-slate-400">（计费、限流）</span>
            </button>

            <div v-if="showCredAdvanced" class="mt-3 space-y-4 rounded-lg border border-slate-100 p-4">
              <!-- 计费方式 -->
              <div>
                <label class="mb-1.5 block text-sm font-medium text-slate-700">计费方式</label>
                <select v-model="credFormBillingType" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
                  <option value="token">Token 计费</option>
                  <option value="per_call">按次计费</option>
                  <option value="monthly_quota">包月次数</option>
                </select>
              </div>

              <!-- Token 计费模式 -->
              <div v-if="credFormBillingType === 'token'">
                <label class="mb-1.5 block text-sm font-medium text-slate-700">Token 定价模式</label>
                <div class="flex gap-4">
                  <label class="flex items-center gap-2 text-sm text-slate-700">
                    <input v-model="credFormTokenPricingMode" type="radio" value="unified" class="h-4 w-4 border-slate-300 text-purple-600 focus:ring-purple-500/20" />
                    统一定价
                  </label>
                  <label class="flex items-center gap-2 text-sm text-slate-700">
                    <input v-model="credFormTokenPricingMode" type="radio" value="per_model" class="h-4 w-4 border-slate-300 text-purple-600 focus:ring-purple-500/20" />
                    按模型定价
                  </label>
                </div>
                <p class="mt-1 text-xs text-slate-400">
                  {{ credFormTokenPricingMode === 'unified' ? '所有模型使用同一价格，在此设置' : '不同模型不同价格，在模型渠道中设置' }}
                </p>
              </div>

              <!-- 统一定价字段 -->
              <div v-if="credFormBillingType === 'token' && credFormTokenPricingMode === 'unified'">
                <div class="grid grid-cols-3 gap-3">
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">Input (¥/token)</label>
                    <input v-model="credFormInputCost" type="number" step="0.0000001" placeholder="如 0.00002" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">Output (¥/token)</label>
                    <input v-model="credFormOutputCost" type="number" step="0.0000001" placeholder="如 0.0001" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">Cache Read</label>
                    <input v-model="credFormCacheReadCost" type="number" step="0.0000001" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                </div>
              </div>

              <!-- 按次计费 -->
              <div v-if="credFormBillingType === 'per_call'">
                <label class="mb-1 block text-xs text-slate-500">单次费用 (¥)</label>
                <input v-model="credFormCostPerCall" type="number" step="0.01" placeholder="每次调用费用" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
              </div>

              <!-- 包月次数 -->
              <div v-if="credFormBillingType === 'monthly_quota'">
                <label class="mb-1 block text-xs text-slate-500">月调用次数上限</label>
                <input v-model="credFormMonthlyQuota" type="number" placeholder="每月可用次数" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
              </div>

              <!-- 限流 -->
              <div>
                <label class="mb-1.5 block text-sm font-medium text-slate-700">限流</label>
                <div class="grid grid-cols-3 gap-3">
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">RPM</label>
                    <input v-model="credFormRpm" type="number" min="0" placeholder="每分钟请求" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">TPM</label>
                    <input v-model="credFormTpm" type="number" min="0" placeholder="每分钟Token" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">最大并发</label>
                    <input v-model="credFormMaxParallel" type="number" min="0" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <p v-if="credError" class="mb-3 text-sm text-red-500">{{ credError }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showCredForm = false">取消</button>
            <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]">保存</button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteProviderTarget"
      title="确认删除"
      :message="`确定要删除供应商「${deleteProviderTarget?.name}」吗？`"
      @confirm="handleConfirmDeleteProvider"
      @cancel="deleteProviderTarget = null"
    />

    <ConfirmDialog
      :visible="!!deleteCredTarget"
      title="确认删除"
      :message="`确定要删除凭证「${deleteCredTarget?.credential_name}」吗？被部署引用的凭证无法删除。`"
      @confirm="handleConfirmDeleteCred"
      @cancel="deleteCredTarget = null"
    />
  </div>
</template>
