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
  getModelVisibility,
  updateModelPublish,
  type ModelInfo,
  type Deployment,
  type Provider,
  type Credential,
  type ActiveModel,
  type AccessGroup,
  type RouterSettings,
  type UpdateRouterSettingsParams,
  type ModelVisibility,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import { getDepartmentTree, type DeptTreeNode } from '@aihelms/shared'
import { Search, X } from 'lucide-vue-next'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import AccessTestDialog from '../../components/AccessTestDialog.vue'
import ProviderIcon from '../../components/ProviderIcon.vue'
import HostedIcon from '@aihelms/shared/src/components/HostedIcon.vue'

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

// Access Test
const showTestDialog = ref(false)
const testDefaultModel = ref('')
const testAvailableModels = ref<string[]>([])

// Publish / Visibility
const showPublishDialog = ref(false)
const publishLoading = ref(false)
const publishIsPublished = ref(false)
const publishVisibilityType = ref('all')
const publishRequiresApproval = ref(false)
const publishDepartmentIds = ref<number[]>([])
const departmentTree = ref<DeptTreeNode[]>([])
const flatDepartments = ref<{ id: number; name: string; path: string }[]>([])

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
const formLogoProviderType = ref('')
const showLogoOptions = ref(false)
const logoSearch = ref('')
const showModelAdvanced = ref(false)
// 创建时可选关联凭证（自动创建 deployment）
const formProviderId = ref<number | null>(null)
const formCredentialId = ref<number | null>(null)
const formDeployModelName = ref('')

// Deployment form — simplified
const deployModelIdStr = ref('')  // 平台模型 ID（用户请求时使用）
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
  { value: 'chat', label: '对话', enabled: true },
  { value: 'embedding', label: '向量', enabled: true },
  { value: 'rerank', label: '重排', enabled: true },
  { value: 'image', label: '文生图', enabled: false },
  { value: 'video', label: '文生视频', enabled: false },
  { value: 'audio', label: '语音识别', enabled: false },
  { value: 'tts', label: '语音合成', enabled: false },
  { value: 'completion', label: '补全', enabled: false },
]

// 能力标签按分类联动
const categoryTags: Record<string, { value: string; label: string }[]> = {
  chat: [
    { value: '图像', label: '图像' },
    { value: '推理', label: '推理' },
    { value: '工具调用', label: '工具调用' },
  ],
  embedding: [
    { value: '多语言', label: '多语言' },
    { value: '多模态', label: '多模态' },
    { value: '代码', label: '代码' },
    { value: '长文本', label: '长文本' },
  ],
  rerank: [
    { value: '多语言', label: '多语言' },
    { value: '多模态', label: '多模态' },
  ],
}

const modelTags = computed(() => {
  return categoryTags[formCategory.value] || []
})

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

function getCredentialFormat(credId: number | null): string {
  if (!credId) return 'openai'
  const cred = credentials.value.find(c => c.id === credId)
  return (cred?.credential_info?.format as string) || 'openai'
}

function getProviderPrefixMap(credId: number | null): Record<string, string | null> | null {
  if (!credId) return null
  const cred = credentials.value.find(c => c.id === credId)
  if (!cred) return null
  const provider = providers.value.find(p => p.id === cred.provider_id)
  if (!provider) return null
  // 优先从供应商 config 中读取，fallback 到默认映射
  const configMap = provider.config?.litellm_prefix_map as Record<string, string | null> | undefined
  if (configMap) return configMap
  return FALLBACK_PREFIX_MAP[provider.provider_type] || null
}

