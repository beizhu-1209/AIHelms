<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  getModels,
  getModelById,
  createModel,
  updateModel,
  deleteModel,
  createDeployment,
  updateDeployment,
  deleteDeployment,
  getProviders,
  getCredentials,
  getActiveModels,
  getAccessGroups,
  createAccessGroup,
  updateAccessGroup,
  deleteAccessGroup,
  getRouterSettings,
  updateRouterSettings,
  type ModelInfo,
  type Deployment,
  type Provider,
  type Credential,
  type ActiveModel,
  type AccessGroup,
  type RouterSettings,
  type UpdateRouterSettingsParams,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()

const models = ref<ModelInfo[]>([])
const filteredModels = ref<ModelInfo[]>([])
const selectedModel = ref<ModelInfo | null>(null)
const deployments = ref<Deployment[]>([])
const providers = ref<Provider[]>([])
const credentials = ref<Credential[]>([])
const showModelForm = ref(false)
const showDeployForm = ref(false)
const isEditingModel = ref(false)
const isEditingDeploy = ref(false)
const editingDeployId = ref<number | null>(null)
const deleteModelTarget = ref<ModelInfo | null>(null)
const deleteDeployTarget = ref<Deployment | null>(null)
const errorMessage = ref('')

// Left nav: group filter
const selectedGroupId = ref<number | null>(null)

// Access Groups
const accessGroups = ref<AccessGroup[]>([])
const activeModels = ref<ActiveModel[]>([])
const showGroupForm = ref(false)
const isEditingGroup = ref(false)
const editingGroupId = ref<number | null>(null)
const deleteGroupTarget = ref<AccessGroup | null>(null)
const groupFormName = ref('')
const groupFormDescription = ref('')
const groupFormModelIds = ref<string[]>([])

// Router Settings
const showRouterForm = ref(false)
const routerSettings = ref<RouterSettings>({
  routing_strategy: 'simple-shuffle',
  fallbacks: [],
  allowed_fails: 3,
  cooldown_time: 60,
  num_retries: 2,
  timeout: 30,
  config: {},
})
const routerSaving = ref(false)
const routerError = ref('')
const newFallbackFrom = ref('')
const newFallbackTo = ref('')

// Model form
const formName = ref('')
const formModelId = ref('')
const formCategory = ref('chat')
const formTags = ref<string[]>([])
const formDescription = ref('')
const showModelAdvanced = ref(false)
// 创建时可选关联凭证（自动创建 deployment）
const formProviderId = ref<number | null>(null)
const formCredentialId = ref<number | null>(null)
const formDeployModelName = ref('')

// Deployment form — simplified
const deployModelName = ref('')  // 管理员填的模型名称（如 claude-sonnet-4-20250514）
const deployProviderId = ref<number | null>(null)
const deployCredentialId = ref<number | null>(null)
const deployName = ref('')
const showAdvanced = ref(false)
// 路由参数
const deployWeight = ref('')
const deployOrder = ref('')
const deployDeployTags = ref('')
// 超时
const deployTimeout = ref('')
const deployStreamTimeout = ref('')
const deployMaxRetries = ref('')
// 计费方式
const deployBillingType = ref('token')
// 外部官方定价（Token: ¥/百万token, Token Plan: ¥/次）
const deployInputCostPerToken = ref('')
const deployOutputCostPerToken = ref('')
const deployCacheReadCostPerToken = ref('')
const deployCacheCreationCostPerToken = ref('')
const deployCostPerCall = ref('')
// 内部结算定价（Token: ¥/百万token, Token Plan: ¥/次）
const deployInternalInputCost = ref('')
const deployInternalOutputCost = ref('')
const deployInternalCacheReadCost = ref('')
const deployInternalCacheCreationCost = ref('')
const deployInternalCostPerCall = ref('')
// 高级
const deployUseInPassThrough = ref(false)
const deployDropParams = ref(false)

const categories = [
  { value: 'chat', label: '对话' },
  { value: 'embedding', label: '向量' },
  { value: 'image', label: '图像' },
  { value: 'audio', label: '音频' },
]

const modelTags = [
  { value: '图像', label: '图像' },
  { value: '文件', label: '文件' },
  { value: '视频', label: '视频' },
  { value: '音频', label: '音频' },
  { value: '联网', label: '联网' },
  { value: '推理', label: '推理' },
  { value: '向量', label: '向量' },
  { value: '重排', label: '重排' },
]

const formFilteredCredentials = computed(() => {
  if (!formProviderId.value) return []
  return credentials.value.filter(c => c.provider_id === formProviderId.value)
})

const deployFilteredCredentials = computed(() => {
  if (!deployProviderId.value) return []
  return credentials.value.filter(c => c.provider_id === deployProviderId.value)
})

function toggleTag(value: string): void {
  const idx = formTags.value.indexOf(value)
  if (idx >= 0) {
    formTags.value.splice(idx, 1)
  } else {
    formTags.value.push(value)
  }
}

function getCredentialProviderType(credId: number | null): string {
  if (!credId) return ''
  const cred = credentials.value.find(c => c.id === credId)
  return cred?.provider_type || (cred?.credential_info?.custom_llm_provider as string) || ''
}

function buildLitellmModelId(credId: number | null, modelName: string): string {
  const providerType = getCredentialProviderType(credId)
  if (!providerType || !modelName) return modelName
  return `${providerType}/${modelName}`
}

async function fetchModels(): Promise<void> {
  const result = await getModels(1, 100)
  models.value = result.items
  applyGroupFilter()
}

