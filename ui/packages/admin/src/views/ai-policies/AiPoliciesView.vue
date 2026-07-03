<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  getAiPolicyAudits,
  getAiPolicySettings,
  getCredentials,
  getModelById,
  getModels,
  toast,
  updateAiPolicySettings,
  type AiPolicyAuditSummary,
  type Credential,
  type ModelInfo,
} from '@aihelms/shared'
import {
  CalendarDays,
  FileText,
  Loader2,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from 'lucide-vue-next'

type StatusFilter = 'all' | 'running' | 'high_risk' | 'attention_required' | 'passed' | 'failed'
type EndTimeFilter = 'all' | 'today' | 'yesterday' | 'last7' | 'unfinished'

interface AuditProgress {
  progress: number
  completed: number
  total: number
  step: string
}

interface ReviewModelOption {
  id: number
  name: string
  model_id: string
  deployments: string[]
}

const router = useRouter()
const audits = ref<AiPolicyAuditSummary[]>([])
const loading = ref(false)
const showSettings = ref(false)
const savingSettings = ref(false)
const loadingReviewModels = ref(false)
const llmEnabled = ref(false)
const selectedModelId = ref<number | null>(null)
const reviewModelOptions = ref<ReviewModelOption[]>([])
const reviewModelLoadError = ref('')
const statusFilter = ref<StatusFilter>('all')
const endTimeFilter = ref<EndTimeFilter>('all')
const query = ref('')

const stats = computed(() => ({
  total: audits.value.length,
  running: audits.value.filter((item) => item.status === 'queued' || item.status === 'running').length,
  high: audits.value.filter((item) => item.decision === 'high_risk').length,
  attention: audits.value.filter((item) => item.decision === 'attention_required').length,
  passed: audits.value.filter((item) => item.decision === 'passed').length,
  failed: audits.value.filter((item) => item.status === 'failed' || item.decision === 'failed').length,
}))

const statusFilters = computed<{ key: StatusFilter; label: string; count: number }[]>(() => [
  { key: 'all', label: '全部', count: stats.value.total },
  { key: 'running', label: '审查中', count: stats.value.running },
  { key: 'high_risk', label: '高风险', count: stats.value.high },
  { key: 'attention_required', label: '建议修改', count: stats.value.attention },
  { key: 'passed', label: '通过', count: stats.value.passed },
  { key: 'failed', label: '失败', count: stats.value.failed },
])

const filteredAudits = computed(() => audits.value.filter((item) => {
  if (statusFilter.value === 'all') return true
  if (statusFilter.value === 'running') return item.status === 'queued' || item.status === 'running'
  if (statusFilter.value === 'failed') return item.status === 'failed' || item.decision === 'failed'
  return item.decision === statusFilter.value
}))

const endTimeFilters: { key: EndTimeFilter; label: string }[] = [
  { key: 'all', label: '全部结束时间' },
  { key: 'today', label: '今天' },
  { key: 'yesterday', label: '昨天' },
  { key: 'last7', label: '近 7 天' },
  { key: 'unfinished', label: '未结束' },
]

const selectedReviewModel = computed(() =>
  reviewModelOptions.value.find((item) => item.id === selectedModelId.value) || null,
)

const modelPlaceholder = computed(() => (llmEnabled.value ? '请选择审查模型' : '启用后选择审查模型'))

function credentialFormat(credential: Credential | undefined): string {
  return String(credential?.credential_info?.format || 'openai').toLowerCase()
}

function isOpenAiChatReviewModel(model: ModelInfo, credentialMap: Map<number, Credential>): ReviewModelOption | null {
  if (!model.is_active || model.category !== 'chat') return null
  const deployments = (model.deployments || []).filter((deployment) => {
    if (!deployment.is_active || !deployment.credential_id) return false
    const credential = credentialMap.get(deployment.credential_id)
    return !!credential?.is_active && credentialFormat(credential) === 'openai'
  })
  if (deployments.length === 0) return null
  return {
    id: model.id,
    name: model.name,
    model_id: model.model_id,
    deployments: deployments.map((item) => item.deploy_name || item.credential_name || `渠道 ${item.id}`),
  }
}

async function loadReviewModelOptions(force = false): Promise<void> {
  if (!force && reviewModelOptions.value.length > 0) return
  loadingReviewModels.value = true
  reviewModelLoadError.value = ''
  try {
    const [modelResult, credentialResult] = await Promise.all([
      getModels(1, 100, 'chat'),
      getCredentials(1, 100),
    ])
    const credentialMap = new Map(credentialResult.items.map((item) => [item.id, item]))
    const details = await Promise.all(
      modelResult.items
        .filter((item) => item.is_active && item.category === 'chat')
        .map(async (item) => getModelById(item.id)),
    )
    reviewModelOptions.value = details
      .map((item) => isOpenAiChatReviewModel(item, credentialMap))
      .filter((item): item is ReviewModelOption => !!item)
  } catch (e) {
    reviewModelLoadError.value = (e as { message?: string }).message || '模型列表加载失败'
    toast.error(reviewModelLoadError.value)
  } finally {
    loadingReviewModels.value = false
  }
}

function openSettings(): void {
  showSettings.value = true
  if (llmEnabled.value) void loadReviewModelOptions()
}

function toDateInput(offsetDays: number): Date {
  const date = new Date()
  date.setHours(0, 0, 0, 0)
  date.setDate(date.getDate() + offsetDays)
  return date
}

function endTimeParams(): { finished_from?: string; finished_to?: string; unfinished?: boolean } {
  if (endTimeFilter.value === 'unfinished') return { unfinished: true }
  if (endTimeFilter.value === 'today') return { finished_from: toDateInput(0).toISOString(), finished_to: toDateInput(1).toISOString(), unfinished: false }
  if (endTimeFilter.value === 'yesterday') return { finished_from: toDateInput(-1).toISOString(), finished_to: toDateInput(0).toISOString(), unfinished: false }
  if (endTimeFilter.value === 'last7') return { finished_from: toDateInput(-6).toISOString(), finished_to: toDateInput(1).toISOString(), unfinished: false }
  return {}
}

async function loadAudits(): Promise<void> {
  loading.value = true
  try {
    const result = await getAiPolicyAudits({
      page: 1,
      page_size: 100,
      audit_type: 'skill',
      q: query.value.trim() || undefined,
      ...endTimeParams(),
    })
    audits.value = result.items
  } catch (e) {
    toast.error((e as { message?: string }).message || 'AI Policies 数据加载失败')
  } finally {
    loading.value = false
  }
}

async function loadSettings(): Promise<void> {
  try {
    const settings = await getAiPolicySettings()
    llmEnabled.value = settings.llm_review_enabled
    selectedModelId.value = settings.llm_review_model_id
  } catch {
    // 配置读取失败不影响审计结果浏览。
  }
}

async function saveSettings(): Promise<void> {
  if (llmEnabled.value) {
    await loadReviewModelOptions()
    if (!selectedModelId.value || !selectedReviewModel.value) {
      toast.error('请选择一个已启用的 OpenAI 格式对话模型')
      return
    }
  }
  savingSettings.value = true
  try {
    await updateAiPolicySettings({
      llm_review_enabled: llmEnabled.value,
      llm_review_model_id: llmEnabled.value ? selectedModelId.value || null : null,
    })
    showSettings.value = false
    toast.success('LLM 审查引擎配置已保存')
  } catch (e) {
    toast.error((e as { message?: string }).message || '配置保存失败')
  } finally {
    savingSettings.value = false
  }
}

function openAudit(item: AiPolicyAuditSummary): void {
  router.push(`/ai-policies/audits/${item.audit_id}`)
}

function formatTime(value?: string | null): string {
  if (!value) return '未结束'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function decisionLabel(item: AiPolicyAuditSummary): string {
  if (item.status === 'queued') return '排队中'
  if (item.status === 'running') return '审查中'
  if (item.status === 'failed' || item.decision === 'failed') return '审查失败'
  return { passed: '通过', attention_required: '建议修改', high_risk: '高风险', '': '未出结论' }[item.decision || '']
}

function badgeClass(item: AiPolicyAuditSummary): string {
  if (item.status === 'queued' || item.status === 'running') return 'bg-indigo-50 text-indigo-700 ring-indigo-200'
  if (item.status === 'failed' || item.decision === 'failed') return 'bg-stone-100 text-stone-700 ring-stone-200'
  if (item.decision === 'high_risk') return 'bg-red-50 text-red-700 ring-red-200'
  if (item.decision === 'attention_required') return 'bg-amber-50 text-amber-700 ring-amber-200'
  return 'bg-emerald-50 text-emerald-700 ring-emerald-200'
}

function progressOf(item: AiPolicyAuditSummary): AuditProgress {
  const raw = item.summary?.progress
  if (raw && typeof raw === 'object') {
    const progress = raw as { value?: number; completed?: number; total?: number; step?: string }
    return {
      progress: typeof progress.value === 'number' ? progress.value : 0,
      completed: typeof progress.completed === 'number' ? progress.completed : 0,
      total: typeof progress.total === 'number' ? progress.total : 4,
      step: typeof progress.step === 'string' ? progress.step : '处理中',
    }
  }
  if (item.status === 'queued') return { progress: 0, completed: 0, total: 4, step: '等待审查任务启动' }
  if (item.status === 'running') return { progress: 25, completed: 1, total: 4, step: '正在扫描 Skill' }
  if (item.status === 'failed') return { progress: 100, completed: 0, total: 4, step: item.error_message || '审查失败' }
  return { progress: 100, completed: 4, total: 4, step: '报告已生成' }
}

function progressBarClass(item: AiPolicyAuditSummary): string {
  if (item.status === 'queued' || item.status === 'running') return 'bg-indigo-500'
  if (item.status === 'failed' || item.decision === 'failed') return 'bg-stone-500'
  if (item.decision === 'high_risk') return 'bg-red-500'
  if (item.decision === 'attention_required') return 'bg-amber-500'
  return 'bg-emerald-500'
}

function shouldShowProgress(item: AiPolicyAuditSummary): boolean {
  return item.status === 'queued' || item.status === 'running'
}

function shortAdvice(item: AiPolicyAuditSummary): string {
  if (item.status === 'queued') return '任务已创建，等待审查引擎处理。'
  if (item.status === 'running') return '正在检查 Skill 压缩包内容，完成后自动生成报告。'
  if (item.status === 'failed') return item.error_message || '审查执行失败，请确认扫描服务和 zip 文件是否可用。'
  if (item.decision === 'high_risk') return `发现 ${item.high_risk_count} 个高优先级风险，建议发布前复核。`
  if (item.decision === 'attention_required') return `发现 ${item.findings_count} 个风险点，建议按报告逐项处理。`
  return '未发现明显高优先级风险。'
}

let queryTimer: number | undefined
watch([query, endTimeFilter], () => {
  window.clearTimeout(queryTimer)
  queryTimer = window.setTimeout(loadAudits, 250)
})

watch(llmEnabled, (enabled) => {
  if (enabled) {
    void loadReviewModelOptions()
  } else {
    selectedModelId.value = null
    reviewModelLoadError.value = ''
  }
})

onMounted(() => {
  loadAudits()
  loadSettings()
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div><div class="mb-2 inline-flex items-center gap-2 rounded-full bg-purple-50 px-3 py-1 text-xs font-medium text-purple-700"><ShieldCheck class="h-3.5 w-3.5" />AI Policies</div><h1 class="text-2xl font-bold text-slate-900">Skill 安全审计中心</h1><p class="mt-1 text-sm text-slate-500">集中查看 Skill 审查任务、风险结论和报告；MCP、Agent、Prompt 审计在 AI 实验室预告页展示。</p></div>
      <button class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-purple-300 hover:text-purple-700" @click="openSettings"><SlidersHorizontal class="h-4 w-4" />LLM 审查引擎配置</button>
    </div>
    <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-center gap-3 border-b border-slate-100 p-4">
        <div class="flex flex-wrap gap-2"><button v-for="item in statusFilters" :key="item.key" class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium transition-colors" :class="statusFilter === item.key ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'" @click="statusFilter = item.key"><span>{{ item.label }}</span><span class="rounded-full px-1.5 py-0.5 text-[10px] leading-none" :class="statusFilter === item.key ? 'bg-white/20 text-white' : 'bg-white text-slate-500 ring-1 ring-slate-200'">{{ item.count }}</span></button></div>
        <div class="ml-auto flex flex-wrap items-center gap-2">
          <label class="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-600"><CalendarDays class="h-4 w-4 text-slate-400" /><span class="text-xs text-slate-500">审查结束时间</span><select v-model="endTimeFilter" class="bg-transparent text-sm text-slate-700 focus:outline-none"><option v-for="item in endTimeFilters" :key="item.key" :value="item.key">{{ item.label }}</option></select></label>
          <label class="relative block"><Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input v-model="query" class="h-9 w-64 rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm focus:border-purple-500 focus:outline-none" placeholder="搜索 Skill" /></label>
        </div>
      </div>
      <div v-if="loading" class="flex items-center justify-center gap-2 py-20 text-sm text-slate-400"><Loader2 class="h-4 w-4 animate-spin" />加载中...</div>
      <div v-else-if="filteredAudits.length === 0" class="py-20 text-center text-sm text-slate-400">暂无符合条件的审查任务。请在 Skill 管理中对已上传 zip 的 Skill 发起审查。</div>
      <div v-else class="grid grid-cols-1 gap-4 p-4 lg:grid-cols-2 2xl:grid-cols-3">
        <div v-for="item in filteredAudits" :key="item.audit_id" class="flex min-h-[230px] flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-purple-300 hover:shadow-md">
          <div class="flex items-start justify-between gap-3"><div class="min-w-0"><h3 class="truncate text-base font-semibold text-slate-900">{{ item.skill_name }}</h3><div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500"><span class="rounded bg-slate-100 px-1.5 py-0.5 font-medium text-slate-600">v{{ item.skill_version || '-' }}</span><span>结束时间：{{ formatTime(item.finished_at) }}</span></div></div><span class="shrink-0 rounded-full px-2 py-1 text-[11px] font-medium ring-1" :class="badgeClass(item)">{{ decisionLabel(item) }}</span></div>
          <div class="mt-4 rounded-xl bg-slate-50 p-3"><template v-if="shouldShowProgress(item)"><div class="flex items-center justify-between text-xs"><span class="font-medium text-slate-700">{{ progressOf(item).step }}</span><span class="text-slate-500">{{ progressOf(item).completed }}/{{ progressOf(item).total }} 项 · {{ progressOf(item).progress }}%</span></div><div class="mt-2 h-2 overflow-hidden rounded-full bg-slate-200"><div class="h-full rounded-full transition-all" :class="progressBarClass(item)" :style="{ width: `${progressOf(item).progress}%` }" /></div></template><div v-else class="grid grid-cols-3 gap-2 text-center"><div><div class="text-lg font-bold text-slate-900">{{ item.risk_score }}</div><div class="text-[11px] text-slate-500">风险分</div></div><div><div class="text-lg font-bold text-slate-900">{{ item.findings_count }}</div><div class="text-[11px] text-slate-500">风险</div></div><div><div class="text-lg font-bold text-slate-900">{{ item.high_risk_count }}</div><div class="text-[11px] text-slate-500">高危</div></div></div><p class="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">{{ shortAdvice(item) }}</p></div>
          <div class="mt-auto flex flex-wrap items-center justify-between gap-2 pt-4"><div class="break-all text-xs text-slate-400">审查任务 {{ item.audit_id }}</div><button class="inline-flex items-center gap-1 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-500" @click="openAudit(item)"><FileText class="h-3.5 w-3.5" />{{ item.status === 'queued' || item.status === 'running' ? '看进度' : '查看报告' }}</button></div>
        </div>
      </div>
    </div>
    <div v-if="showSettings" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm">
      <div class="w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-2xl"><div class="flex items-start justify-between border-b border-slate-100 p-5"><div><h2 class="text-lg font-semibold text-slate-900">LLM 审查引擎配置</h2><p class="mt-1 text-sm text-slate-500">启用后由平台调用所选模型，对规则扫描结果和受控摘录做语义研判。</p></div><button class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700" @click="showSettings = false"><X class="h-5 w-5" /></button></div>
        <div class="space-y-4 p-5"><label class="flex items-start justify-between gap-4 rounded-xl border border-slate-200 p-4"><span><span class="block text-sm font-semibold text-slate-900">启用 LLM 审查引擎</span><span class="mt-1 block text-xs text-slate-500">默认关闭；失败或超时不影响静态审查任务落库。</span></span><input v-model="llmEnabled" type="checkbox" class="mt-1 h-5 w-5 accent-purple-600" /></label><div><label class="mb-1 block text-sm font-medium text-slate-700">审查模型</label><select v-model="selectedModelId" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none disabled:bg-slate-50 disabled:text-slate-400" :disabled="!llmEnabled || loadingReviewModels"><option :value="null">{{ modelPlaceholder }}</option><option v-for="model in reviewModelOptions" :key="model.id" :value="model.id">{{ model.name }}</option></select><p v-if="reviewModelLoadError" class="mt-2 text-xs text-red-500">{{ reviewModelLoadError }}</p></div></div>
        <div class="flex justify-end gap-2 border-t border-slate-100 p-5"><button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showSettings = false">取消</button><button class="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-500 disabled:opacity-50" :disabled="savingSettings" @click="saveSettings"><Settings2 class="h-4 w-4" />{{ savingSettings ? '保存中...' : '保存配置' }}</button></div>
      </div>
    </div>
  </div>
</template>