// 默认前缀映射 fallback（供应商未配置 litellm_prefix_map 时使用）
const FALLBACK_PREFIX_MAP: Record<string, Record<string, string | null>> = {
  openai: { chat: 'openai', embedding: 'openai', rerank: null },
  anthropic: { chat: 'anthropic', embedding: null, rerank: null },
  azure: { chat: 'azure', embedding: 'azure', rerank: null },
  google: { chat: 'gemini', embedding: 'gemini', rerank: null },
  deepseek: { chat: 'deepseek', embedding: null, rerank: null },
  bedrock: { chat: 'bedrock', embedding: 'bedrock', rerank: null },
  vertex_ai: { chat: 'vertex_ai', embedding: 'vertex_ai', rerank: null },
  volcengine: { chat: 'openai', embedding: 'openai', rerank: null },
  dashscope: { chat: 'openai', embedding: 'openai', rerank: null },
  zhipu: { chat: 'openai', embedding: 'openai', rerank: null },
  moonshot: { chat: 'openai', embedding: null, rerank: null },
  minimax: { chat: 'openai', embedding: null, rerank: null },
  tencent: { chat: 'tencent', embedding: null, rerank: null },
  xai: { chat: 'xai', embedding: null, rerank: null },
  vllm: { chat: 'openai', embedding: 'openai', rerank: 'hosted_vllm' },
  sglang: { chat: 'openai', embedding: 'openai', rerank: null },
  ollama: { chat: 'ollama', embedding: 'ollama', rerank: null },
  lmstudio: { chat: 'openai', embedding: 'openai', rerank: null },
}

interface LogoOption { value: string; label: string }

const BUILT_IN_LOGO_OPTIONS: LogoOption[] = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'azure', label: 'Azure' },
  { value: 'google', label: 'Google' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'bedrock', label: 'Bedrock' },
  { value: 'vertex_ai', label: 'Vertex AI' },
  { value: 'volcengine', label: '火山引擎' },
  { value: 'dashscope', label: '阿里百炼' },
  { value: 'zhipu', label: 'Z.ai（GLM）' },
  { value: 'moonshot', label: 'Moonshot' },
  { value: 'minimax', label: 'MiniMax' },
  { value: 'xiaomi_mimo', label: '小米MiMo' },
  { value: 'tencent', label: '腾讯混元' },
  { value: 'xai', label: 'xAI（Grok）' },
  { value: 'vllm', label: 'vLLM' },
  { value: 'sglang', label: 'SGLang' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'lmstudio', label: 'LM Studio' },
  { value: 'openai_compatible', label: 'OpenAI Compatible' },
  { value: 'custom', label: '自定义' },
]

const modelLogoOptions = computed<LogoOption[]>(() => {
  const options: LogoOption[] = [{ value: '', label: '默认' }]
  const seen = new Set<string>([''])

  if (isEditingModel.value && selectedModel.value) {
    for (const deployment of deployments.value) {
      const providerType = getCredentialProviderType(deployment.credential_id)
      if (providerType && !seen.has(providerType)) {
        options.push({ value: providerType, label: getLogoProviderLabel(providerType) })
        seen.add(providerType)
      }
    }
  }

  for (const option of BUILT_IN_LOGO_OPTIONS) {
    if (!seen.has(option.value)) {
      options.push(option)
      seen.add(option.value)
    }
  }
  return options
})

const filteredLogoOptions = computed<LogoOption[]>(() => {
  const q = logoSearch.value.trim().toLowerCase()
  if (!q) return modelLogoOptions.value
  return modelLogoOptions.value.filter(option => {
    return option.label.toLowerCase().includes(q) || option.value.toLowerCase().includes(q)
  })
})

const selectedLogoOption = computed<LogoOption>(() => {
  const selected = modelLogoOptions.value.find(option => option.value === formLogoProviderType.value)
  if (selected) return selected
  if (formLogoProviderType.value) {
    return { value: formLogoProviderType.value, label: getLogoProviderLabel(formLogoProviderType.value) }
  }
  return modelLogoOptions.value[0]
})

function getLogoProviderLabel(providerType: string): string {
  return providers.value.find(p => p.provider_type === providerType)?.name
    || BUILT_IN_LOGO_OPTIONS.find(option => option.value === providerType)?.label
    || providerType
}

function handleOpenLogoPicker(): void {
  logoSearch.value = ''
  showLogoOptions.value = true
}