function applyGroupFilter(): void {
  if (!selectedGroupId.value) {
    filteredModels.value = models.value
  } else {
    const group = accessGroups.value.find(g => g.id === selectedGroupId.value)
    if (group) {
      filteredModels.value = models.value.filter(m => group.model_ids.includes(m.model_id))
    } else {
      filteredModels.value = models.value
    }
  }
}

function handleSelectGroup(groupId: number | null): void {
  selectedGroupId.value = groupId
  applyGroupFilter()
}

async function fetchCredentials(): Promise<void> {
  const result = await getCredentials(1, 100)
  credentials.value = result.items.filter(c => c.is_active)
}

async function fetchProviderList(): Promise<void> {
  const result = await getProviders(1, 100)
  providers.value = result.items.filter(p => p.is_active)
}

async function fetchModelDetail(id: number): Promise<void> {
  const detail = await getModelById(id)
  selectedModel.value = detail
  deployments.value = detail.deployments || []
}

function handleSelectModel(model: ModelInfo): void {
  fetchModelDetail(model.id)
}

function handleCreateModel(): void {
  isEditingModel.value = false
  formName.value = ''
  formModelId.value = ''
  formCategory.value = 'chat'
  formTags.value = []
  formDescription.value = ''
  formProviderId.value = null
  formCredentialId.value = null
  formDeployModelName.value = ''
  showModelAdvanced.value = false
  errorMessage.value = ''
  showModelForm.value = true
}

function handleEditModel(): void {
  if (!selectedModel.value) return
  isEditingModel.value = true
  formName.value = selectedModel.value.name
  formModelId.value = selectedModel.value.model_id
  formCategory.value = selectedModel.value.category
  formTags.value = [...selectedModel.value.capabilities]
  formDescription.value = selectedModel.value.description
  showModelAdvanced.value = false
  errorMessage.value = ''
  showModelForm.value = true
}