function handleCloseLogoPicker(): void {
  showLogoOptions.value = false
  logoSearch.value = ''
}

function handleSelectLogoProvider(providerType: string): void {
  formLogoProviderType.value = providerType
  handleCloseLogoPicker()
}

const categoryLabels: Record<string, string> = {
  chat: '对话',
  embedding: '向量',
  rerank: '重排',
  image: '文生图',
  video: '文生视频',
  audio: '语音识别',
  tts: '语音合成',
  completion: '补全',
}

function buildLitellmModelId(credId: number | null, modelName: string, category?: string): string {
  if (!modelName) return modelName
  const prefixMap = getProviderPrefixMap(credId)
  if (prefixMap && category) {
    const prefix = prefixMap[category]
    if (prefix === null) return modelName
    if (prefix) return `${prefix}/${modelName}`
  }
  // fallback: 用凭证的 provider_type
  const providerType = getCredentialProviderType(credId)
  if (!providerType) return modelName
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
  formLogoProviderType.value = ''
  showLogoOptions.value = false
  logoSearch.value = ''
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
  formLogoProviderType.value = selectedModel.value.logo_provider_type || ''
  showLogoOptions.value = false
  logoSearch.value = ''
  showModelAdvanced.value = false
  errorMessage.value = ''
  showModelForm.value = true
}

async function handleSubmitModel(): Promise<void> {
  errorMessage.value = ''
  if (!formName.value) {
    errorMessage.value = '请填写模型名称'
    return
  }
  try {
    if (isEditingModel.value && selectedModel.value) {
      await updateModel(selectedModel.value.id, {
        name: formName.value,
        model_id: formModelId.value || undefined,
        category: formCategory.value,
        capabilities: formTags.value,
        description: formDescription.value,
        logo_provider_type: formLogoProviderType.value,
      })
      await fetchModelDetail(selectedModel.value.id)
    } else {
      await createModel({
        name: formName.value,
        model_id: '',
        category: formCategory.value,
        capabilities: formTags.value,
        description: formDescription.value,
        logo_provider_type: formLogoProviderType.value,
      })
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
  deployModelIdStr.value = selectedModel.value?.model_id || ''
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

function handleTestDeployment(d: Deployment): void {
  const baseModelId = selectedModel.value?.model_id || ''
  // 判断凭证格式，anthropic 格式用 (Anthropic) 后缀
  const cred = credentials.value.find(c => c.id === d.credential_id)
  const credFormat = cred?.credential_info?.format as string || 'openai'
  testDefaultModel.value = credFormat === 'anthropic' ? `${baseModelId}(Anthropic)` : baseModelId
  testAvailableModels.value = []
  showTestDialog.value = true
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
  deployModelIdStr.value = selectedModel.value?.model_id || ''
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
  const litellmParams: Record<string, unknown> = { model: deployModelName.value }
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
  if (!deployModelIdStr.value) {
    errorMessage.value = '请填写模型 ID'
    return
  }
  if (!deployModelName.value) {
    errorMessage.value = '请填写厂商模型名称'
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
    model_id_str: deployModelIdStr.value || undefined,
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
  const full = (params?.model as string) || '-'
  const slashIdx = full.indexOf('/')
  return slashIdx >= 0 ? full.slice(slashIdx + 1) : full
}

function getDeployLitellmModelName(d: Deployment): string {
  const baseId = selectedModel.value?.model_id || ''
  if (!baseId) return ''
  const cred = credentials.value.find(c => c.id === d.credential_id)
  const credFormat = (cred?.credential_info?.format as string) || 'openai'
  return credFormat === 'anthropic' ? `${baseId}(Anthropic)` : baseId
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

// --- Publish methods ---

function flattenDeptTree(nodes: DeptTreeNode[], path: string = ''): { id: number; name: string; path: string }[] {
  const result: { id: number; name: string; path: string }[] = []
  for (const node of nodes) {
    const fullPath = path ? `${path} / ${node.name}` : node.name
    result.push({ id: node.id, name: node.name, path: fullPath })
    if (node.children && node.children.length > 0) {
      result.push(...flattenDeptTree(node.children, fullPath))
    }
  }
  return result
}

async function fetchDepartmentTree(): Promise<void> {
  try {
    departmentTree.value = await getDepartmentTree()
    flatDepartments.value = flattenDeptTree(departmentTree.value)
  } catch {
    departmentTree.value = []
    flatDepartments.value = []
  }
}

async function handleOpenPublish(): Promise<void> {
  if (!selectedModel.value) return
  publishLoading.value = true
  try {
    const vis = await getModelVisibility(selectedModel.value.id)
    publishIsPublished.value = vis.is_published
    publishVisibilityType.value = vis.visibility_type
    publishRequiresApproval.value = vis.requires_approval
    publishDepartmentIds.value = [...vis.department_ids]
    if (flatDepartments.value.length === 0) {
      await fetchDepartmentTree()
    }
    showPublishDialog.value = true
  } finally {
    publishLoading.value = false
  }
}

function togglePublishDept(deptId: number): void {
  const idx = publishDepartmentIds.value.indexOf(deptId)
  if (idx >= 0) {
    publishDepartmentIds.value.splice(idx, 1)
  } else {
    publishDepartmentIds.value.push(deptId)
  }
}

async function handleSavePublish(): Promise<void> {
  if (!selectedModel.value) return
  publishLoading.value = true
  try {
    await updateModelPublish(selectedModel.value.id, {
      is_published: publishIsPublished.value,
      visibility_type: publishVisibilityType.value,
      department_ids: publishVisibilityType.value === 'selected' ? publishDepartmentIds.value : undefined,
      requires_approval: publishRequiresApproval.value,
    })
    showPublishDialog.value = false
    await fetchModelDetail(selectedModel.value.id)
    await fetchModels()
  } finally {
    publishLoading.value = false
  }
}

async function handleQuickPublish(model: ModelInfo, event: Event): Promise<void> {
  event.stopPropagation()
  try {
    await updateModelPublish(model.id, { is_published: !model.is_published })
    await fetchModels()
    if (selectedModel.value?.id === model.id) {
      await fetchModelDetail(model.id)
    }
  } catch {
    // silent
  }
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
          class="mb-1 flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 transition-colors"
          :class="selectedModel?.id === model.id ? 'bg-purple-50 ring-1 ring-purple-200' : 'hover:bg-slate-50'"
          @click="handleSelectModel(model)"
        >
            <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100">
              <ProviderIcon :src="model.icon_url" :type="model.logo_provider_type" :size="20" />
            </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-sm font-medium" :class="selectedModel?.id === model.id ? 'text-purple-700' : 'text-slate-900'">{{ model.name }}</span>
              <span v-if="model.deployment_count" class="shrink-0 text-[10px] text-slate-400">{{ model.deployment_count }}凭证</span>
              <button
                v-if="hasPermission('user:update')"
                class="shrink-0 rounded px-1 py-0.5 text-[10px] font-medium transition-colors"
                :class="model.is_published ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-slate-100 text-slate-400 hover:bg-slate-200'"
                @click="handleQuickPublish(model, $event)"
              >
                {{ model.is_published ? '已发布' : '未发布' }}
              </button>
            </div>
            <div class="mt-0.5 flex items-center gap-1.5">
              <span class="rounded bg-blue-50 px-1 py-0.5 text-[10px] text-blue-600">{{ categoryLabels[model.category] || model.category }}</span>
              <span
                v-for="cap in model.capabilities.slice(0, 2)"
                :key="cap"
                class="rounded bg-slate-100 px-1 py-0.5 text-[10px] text-slate-500"
              >{{ cap }}</span>
              <span v-if="model.capabilities.length > 2" class="text-[10px] text-slate-400">+{{ model.capabilities.length - 2 }}</span>
            </div>
          </div>
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
          <div class="flex gap-1.5">
            <button
              v-if="hasPermission('user:update')"
              class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200"
              @click="handleEditModel"
            >
              编辑
            </button>
            <button
              v-if="hasPermission('user:update')"
              class="rounded-md px-2.5 py-1 text-xs font-medium transition-colors"
              :class="selectedModel.is_published ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-amber-50 text-amber-600 hover:bg-amber-100'"
              @click="handleOpenPublish"
            >
              发布设置
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
                    <span class="text-sm font-medium text-slate-900">{{ getDeployLitellmModelName(d) || selectedModel?.model_id || '-' }}</span>
                    <span
                      class="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      :class="d.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-400'"
                    >
                      {{ d.is_active ? '启用' : '禁用' }}
                    </span>
                  </div>
                  <p class="mt-1 text-xs text-slate-400">{{ d.credential_name || getDeployCredentialName(d) || d.deploy_name || '' }}</p>
                </div>
              </div>
              <!-- 指标 -->
              <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
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
              <div class="mt-3 flex items-center gap-1.5 border-t border-slate-100 pt-2">
                <button
                  class="rounded-md px-2 py-1 text-xs font-medium transition-colors"
                  :class="d.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                  @click="handleToggleDeployment(d)"
                >
                  {{ d.is_active ? '启用' : '禁用' }}
                </button>
                <button
                  v-if="hasPermission('user:update')"
                  class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200"
                  @click="handleEditDeployment(d)"
                >
                  编辑
                </button>
                <button
                  v-if="hasPermission('user:delete')"
                  class="rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-100"
                  @click="deleteDeployTarget = d"
                >
                  删除
                </button>
                <button
                  class="rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-600 transition-colors hover:bg-emerald-100"
                  @click="handleTestDeployment(d)"
                >
                  测试
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
            <label class="mb-1.5 block text-sm font-medium text-slate-700">分类</label>
            <select v-model="formCategory" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" @change="formTags = []">
              <option v-for="c in categories" :key="c.value" :value="c.value" :disabled="!c.enabled">{{ c.label }}{{ !c.enabled ? '（即将上线）' : '' }}</option>
            </select>
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">Logo</label>
            <div>
              <button
                type="button"
                class="flex h-11 w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 transition-colors hover:bg-slate-50 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
                @click="handleOpenLogoPicker"
              >
                <span class="flex min-w-0 items-center gap-2">
                  <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-slate-100">
                    <ProviderIcon v-if="formLogoProviderType" :type="formLogoProviderType" :size="18" />
                    <HostedIcon v-else src="/icons/v1/default.svg" alt="平台默认图标" :size="18" />
                  </span>
                  <span class="truncate font-medium">{{ selectedLogoOption.label }}</span>
                </span>
                <span class="shrink-0 text-xs text-slate-400">点击修改</span>
              </button>
            </div>
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

          <p v-if="errorMessage" class="mb-3 text-sm text-red-500">{{ errorMessage }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showModelForm = false">取消</button>
            <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]">保存</button>
          </div>
        </form>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="showLogoOptions"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/20 backdrop-blur-sm"
        @click.self="handleCloseLogoPicker"
      >
        <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white p-5 shadow-xl">
          <div class="mb-3 flex items-center justify-between">
            <h4 class="text-sm font-semibold text-slate-800">选择 Logo</h4>
            <button type="button" class="rounded p-1 text-slate-400 hover:text-slate-600" @click="handleCloseLogoPicker">
              <X class="h-4 w-4" />
            </button>
          </div>
          <div class="relative mb-3">
            <Search class="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              v-model="logoSearch"
              type="text"
              placeholder="搜索 Logo 名称或 provider_type..."
              class="w-full rounded-lg border border-slate-200 bg-white py-2 pl-8 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div class="grid max-h-72 grid-cols-5 gap-2 overflow-y-auto pr-1">
            <button
              v-for="option in filteredLogoOptions"
              :key="option.value || 'default'"
              type="button"
              class="flex h-16 flex-col items-center justify-center gap-1 rounded-lg border text-xs transition-colors"
              :class="formLogoProviderType === option.value ? 'border-purple-300 bg-purple-50 text-purple-700 ring-2 ring-purple-500/20' : 'border-slate-100 text-slate-600 hover:bg-slate-50'"
              :title="option.value || 'default'"
              @click="handleSelectLogoProvider(option.value)"
            >
              <span class="flex h-7 w-7 items-center justify-center rounded bg-slate-100">
                <ProviderIcon v-if="option.value" :type="option.value" :size="20" />
                <HostedIcon v-else src="/icons/v1/default.svg" alt="平台默认图标" :size="20" />
              </span>
              <span class="max-w-full truncate px-1">{{ option.label }}</span>
            </button>
          </div>
          <p v-if="!filteredLogoOptions.length" class="py-4 text-center text-xs text-slate-400">无匹配 Logo</p>
        </div>
      </div>
    </Teleport>

    <!-- 添加/编辑凭证弹窗 -->
    <div v-if="showDeployForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ isEditingDeploy ? '编辑凭证' : '添加凭证' }}</h3>
        <form @submit.prevent="handleSubmitDeployment">
          <!-- 核心配置 -->
          <div class="mb-4 space-y-3">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-slate-700">模型 ID（用户请求时使用） <span class="text-red-400">*</span></label>
              <input v-model="deployModelIdStr" placeholder="如：deepseek-v4-pro" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
              <p v-if="deployCredentialId && getCredentialFormat(deployCredentialId) === 'anthropic'" class="mt-1 text-xs text-amber-600">Anthropic 格式凭证，同步到 LiteLLM 时将自动注册为 {{ deployModelIdStr || '...' }}(Anthropic)</p>
            </div>
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
              <label class="mb-1.5 block text-sm font-medium text-slate-700">厂商模型名 <span class="text-red-400">*</span></label>
              <input v-model="deployModelName" placeholder="如 claude-sonnet-4-20250514" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
              <p class="mt-1 text-xs text-slate-400">供应商 API 中的模型标识，用于实际调用上游</p>
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
                    <input v-model="deployInputCostPerToken" type="number" step="0.000001" placeholder="如 15" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">输出</label>
                    <input v-model="deployOutputCostPerToken" type="number" step="0.000001" placeholder="如 60" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">缓存读取</label>
                    <input v-model="deployCacheReadCostPerToken" type="number" step="0.000001" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">缓存写入</label>
                    <input v-model="deployCacheCreationCostPerToken" type="number" step="0.000001" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                </div>
              </div>

              <!-- Token Plan：外部单次定价 -->
              <div v-if="deployBillingType === 'per_call' || deployBillingType === 'monthly_quota'">
                <h4 class="mb-2 text-xs font-medium text-slate-500">外部单次定价</h4>
                <div>
                  <label class="mb-1 block text-xs text-slate-500">单次费用 (¥)</label>
                  <input v-model="deployCostPerCall" type="number" step="0.000001" placeholder="每次调用费用" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                </div>
              </div>

              <!-- Token 计费：内部结算定价 -->
              <div v-if="deployBillingType === 'token'">
                <h4 class="mb-2 text-xs font-medium text-slate-500">内部结算定价 (¥/百万token)</h4>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">输入</label>
                    <input v-model="deployInternalInputCost" type="number" step="0.000001" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">输出</label>
                    <input v-model="deployInternalOutputCost" type="number" step="0.000001" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">缓存读取</label>
                    <input v-model="deployInternalCacheReadCost" type="number" step="0.000001" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                  <div>
                    <label class="mb-1 block text-xs text-slate-500">缓存写入</label>
                    <input v-model="deployInternalCacheCreationCost" type="number" step="0.000001" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
                  </div>
                </div>
              </div>

              <!-- Token Plan：内部单次定价 -->
              <div v-if="deployBillingType === 'per_call' || deployBillingType === 'monthly_quota'">
                <h4 class="mb-2 text-xs font-medium text-slate-500">内部结算定价</h4>
                <div>
                  <label class="mb-1 block text-xs text-slate-500">内部单次费用 (¥)</label>
                  <input v-model="deployInternalCostPerCall" type="number" step="0.000001" placeholder="可选" class="flex h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
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

    <AccessTestDialog
      :visible="showTestDialog"
      :default-model="testDefaultModel"
      :available-models="testAvailableModels"
      @close="showTestDialog = false"
    />

    <!-- 发布设置弹窗 -->
    <div v-if="showPublishDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">发布设置</h3>
        <p class="mb-4 text-xs text-slate-400">设置模型在用户端的可见性，权限落在用户身上，部门选择用于批量操作</p>

        <!-- 发布开关 -->
        <div class="mb-4 flex items-center justify-between rounded-lg border border-slate-200 p-3">
          <div>
            <span class="text-sm font-medium text-slate-700">发布到用户端</span>
            <p class="text-xs text-slate-400">开启后用户可在用户端看到并申请此模型</p>
          </div>
          <button
            class="relative h-6 w-11 rounded-full transition-colors"
            :class="publishIsPublished ? 'bg-green-500' : 'bg-slate-300'"
            @click="publishIsPublished = !publishIsPublished"
          >
            <span
              class="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform"
              :class="publishIsPublished ? 'left-[22px]' : 'left-0.5'"
            />
          </button>
        </div>

        <!-- 可见范围 -->
        <div v-if="publishIsPublished" class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">可见范围</label>
          <div class="flex gap-3">
            <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors" :class="publishVisibilityType === 'all' ? 'border-purple-300 bg-purple-50 text-purple-700' : 'border-slate-200 text-slate-600'">
              <input v-model="publishVisibilityType" type="radio" value="all" class="h-4 w-4 text-purple-600" />
              全部用户
            </label>
            <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors" :class="publishVisibilityType === 'selected' ? 'border-purple-300 bg-purple-50 text-purple-700' : 'border-slate-200 text-slate-600'">
              <input v-model="publishVisibilityType" type="radio" value="selected" class="h-4 w-4 text-purple-600" />
              指定部门
            </label>
          </div>
        </div>

        <!-- 部门穿梭框 -->
        <div v-if="publishIsPublished && publishVisibilityType === 'selected'" class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">选择部门（部门内用户将获得可见权限）</label>
          <div class="max-h-60 overflow-y-auto rounded-lg border border-slate-200 p-2">
            <label
              v-for="dept in flatDepartments"
              :key="dept.id"
              class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors hover:bg-slate-50"
            >
              <input
                type="checkbox"
                :checked="publishDepartmentIds.includes(dept.id)"
                class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
                @change="togglePublishDept(dept.id)"
              />
              <span class="text-slate-700">{{ dept.path }}</span>
            </label>
            <p v-if="flatDepartments.length === 0" class="py-2 text-center text-xs text-slate-400">暂无部门数据</p>
          </div>
          <p class="mt-1 text-xs text-slate-400">已选 {{ publishDepartmentIds.length }} 个部门</p>
        </div>

        <!-- 领用审批 -->
        <div v-if="publishIsPublished" class="mb-4 flex items-center gap-2 rounded-lg border border-slate-200 p-3">
          <input
            v-model="publishRequiresApproval"
            type="checkbox"
            class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
          />
          <div>
            <span class="text-sm font-medium text-slate-700">领用前需要审批</span>
            <p class="text-xs text-slate-400">开启后用户申请使用此模型需管理员审批</p>
          </div>
        </div>

        <div class="flex justify-end gap-3">
          <button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showPublishDialog = false">取消</button>
          <button
            class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98] disabled:opacity-50"
            :disabled="publishLoading"
            @click="handleSavePublish"
          >
            {{ publishLoading ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