async function handleSubmitModel(): Promise<void> {
  errorMessage.value = ''
  if (!formName.value || !formModelId.value) {
    errorMessage.value = '请填写模型名称和 ID'
    return
  }
  if (formCredentialId.value && !formDeployModelName.value) {
    errorMessage.value = '选择凭证后请填写厂商模型名称'
    return
  }
  try {
    if (isEditingModel.value && selectedModel.value) {
      await updateModel(selectedModel.value.id, {
        name: formName.value,
        category: formCategory.value,
        capabilities: formTags.value,
        description: formDescription.value,
      })
      await fetchModelDetail(selectedModel.value.id)
    } else {
      const model = await createModel({
        name: formName.value,
        model_id: formModelId.value,
        category: formCategory.value,
        capabilities: formTags.value,
        description: formDescription.value,
      })
      // Auto-create deployment if credential selected
      if (formCredentialId.value && formDeployModelName.value) {
        const litellmModel = buildLitellmModelId(formCredentialId.value, formDeployModelName.value)
        const litellmParams: Record<string, unknown> = { model: litellmModel }
        const cred = credentials.value.find(c => c.id === formCredentialId.value)
        if (cred) litellmParams.litellm_credential_name = cred.credential_name
        await createDeployment(model.id, {
          litellm_params: litellmParams,
          credential_id: formCredentialId.value,
        })
      }
    }
    showModelForm.value = false
    await fetchModels()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleConfirmDeleteModel(): Promise<void> {
  if (!deleteModelTarget.value) return
  try {
    await deleteModel(deleteModelTarget.value.id)
    if (selectedModel.value?.id === deleteModelTarget.value.id) {
      selectedModel.value = null
      deployments.value = []
    }
    deleteModelTarget.value = null
    await fetchModels()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '删除失败'
    deleteModelTarget.value = null
  }
}

function resetDeployForm(): void {
  deployModelName.value = ''
  deployProviderId.value = null
  deployCredentialId.value = null
  deployName.value = ''
  showAdvanced.value = false
  deployWeight.value = ''
  deployOrder.value = ''
  deployDeployTags.value = ''
  deployTimeout.value = ''
  deployStreamTimeout.value = ''
  deployMaxRetries.value = ''
  deployBillingType.value = 'token'
  deployInputCostPerToken.value = ''
  deployOutputCostPerToken.value = ''
  deployCacheReadCostPerToken.value = ''
  deployCacheCreationCostPerToken.value = ''
  deployCostPerCall.value = ''
  deployInternalInputCost.value = ''
  deployInternalOutputCost.value = ''
  deployInternalCacheReadCost.value = ''
  deployInternalCacheCreationCost.value = ''
  deployInternalCostPerCall.value = ''
  deployUseInPassThrough.value = false
  deployDropParams.value = false
}

function handleAddDeployment(): void {
  isEditingDeploy.value = false
  editingDeployId.value = null
  resetDeployForm()
  errorMessage.value = ''
  showDeployForm.value = true
}

function handleEditDeployment(d: Deployment): void {
  isEditingDeploy.value = true
  editingDeployId.value = d.id
  const params = (d.litellm_params || {}) as Record<string, unknown>
  // 从 litellm model 标识中提取模型名称（去掉 provider/ 前缀）
  const fullModel = (params.model as string) || ''
  const slashIdx = fullModel.indexOf('/')
  deployModelName.value = slashIdx >= 0 ? fullModel.slice(slashIdx + 1) : fullModel
  // 从凭证反推供应商
  const cred = credentials.value.find(c => c.id === d.credential_id)
  deployProviderId.value = cred?.provider_id || null
  deployCredentialId.value = d.credential_id
  deployName.value = d.deploy_name || ''
  deployWeight.value = params.weight ? String(params.weight) : ''
  deployOrder.value = params.order ? String(params.order) : ''
  deployDeployTags.value = Array.isArray(params.tags) ? (params.tags as string[]).join(', ') : ''
  deployTimeout.value = params.timeout ? String(params.timeout) : ''
  deployStreamTimeout.value = params.stream_timeout ? String(params.stream_timeout) : ''
  deployMaxRetries.value = params.max_retries ? String(params.max_retries) : ''
  deployBillingType.value = d.billing_type || 'token'
  deployInputCostPerToken.value = params.input_cost_per_token ? String(params.input_cost_per_token) : ''
  deployOutputCostPerToken.value = params.output_cost_per_token ? String(params.output_cost_per_token) : ''
  deployCacheReadCostPerToken.value = params.cache_read_input_token_cost ? String(params.cache_read_input_token_cost) : ''
  deployCacheCreationCostPerToken.value = params.cache_creation_input_token_cost ? String(params.cache_creation_input_token_cost) : ''
  deployCostPerCall.value = d.cost_per_call ? String(d.cost_per_call) : ''
  // 内部定价从 model_info 中读取
  const mInfo = (d.model_info || {}) as Record<string, unknown>
  deployInternalInputCost.value = mInfo.internal_input_cost ? String(mInfo.internal_input_cost) : ''
  deployInternalOutputCost.value = mInfo.internal_output_cost ? String(mInfo.internal_output_cost) : ''
  deployInternalCacheReadCost.value = mInfo.internal_cache_read_cost ? String(mInfo.internal_cache_read_cost) : ''
  deployInternalCacheCreationCost.value = mInfo.internal_cache_creation_cost ? String(mInfo.internal_cache_creation_cost) : ''
  deployInternalCostPerCall.value = mInfo.internal_cost_per_call ? String(mInfo.internal_cost_per_call) : ''
  deployUseInPassThrough.value = params.use_in_pass_through === true
  deployDropParams.value = params.drop_params === true
  showAdvanced.value = !!(deployWeight.value || deployOrder.value || deployDeployTags.value || deployTimeout.value || deployInputCostPerToken.value || deployInternalInputCost.value)
  errorMessage.value = ''
  showDeployForm.value = true
}

function buildLitellmParams(): Record<string, unknown> {
  const litellmModel = buildLitellmModelId(deployCredentialId.value, deployModelName.value)
  const litellmParams: Record<string, unknown> = { model: litellmModel }
  // 从凭证获取 credential_name 注入
  if (deployCredentialId.value) {
    const cred = credentials.value.find(c => c.id === deployCredentialId.value)
    if (cred) litellmParams.litellm_credential_name = cred.credential_name
  }
  if (deployWeight.value) litellmParams.weight = Number(deployWeight.value)
  if (deployOrder.value) litellmParams.order = Number(deployOrder.value)
  if (deployDeployTags.value) litellmParams.tags = deployDeployTags.value.split(',').map(s => s.trim()).filter(Boolean)
  if (deployTimeout.value) litellmParams.timeout = Number(deployTimeout.value)
  if (deployStreamTimeout.value) litellmParams.stream_timeout = Number(deployStreamTimeout.value)
  if (deployMaxRetries.value) litellmParams.max_retries = Number(deployMaxRetries.value)
  if (deployInputCostPerToken.value) litellmParams.input_cost_per_token = Number(deployInputCostPerToken.value)
  if (deployOutputCostPerToken.value) litellmParams.output_cost_per_token = Number(deployOutputCostPerToken.value)
  if (deployCacheReadCostPerToken.value) litellmParams.cache_read_input_token_cost = Number(deployCacheReadCostPerToken.value)
  if (deployCacheCreationCostPerToken.value) litellmParams.cache_creation_input_token_cost = Number(deployCacheCreationCostPerToken.value)
  litellmParams.use_in_pass_through = deployUseInPassThrough.value
  if (deployDropParams.value) litellmParams.drop_params = true
  return litellmParams
}

async function handleSubmitDeployment(): Promise<void> {
  if (!selectedModel.value) return
  if (!deployCredentialId.value) {
    errorMessage.value = '请选择关联凭证'
    return
  }
  if (!deployModelName.value) {
    errorMessage.value = '请填写模型名称'
    return
  }
  errorMessage.value = ''
  const litellmParams = buildLitellmParams()
  const modelInfo: Record<string, unknown> = {}
  if (deployBillingType.value === 'token') {
    if (deployInternalInputCost.value) modelInfo.internal_input_cost = Number(deployInternalInputCost.value)
    if (deployInternalOutputCost.value) modelInfo.internal_output_cost = Number(deployInternalOutputCost.value)
    if (deployInternalCacheReadCost.value) modelInfo.internal_cache_read_cost = Number(deployInternalCacheReadCost.value)
    if (deployInternalCacheCreationCost.value) modelInfo.internal_cache_creation_cost = Number(deployInternalCacheCreationCost.value)
  } else {
    if (deployInternalCostPerCall.value) modelInfo.internal_cost_per_call = Number(deployInternalCostPerCall.value)
  }
  const payload: Record<string, unknown> = {
    litellm_params: litellmParams,
    credential_id: deployCredentialId.value,
    deploy_name: deployName.value || undefined,
    billing_type: deployBillingType.value,
    model_info: Object.keys(modelInfo).length > 0 ? modelInfo : undefined,
  }
  if (deployBillingType.value === 'per_call' && deployCostPerCall.value) {
    payload.cost_per_call = Number(deployCostPerCall.value)
  }
  if (deployBillingType.value === 'monthly_quota' && deployCostPerCall.value) {
    payload.cost_per_call = Number(deployCostPerCall.value)
    payload.monthly_call_quota = null
  }
  try {
    if (isEditingDeploy.value && editingDeployId.value) {
      await updateDeployment(selectedModel.value.id, editingDeployId.value, payload as unknown as Parameters<typeof updateDeployment>[2])
    } else {
      await createDeployment(selectedModel.value.id, payload as unknown as Parameters<typeof createDeployment>[1])
    }
    showDeployForm.value = false
    await fetchModelDetail(selectedModel.value.id)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleToggleDeployment(d: Deployment): Promise<void> {
  if (!selectedModel.value) return
  await updateDeployment(selectedModel.value.id, d.id, { is_active: !d.is_active })
  await fetchModelDetail(selectedModel.value.id)
}

async function handleConfirmDeleteDeploy(): Promise<void> {
  if (!selectedModel.value || !deleteDeployTarget.value) return
  try {
    await deleteDeployment(selectedModel.value.id, deleteDeployTarget.value.id)
    deleteDeployTarget.value = null
    await fetchModelDetail(selectedModel.value.id)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '删除失败'
    deleteDeployTarget.value = null
  }
}

function getDeployModelName(d: Deployment): string {
  const params = d.litellm_params as Record<string, unknown>
  return (params?.model as string) || '-'
}

function getDeployCredentialName(d: Deployment): string {
  const params = d.litellm_params as Record<string, unknown>
  return (params?.litellm_credential_name as string) || ''
}

// --- Access Group methods ---

async function fetchAccessGroups(): Promise<void> {
  accessGroups.value = await getAccessGroups()
  applyGroupFilter()
}

async function fetchActiveModels(): Promise<void> {
  activeModels.value = await getActiveModels()
}

function handleCreateGroup(): void {
  isEditingGroup.value = false
  editingGroupId.value = null
  groupFormName.value = ''
  groupFormDescription.value = ''
  groupFormModelIds.value = []
  errorMessage.value = ''
  showGroupForm.value = true
}

function handleEditGroup(group: AccessGroup): void {
  isEditingGroup.value = true
  editingGroupId.value = group.id
  groupFormName.value = group.group_name
  groupFormDescription.value = group.description
  groupFormModelIds.value = [...group.model_ids]
  errorMessage.value = ''
  showGroupForm.value = true
}

function toggleGroupModel(modelId: string): void {
  const idx = groupFormModelIds.value.indexOf(modelId)
  if (idx >= 0) {
    groupFormModelIds.value.splice(idx, 1)
  } else {
    groupFormModelIds.value.push(modelId)
  }
}

async function handleSubmitGroup(): Promise<void> {
  errorMessage.value = ''
  if (!groupFormName.value) {
    errorMessage.value = '请输入分组名称'
    return
  }
  try {
    if (isEditingGroup.value && editingGroupId.value) {
      await updateAccessGroup(editingGroupId.value, {
        group_name: groupFormName.value,
        description: groupFormDescription.value,
        model_ids: groupFormModelIds.value,
      })
    } else {
      await createAccessGroup({
        group_name: groupFormName.value,
        description: groupFormDescription.value,
        model_ids: groupFormModelIds.value,
      })
    }
    showGroupForm.value = false
    await fetchAccessGroups()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleConfirmDeleteGroup(): Promise<void> {
  if (!deleteGroupTarget.value) return
  try {
    await deleteAccessGroup(deleteGroupTarget.value.id)
    deleteGroupTarget.value = null
    await fetchAccessGroups()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '删除失败'
    deleteGroupTarget.value = null
  }
}

function getModelNameById(modelId: string): string {
  const m = activeModels.value.find(am => am.model_id === modelId)
  return m ? m.name : modelId
}

// --- Router Settings methods ---

async function fetchRouterSettings(): Promise<void> {
  try {
    routerSettings.value = await getRouterSettings()
  } catch {
    // First time, no settings yet
  }
}

async function handleSaveRouterSettings(): Promise<void> {
  routerSaving.value = true
  routerError.value = ''
  try {
    const params: UpdateRouterSettingsParams = {
      routing_strategy: routerSettings.value.routing_strategy,
      fallbacks: routerSettings.value.fallbacks,
      allowed_fails: routerSettings.value.allowed_fails,
      cooldown_time: routerSettings.value.cooldown_time,
      num_retries: routerSettings.value.num_retries,
      timeout: routerSettings.value.timeout,
    }
    routerSettings.value = await updateRouterSettings(params)
  } catch (e) {
    routerError.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    routerSaving.value = false
  }
}

function handleAddFallback(): void {
  if (!newFallbackFrom.value || !newFallbackTo.value) return
  const entry: Record<string, string[]> = {}
  entry[newFallbackFrom.value] = [newFallbackTo.value]
  routerSettings.value.fallbacks = [...routerSettings.value.fallbacks, entry]
  newFallbackFrom.value = ''
  newFallbackTo.value = ''
}

function handleRemoveFallback(index: number): void {
  routerSettings.value.fallbacks = routerSettings.value.fallbacks.filter((_, i) => i !== index)
}

onMounted(() => {
  fetchModels()
  fetchProviderList()
  fetchCredentials()
  fetchAccessGroups()
  fetchActiveModels()
  fetchRouterSettings()
})
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- 模型管理（主视图） -->
    <div class="flex flex-1 gap-4 overflow-hidden">
    <!-- 左侧：分组导航 + 模型列表 -->
    <div class="w-80 shrink-0 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
        <h3 class="text-sm font-semibold text-slate-900">模型</h3>
        <button
          v-if="hasPermission('user:update')"
          class="rounded-md bg-purple-600 px-2.5 py-1 text-xs font-medium text-white transition-all hover:bg-purple-500"
          @click="handleCreateModel"
        >
          新建
        </button>
      </div>
      <!-- 分组导航 -->
      <div class="border-b border-slate-100 px-2 py-1.5">
        <div class="mb-1 flex items-center justify-between px-1">
          <span class="text-xs font-medium text-slate-400">分组</span>
          <button
            v-if="hasPermission('user:update')"
            class="text-xs text-purple-500 transition-colors hover:text-purple-600"
            @click="handleCreateGroup"
          >
            +新建
          </button>
        </div>
        <button
          class="mb-0.5 w-full rounded-md px-3 py-1.5 text-left text-xs font-medium transition-colors"
          :class="!selectedGroupId ? 'bg-purple-50 text-purple-700' : 'text-slate-500 hover:bg-slate-50'"
          @click="handleSelectGroup(null)"
        >
          全部模型 ({{ models.length }})
        </button>
        <div
          v-for="group in accessGroups"
          :key="group.id"
          class="group mb-0.5 flex items-center justify-between rounded-md px-3 py-1.5 text-xs font-medium transition-colors"
          :class="selectedGroupId === group.id ? 'bg-purple-50 text-purple-700' : 'text-slate-500 hover:bg-slate-50'"
        >
          <button class="flex-1 text-left" @click="handleSelectGroup(group.id)">
            {{ group.group_name }} ({{ group.model_ids.length }})
          </button>
          <div class="hidden gap-1 group-hover:flex">
            <button class="text-purple-400 hover:text-purple-600" @click="handleEditGroup(group)">✎</button>
            <button class="text-red-400 hover:text-red-600" @click="deleteGroupTarget = group">×</button>
          </div>
        </div>
      </div>
      <!-- 模型列表 -->
      <div class="overflow-y-auto p-2" style="max-height: calc(100vh - 14rem)">
        <div
          v-for="model in filteredModels"
          :key="model.id"
          class="mb-0.5 flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-sm transition-colors"
          :class="selectedModel?.id === model.id ? 'bg-purple-50 font-medium text-purple-700' : 'text-slate-700 hover:bg-slate-100'"
          @click="handleSelectModel(model)"
        >
          <span>{{ model.name }}</span>
          <span class="text-xs text-slate-400">{{ model.deployment_count }}凭证</span>
        </div>
        <div v-if="filteredModels.length === 0" class="py-8 text-center text-sm text-slate-400">暂无模型</div>
      </div>
    </div>

    <!-- 右侧：部署管理 -->
    <div class="flex-1 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <template v-if="selectedModel">
        <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-semibold text-slate-900">{{ selectedModel.name }}</h3>
            <span class="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">{{ selectedModel.model_id }}</span>
            <span class="text-xs text-slate-400">{{ selectedModel.category }}</span>
          </div>
          <div class="flex gap-2">
            <button
              v-if="hasPermission('user:update')"
              class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200"
              @click="handleEditModel"
            >
              编辑
            </button>
            <button
              v-if="hasPermission('user:update')"
              class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200"
              @click="showRouterForm = true"
            >
              路由配置
            </button>
            <button
              v-if="hasPermission('user:update')"
              class="rounded-md bg-purple-600 px-2.5 py-1 text-xs font-medium text-white transition-all hover:bg-purple-500"
              @click="handleAddDeployment"
            >
              添加凭证
            </button>
            <button
              v-if="hasPermission('user:delete')"
              class="rounded-md bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-100"
              @click="deleteModelTarget = selectedModel"
            >
              删除
            </button>
          </div>
        </div>
        <div class="overflow-y-auto p-4" style="max-height: calc(100vh - 10rem)">
          <!-- 能力标签 -->
          <div v-if="selectedModel.capabilities.length > 0" class="mb-4 flex gap-1">
            <span
              v-for="cap in selectedModel.capabilities"
              :key="cap"
              class="rounded bg-purple-50 px-2 py-0.5 text-xs text-purple-600"
            >
              {{ cap }}
            </span>
          </div>

          <!-- 部署卡片 -->
          <div v-if="deployments.length > 0" class="grid grid-cols-2 gap-3">
            <div
              v-for="d in deployments"
              :key="d.id"
              class="rounded-xl border border-slate-200/60 bg-white p-4 transition-shadow hover:shadow-sm"
            >
              <div class="flex items-start justify-between">
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-slate-900">{{ d.deploy_name || getDeployModelName(d) }}</span>
                    <span
                      class="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      :class="d.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-400'"
                    >
                      {{ d.is_active ? '启用' : '禁用' }}
                    </span>
                  </div>
                  <div class="mt-1.5 text-xs text-slate-500">
                    <span class="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">{{ getDeployModelName(d) }}</span>
                  </div>
                </div>
              </div>
              <!-- 指标 -->
              <div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                <span v-if="d.credential_name || getDeployCredentialName(d)">
                  凭证: <span class="text-slate-700">{{ d.credential_name || getDeployCredentialName(d) }}</span>
                </span>
                <span v-if="(d.litellm_params as Record<string, unknown>)?.weight">
                  权重: <span class="text-slate-700">{{ (d.litellm_params as Record<string, unknown>).weight }}</span>
                </span>
                <span v-if="(d.litellm_params as Record<string, unknown>)?.order">
                  优先级: <span class="text-slate-700">{{ (d.litellm_params as Record<string, unknown>).order }}</span>
                </span>
                <span v-if="(d.litellm_params as Record<string, unknown>)?.timeout">
                  超时: <span class="text-slate-700">{{ (d.litellm_params as Record<string, unknown>).timeout }}s</span>
                </span>
                <span v-if="(d.litellm_params as Record<string, unknown>)?.use_in_pass_through">
                  <span class="text-green-600">透传</span>
                </span>
              </div>
              <!-- 操作 -->
              <div class="mt-3 flex items-center gap-2 border-t border-slate-100 pt-2">
                <button
                  class="rounded-full px-2 py-0.5 text-xs font-medium transition-colors"
                  :class="d.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                  @click="handleToggleDeployment(d)"
                >
                  {{ d.is_active ? '启用' : '禁用' }}
                </button>
                <button
                  v-if="hasPermission('user:update')"
                  class="text-xs text-purple-500 transition-colors hover:text-purple-600"
                  @click="handleEditDeployment(d)"
                >
                  编辑
                </button>
                <button
                  v-if="hasPermission('user:delete')"
                  class="text-xs text-red-500 transition-colors hover:text-red-600"
                  @click="deleteDeployTarget = d"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
          <div v-else class="py-8 text-center text-sm text-slate-400">暂无凭证，点击「添加凭证」配置模型接入</div>
        </div>
      </template>
      <template v-else>
        <div class="flex h-full items-center justify-center text-sm text-slate-400">请选择左侧模型</div>
      </template>
    </div>
    </div>

    <!-- 路由配置弹窗 -->
    <div v-if="showRouterForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">路由配置</h3>
        <p class="mb-4 text-xs text-slate-400">全局路由策略，同步到 LiteLLM router_settings</p>

        <div class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">路由策略</label>
          <select v-model="routerSettings.routing_strategy" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
            <option value="simple-shuffle">轮询 (simple-shuffle)</option>
            <option value="latency-based-routing">最低延迟 (latency-based)</option>
            <option value="cost-based-routing">最低成本 (cost-based)</option>
            <option value="least-busy">最少使用 (least-busy)</option>
            <option value="usage-based-routing">按用量均衡 (usage-based)</option>
          </select>
        </div>

        <div class="mb-4 grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1 block text-xs text-slate-500">连续失败摘除</label>
            <input v-model.number="routerSettings.allowed_fails" type="number" min="0" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div>
            <label class="mb-1 block text-xs text-slate-500">冷却时间 (秒)</label>
            <input v-model.number="routerSettings.cooldown_time" type="number" min="0" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div>
            <label class="mb-1 block text-xs text-slate-500">全局重试次数</label>
            <input v-model.number="routerSettings.num_retries" type="number" min="0" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div>
            <label class="mb-1 block text-xs text-slate-500">全局超时 (秒)</label>
            <input v-model.number="routerSettings.timeout" type="number" min="0" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
        </div>

        <!-- Fallback 链 -->
        <div class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">Fallback 链</label>
          <div v-if="routerSettings.fallbacks.length > 0" class="mb-2 space-y-1.5">
            <div
              v-for="(fb, idx) in routerSettings.fallbacks"
              :key="idx"
              class="flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-1.5"
            >
              <span class="text-sm text-slate-700">{{ Object.keys(fb as Record<string, unknown>)[0] }}</span>
              <span class="text-xs text-slate-400">→</span>
              <span class="text-sm text-slate-700">{{ (Object.values(fb as Record<string, unknown>)[0] as string[])?.join(', ') }}</span>
              <button class="ml-auto text-xs text-red-400 hover:text-red-600" @click="handleRemoveFallback(idx)">移除</button>
            </div>
          </div>
          <div class="flex items-end gap-2">
            <div class="flex-1">
              <input v-model="newFallbackFrom" placeholder="源模型" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
            </div>
            <span class="pb-2 text-xs text-slate-400">→</span>
            <div class="flex-1">
              <input v-model="newFallbackTo" placeholder="Fallback 模型" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
            </div>
            <button class="rounded-md bg-slate-100 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-200" @click="handleAddFallback">添加</button>
          </div>
        </div>

        <p v-if="routerError" class="mb-3 text-sm text-red-500">{{ routerError }}</p>
        <div class="flex justify-end gap-3">
          <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showRouterForm = false">取消</button>
          <button
            class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98] disabled:opacity-50"
            :disabled="routerSaving"
            @click="handleSaveRouterSettings"
          >
            {{ routerSaving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 分组表单弹窗 -->
    <div v-if="showGroupForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ isEditingGroup ? '编辑分组' : '新建分组' }}</h3>
        <form @submit.prevent="handleSubmitGroup">
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">分组名称</label>
            <input v-model="groupFormName" placeholder="如：基础模型组" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">描述</label>
            <input v-model="groupFormDescription" placeholder="可选" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">包含模型</label>
            <div class="max-h-48 overflow-y-auto rounded-lg border border-slate-200 p-2">
              <label
                v-for="m in activeModels"
                :key="m.model_id"
                class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  :checked="groupFormModelIds.includes(m.model_id)"
                  class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
                  @change="toggleGroupModel(m.model_id)"
                />
                <span class="text-slate-700">{{ m.name }}</span>
                <span class="text-xs text-slate-400">{{ m.model_id }}</span>
              </label>
              <p v-if="activeModels.length === 0" class="py-2 text-center text-xs text-slate-400">暂无可用模型</p>
            </div>
          </div>
          <p v-if="errorMessage" class="mb-3 text-sm text-red-500">{{ errorMessage }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showGroupForm = false">取消</button>
            <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]">保存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 新建/编辑模型弹窗 -->
    <div v-if="showModelForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ isEditingModel ? '编辑模型' : '新建模型' }}</h3>
        <form @submit.prevent="handleSubmitModel">
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">模型名称</label>
            <input v-model="formName" placeholder="如：Claude Sonnet 4" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">模型 ID（用户请求时使用）</label>
            <input v-model="formModelId" :disabled="isEditingModel" placeholder="如：claude-sonnet-4" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20 disabled:bg-slate-50 disabled:text-slate-400" />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">分类</label>
            <select v-model="formCategory" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
              <option v-for="c in categories" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">能力标签</label>
            <div class="flex flex-wrap gap-2">
              <label
                v-for="tag in modelTags"
                :key="tag.value"
                class="flex cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-sm transition-colors"
                :class="formTags.includes(tag.value) ? 'border-purple-300 bg-purple-50 text-purple-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50'"
              >
                <input
                  type="checkbox"
                  :checked="formTags.includes(tag.value)"
                  class="h-3.5 w-3.5 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
                  @change="toggleTag(tag.value)"
                />
                {{ tag.label }}
              </label>
            </div>
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">描述</label>
            <input v-model="formDescription" placeholder="可选" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>

          <!-- 高级设置 -->
          <div class="mb-4">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100"
              @click="showModelAdvanced = !showModelAdvanced"
            >
              <span class="text-xs transition-transform" :class="showModelAdvanced ? 'rotate-90' : ''">▶</span>
              高级设置
              <span class="text-xs text-slate-400">（关联凭证）</span>
            </button>

            <div v-if="showModelAdvanced" class="mt-3 space-y-3 rounded-lg border border-slate-100 p-4">
              <template v-if="!isEditingModel">
                <p class="text-xs text-slate-400">选择供应商和凭证后，自动为模型创建关联</p>
                <div>
                  <label class="mb-1.5 block text-sm font-medium text-slate-700">供应商</label>
                  <select v-model="formProviderId" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" @change="formCredentialId = null">
                    <option :value="null">不关联</option>
                    <option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option>
                  </select>
                </div>
                <div v-if="formProviderId">
                  <label class="mb-1.5 block text-sm font-medium text-slate-700">凭证</label>
                  <select v-model="formCredentialId" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
                    <option :value="null">请选择凭证</option>
                    <option v-for="c in formFilteredCredentials" :key="c.id" :value="c.id">{{ c.credential_name }}</option>
                  </select>
                  <p v-if="formFilteredCredentials.length === 0" class="mt-1 text-xs text-slate-400">该供应商暂无可用凭证</p>
                </div>
                <div v-if="formCredentialId">
                  <label class="mb-1.5 block text-sm font-medium text-slate-700">厂商模型名</label>
                  <input v-model="formDeployModelName" placeholder="如 claude-sonnet-4-20250514" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  <p v-if="formDeployModelName" class="mt-1 text-xs text-slate-400">
                    LiteLLM 标识: <span class="font-mono text-purple-600">{{ buildLitellmModelId(formCredentialId, formDeployModelName) }}</span>
                  </p>
                </div>
              </template>
              <p v-else class="text-xs text-slate-400">编辑模式下请通过「添加凭证」管理关联</p>
            </div>
          </div>

          <p v-if="errorMessage" class="mb-3 text-sm text-red-500">{{ errorMessage }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showModelForm = false">取消</button>
            <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]">保存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 添加/编辑凭证弹窗 -->
    <div v-if="showDeployForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ isEditingDeploy ? '编辑凭证' : '添加凭证' }}</h3>
        <form @submit.prevent="handleSubmitDeployment">
          <!-- 核心配置 -->
          <div class="mb-4 space-y-3">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-slate-700">供应商 <span class="text-red-400">*</span></label>
              <select v-model="deployProviderId" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" @change="deployCredentialId = null">
                <option :value="null" disabled>请选择供应商</option>
                <option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div v-if="deployProviderId">
              <label class="mb-1.5 block text-sm font-medium text-slate-700">凭证 <span class="text-red-400">*</span></label>
              <select v-model="deployCredentialId" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
                <option :value="null" disabled>请选择凭证</option>
                <option v-for="c in deployFilteredCredentials" :key="c.id" :value="c.id">{{ c.credential_name }}</option>
              </select>
              <p v-if="deployFilteredCredentials.length === 0" class="mt-1 text-xs text-slate-400">该供应商暂无可用凭证</p>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-slate-700">模型名称 <span class="text-red-400">*</span></label>
              <input v-model="deployModelName" placeholder="厂商模型名，如 claude-sonnet-4-20250514" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
              <p v-if="deployCredentialId && deployModelName" class="mt-1 text-xs text-slate-400">
                LiteLLM 标识: <span class="font-mono text-purple-600">{{ buildLitellmModelId(deployCredentialId, deployModelName) }}</span>
              </p>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-slate-700">备注名称</label>
              <input v-model="deployName" placeholder="可选备注，如「官方直连」" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
            </div>
          </div>

          <!-- 高级设置折叠 -->
          <div class="mb-4">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100"
              @click="showAdvanced = !showAdvanced"
            >
              <span class="text-xs transition-transform" :class="showAdvanced ? 'rotate-90' : ''">▶</span>
              高级设置
              <span class="text-xs text-slate-400">（路由、超时、定价）</span>
            </button>

            <div v-if="showAdvanced" class="mt-3 space-y-4 rounded-lg border border-slate-100 p-4">
              <!-- 路由 -->
              <div>
                <h4 class="mb-2 text-xs font-medium text-slate-500">路由</h4>
                <div class="grid grid-cols-3 gap-3">
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">权重</label>
                    <input v-model="deployWeight" type="number" min="0" placeholder="默认1" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">优先级</label>
                    <input v-model="deployOrder" type="number" min="0" placeholder="数字小优先" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">标签</label>
                    <input v-model="deployDeployTags" placeholder="逗号分隔" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                </div>
              </div>

              <!-- 超时 -->
              <div>
                <h4 class="mb-2 text-xs font-medium text-slate-500">超时</h4>
                <div class="grid grid-cols-3 gap-3">
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">超时 (秒)</label>
                    <input v-model="deployTimeout" type="number" min="0" placeholder="30" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">流式超时</label>
                    <input v-model="deployStreamTimeout" type="number" min="0" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">最大重试</label>
                    <input v-model="deployMaxRetries" type="number" min="0" placeholder="2" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                </div>
              </div>

              <!-- 计费方式 -->
              <div>
                <h4 class="mb-2 text-xs font-medium text-slate-500">计费方式</h4>
                <select v-model="deployBillingType" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
                  <option value="token">Token 计费</option>
                  <option value="monthly_quota">Token Plan（包月次数）</option>
                  <option value="per_call">Token Plan（按次计费）</option>
                </select>
              </div>

              <!-- Token 计费：外部官方定价 -->
              <div v-if="deployBillingType === 'token'">
                <h4 class="mb-2 text-xs font-medium text-slate-500">外部官方定价 (¥/百万token)</h4>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">输入</label>
                    <input v-model="deployInputCostPerToken" type="number" step="0.01" placeholder="如 15" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">输出</label>
                    <input v-model="deployOutputCostPerToken" type="number" step="0.01" placeholder="如 60" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">缓存读取</label>
                    <input v-model="deployCacheReadCostPerToken" type="number" step="0.01" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">缓存写入</label>
                    <input v-model="deployCacheCreationCostPerToken" type="number" step="0.01" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                </div>
              </div>

              <!-- Token Plan：外部单次定价 -->
              <div v-if="deployBillingType === 'per_call' || deployBillingType === 'monthly_quota'">
                <h4 class="mb-2 text-xs font-medium text-slate-500">外部单次定价</h4>
                <div>
                  <label class="mb-1 block text-xs text-slate-500">单次费用 (¥)</label>
                  <input v-model="deployCostPerCall" type="number" step="0.01" placeholder="每次调用费用" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                </div>
              </div>

              <!-- Token 计费：内部结算定价 -->
              <div v-if="deployBillingType === 'token'">
                <h4 class="mb-2 text-xs font-medium text-slate-500">内部结算定价 (¥/百万token)</h4>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">输入</label>
                    <input v-model="deployInternalInputCost" type="number" step="0.01" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">输出</label>
                    <input v-model="deployInternalOutputCost" type="number" step="0.01" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">缓存读取</label>
                    <input v-model="deployInternalCacheReadCost" type="number" step="0.01" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">缓存写入</label>
                    <input v-model="deployInternalCacheCreationCost" type="number" step="0.01" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                </div>
              </div>

              <!-- Token Plan：内部单次定价 -->
              <div v-if="deployBillingType === 'per_call' || deployBillingType === 'monthly_quota'">
                <h4 class="mb-2 text-xs font-medium text-slate-500">内部结算定价</h4>
                <div>
                  <label class="mb-1 block text-xs text-slate-500">内部单次费用 (¥)</label>
                  <input v-model="deployInternalCostPerCall" type="number" step="0.01" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                </div>
              </div>

              <!-- 其他 -->
              <div>
                <div class="flex gap-6">
                  <label class="flex items-center gap-2 text-sm text-slate-700">
                    <input v-model="deployUseInPassThrough" type="checkbox" class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20" />
                    透传
                  </label>
                  <label class="flex items-center gap-2 text-sm text-slate-700">
                    <input v-model="deployDropParams" type="checkbox" class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20" />
                    丢弃不支持参数
                </label>
                </div>
                <p v-if="deployUseInPassThrough" class="mt-1.5 text-xs text-amber-600">开启透传后 RPM/TPM 等限流将不生效</p>
              </div>
            </div>
          </div>

          <p v-if="errorMessage" class="mb-3 text-sm text-red-500">{{ errorMessage }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showDeployForm = false">取消</button>
            <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]">{{ isEditingDeploy ? '保存' : '添加' }}</button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteModelTarget"
      title="确认删除"
      :message="`确定要删除模型「${deleteModelTarget?.name}」吗？关联的凭证也会被移除。`"
      @confirm="handleConfirmDeleteModel"
      @cancel="deleteModelTarget = null"
    />

    <ConfirmDialog
      :visible="!!deleteDeployTarget"
      title="确认删除"
      :message="`确定要删除此凭证关联吗？`"
      @confirm="handleConfirmDeleteDeploy"
      @cancel="deleteDeployTarget = null"
    />

    <ConfirmDialog
      :visible="!!deleteGroupTarget"
      title="确认删除"
      :message="`确定要删除分组「${deleteGroupTarget?.group_name}」吗？`"
      @confirm="handleConfirmDeleteGroup"
      @cancel="deleteGroupTarget = null"
    />
  </div>
</template>
