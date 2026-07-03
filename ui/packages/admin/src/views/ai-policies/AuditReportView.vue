<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getAiPolicyAudit,
  getAiPolicyRiskCatalog,
  getAiPolicyReportDownloadUrl,
  toast,
  type AiPolicyAudit,
  type AiPolicyFinding,
  type AiPolicyRiskCatalogItem,
} from '@aihelms/shared'
import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  Loader2,
  ScanLine,
} from 'lucide-vue-next'

interface RiskCategory {
  code: string
  name: string
  findings: AiPolicyFinding[]
  severity: string
  hitCount: number
}

interface AuditProgress {
  value: number
  completed: number
  total: number
  step: string
}

interface LlmCategoryReview {
  code: string
  name?: string
  result?: string
  reason?: string
  recommendation?: string
}

interface LlmReviewSummary {
  status?: string
  model?: string
  overall_judgement?: string
  reason?: string
  message?: string
  category_reviews?: LlmCategoryReview[]
}

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const refreshing = ref(false)
const audit = ref<AiPolicyAudit | null>(null)
const catalog = ref<AiPolicyRiskCatalogItem[]>([])
const detailSectionOpen = ref(true)
const expandedCategories = ref<Record<string, boolean>>({})
const expandedLocations = ref<Record<string, boolean>>({})

const severityOrder: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
  unknown: 0,
  none: 0,
  '': 0,
}

const findings = computed(() => [...(audit.value?.findings || [])].sort(compareFinding))
const referenceItems = computed(() => {
  const catalogItems = catalog.value.map((item) => ({
    code: item.code,
    name: item.name_zh || item.code,
    sortOrder: item.sort_order,
  }))
  const knownCodes = new Set(catalogItems.map((item) => item.code))
  const unknownItems = findings.value
    .map((item) => item.category || 'AST08')
    .filter((code, index, codes) => !knownCodes.has(code) && codes.indexOf(code) === index)
    .map((code) => ({ code, name: '安全风险', sortOrder: 999 }))
  return [...catalogItems, ...unknownItems].sort((a, b) => a.sortOrder - b.sortOrder || a.code.localeCompare(b.code))
})
const isRunning = computed(() => audit.value?.status === 'queued' || audit.value?.status === 'running')
const scoreLabel = computed(() => (audit.value ? String(audit.value.risk_score ?? 0) : '--'))
const llmReview = computed<LlmReviewSummary | null>(() => {
  const raw = audit.value?.summary?.llm_review
  return raw && typeof raw === 'object' ? (raw as LlmReviewSummary) : null
})

const riskCategories = computed<RiskCategory[]>(() => {
  const items = referenceItems.value
    .map((item) => {
      const related = findings.value.filter((finding) => finding.category === item.code)
      return {
        ...item,
        findings: related,
        severity: highestSeverity(related),
        hitCount: related.reduce((sum, finding) => sum + hitCount(finding), 0),
      }
    })
    .filter((item) => item.findings.length > 0)
  return items.sort((a, b) => severityOrder[b.severity] - severityOrder[a.severity] || a.code.localeCompare(b.code))
})

const missedCategoryCount = computed(() => {
  const hitCodes = new Set(riskCategories.value.map((item) => item.code))
  return catalog.value.filter((item) => !hitCodes.has(item.code)).length
})
const riskCategoryCount = computed(() => riskCategories.value.length)
const progress = computed<AuditProgress>(() => progressFromSummary())

const progressSteps = computed(() => [
  { key: 'prepare', label: '准备 Skill 包', description: '校验 zip 与基础信息', state: stepState(1) },
  { key: 'scan', label: '规则扫描', description: '检查危险代码、外传和依赖风险', state: stepState(2) },
  { key: 'classify', label: '风险归类', description: '按 AST 风险分类整理', state: stepState(3) },
  { key: 'report', label: '生成报告', description: '生成文件和处理建议', state: stepState(4) },
])

const severityBuckets = computed(() => {
  const raw = audit.value?.summary?.severity_counts
  const counts = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const fallback = severityCountFallback()
  return [
    { key: 'critical', label: '严重', value: numberValue(counts.critical, fallback.critical), className: 'border-red-200 bg-red-50 text-red-700' },
    { key: 'high', label: '高危', value: numberValue(counts.high, fallback.high), className: 'border-orange-200 bg-orange-50 text-orange-700' },
    { key: 'medium', label: '中危', value: numberValue(counts.medium, fallback.medium), className: 'border-amber-200 bg-amber-50 text-amber-700' },
    { key: 'low', label: '低危', value: numberValue(counts.low, fallback.low), className: 'border-slate-200 bg-slate-50 text-slate-700' },
  ]
})

const allClear = computed(() => severityBuckets.value.every((item) => item.value === 0))

async function loadAudit(): Promise<void> {
  loading.value = true
  try {
    catalog.value = await getAiPolicyRiskCatalog()
    await fetchAudit(true)
  } catch (e) {
    toast.error((e as { message?: string }).message || '报告数据加载失败')
  } finally {
    loading.value = false
  }
}

async function fetchAudit(resetExpanded = false, forceRefresh = false): Promise<void> {
  const params = forceRefresh ? { _t: Date.now() } : {}
  audit.value = await getAiPolicyAudit(String(route.params.auditId), params)
  if (!resetExpanded) return
  const initialExpanded: Record<string, boolean> = {}
  riskCategories.value.forEach((item) => {
    initialExpanded[item.code] = item.severity === 'critical' || item.severity === 'high'
  })
  expandedCategories.value = initialExpanded
}

async function refreshAudit(): Promise<void> {
  refreshing.value = true
  try {
    await fetchAudit(false, true)
  } catch (e) {
    toast.error((e as { message?: string }).message || '刷新失败')
  } finally {
    refreshing.value = false
  }
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === 'number' ? value : fallback
}

function severityCountFallback(): Record<string, number> {
  return findings.value.reduce(
    (counts, finding) => {
      const severity = finding.severity || 'unknown'
      if (severity in counts) counts[severity] += hitCount(finding)
      return counts
    },
    { critical: 0, high: 0, medium: 0, low: 0 } as Record<string, number>,
  )
}

function compareFinding(a: AiPolicyFinding, b: AiPolicyFinding): number {
  return severityOrder[b.severity || ''] - severityOrder[a.severity || ''] || String(a.category || '').localeCompare(String(b.category || ''))
}

function progressFromSummary(): AuditProgress {
  const raw = audit.value?.summary?.progress
  if (raw && typeof raw === 'object') {
    const progress = raw as Partial<AuditProgress>
    return {
      value: typeof progress.value === 'number' ? progress.value : 0,
      completed: typeof progress.completed === 'number' ? progress.completed : 0,
      total: typeof progress.total === 'number' ? progress.total : 4,
      step: typeof progress.step === 'string' ? progress.step : '处理中',
    }
  }
  if (!audit.value) return { value: 0, completed: 0, total: 4, step: '加载报告' }
  if (audit.value.status === 'queued') return { value: 0, completed: 0, total: 4, step: '等待审查任务启动' }
  if (audit.value.status === 'running') return { value: 25, completed: 1, total: 4, step: '正在扫描 Skill' }
  if (audit.value.status === 'failed') return { value: 100, completed: 0, total: 4, step: audit.value.error_message || '审查失败' }
  return { value: 100, completed: 4, total: 4, step: '报告已生成' }
}

function stepState(index: number): 'done' | 'running' | 'pending' | 'failed' {
  if (!audit.value) return 'pending'
  if (audit.value.status === 'failed') return index === Math.max(1, progress.value.completed + 1) ? 'failed' : 'pending'
  if (progress.value.completed >= index) return 'done'
  if ((audit.value.status === 'queued' || audit.value.status === 'running') && index === progress.value.completed + 1) return 'running'
  return audit.value.status === 'completed' ? 'done' : 'pending'
}

function stepIcon(state: string) {
  if (state === 'done') return CheckCircle2
  if (state === 'running') return Loader2
  return ScanLine
}

function highestSeverity(items: AiPolicyFinding[]): string {
  return ['critical', 'high', 'medium', 'low'].find((level) => items.some((item) => item.severity === level)) || 'none'
}

function hitCount(finding: AiPolicyFinding): number {
  if (typeof finding.hit_count === 'number' && finding.hit_count > 0) return finding.hit_count
  if (Array.isArray(finding.locations) && finding.locations.length > 0) return finding.locations.length
  return 1
}

function decisionLabel(): string {
  if (!audit.value) return '-'
  if (audit.value.status === 'queued') return '排队中'
  if (audit.value.status === 'running') return '审查中'
  if (audit.value.status === 'failed' || audit.value.decision === 'failed') return '审查失败'
  if (audit.value.decision === 'high_risk') return '高风险'
  if (audit.value.decision === 'attention_required') return '建议修改'
  return '通过'
}

function severityLabel(severity?: string): string {
  return {
    critical: '严重',
    high: '高危',
    medium: '中危',
    low: '低危',
    none: '未发现问题',
    unknown: '未知',
    '': '未分级',
  }[severity || ''] || String(severity)
}

function scoreTone(): string {
  if (!audit.value) return 'bg-slate-100 text-slate-600'
  if (audit.value.severity === 'critical') return 'bg-red-600 text-white'
  if (audit.value.severity === 'high' || audit.value.decision === 'high_risk') return 'bg-red-500 text-white'
  if (audit.value.severity === 'medium' || audit.value.decision === 'attention_required') return 'bg-amber-500 text-white'
  return 'bg-emerald-500 text-white'
}

function scoreBarClass(): string {
  if (!audit.value) return 'bg-slate-300'
  if (audit.value.severity === 'critical') return 'bg-red-600'
  if (audit.value.severity === 'high' || audit.value.decision === 'high_risk') return 'bg-red-500'
  if (audit.value.severity === 'medium' || audit.value.decision === 'attention_required') return 'bg-amber-500'
  return 'bg-emerald-500'
}

function severityClass(severity?: string): string {
  if (severity === 'critical') return 'bg-red-50 text-red-700 ring-red-200'
  if (severity === 'high') return 'bg-orange-50 text-orange-700 ring-orange-200'
  if (severity === 'medium') return 'bg-amber-50 text-amber-700 ring-amber-200'
  if (severity === 'low') return 'bg-slate-100 text-slate-600 ring-slate-200'
  return 'bg-emerald-50 text-emerald-700 ring-emerald-200'
}

function formatTime(value?: string | null): string {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function locationText(location: { file?: string; start_line?: number | null; end_line?: number | null }): string {
  const line = location.start_line ? `:${location.start_line}${location.end_line && location.end_line !== location.start_line ? `-${location.end_line}` : ''}` : ''
  return `${location.file || '未标明文件'}${line}`
}

function locationsOf(finding: AiPolicyFinding) {
  if (Array.isArray(finding.locations) && finding.locations.length > 0) return finding.locations
  const location = finding.location || {}
  return [{ ...location, snippet: finding.evidence?.snippet || finding.evidence?.matched_text || '' }]
}

function locationSnippet(location: { snippet?: string }): string {
  return location.snippet || '未提取到代码片段，可打开上方文件位置查看。'
}

function isCategoryExpanded(item: RiskCategory): boolean {
  return expandedCategories.value[item.code] ?? false
}

function toggleCategory(item: RiskCategory): void {
  expandedCategories.value = { ...expandedCategories.value, [item.code]: !isCategoryExpanded(item) }
}

function groupKey(category: RiskCategory, finding: AiPolicyFinding, index: number): string {
  return `${category.code}-${finding.rule_id || 'rule'}-${index}`
}

function isLocationsExpanded(key: string): boolean {
  return expandedLocations.value[key] ?? false
}

function toggleLocations(key: string): void {
  expandedLocations.value = { ...expandedLocations.value, [key]: !isLocationsExpanded(key) }
}

function shownLocations(finding: AiPolicyFinding, key: string) {
  const locations = locationsOf(finding)
  return isLocationsExpanded(key) ? locations : locations.slice(0, 3)
}

function llmCategoryReview(code: string): LlmCategoryReview | null {
  const reviews = llmReview.value?.category_reviews || []
  return reviews.find((item) => item.code === code) || null
}

function llmReviewText(code: string): string {
  if (!audit.value?.llm_review_used) return ''
  const review = llmCategoryReview(code)
  if (!review) return ''
  if (review.result === 'LLM 未单独研判') return 'LLM 未单独研判'
  return [review.result, review.reason, review.recommendation].filter(Boolean).join('；')
}

function reviewMethod(): string {
  return audit.value?.llm_review_used ? '规则扫描 + AI 深度审查' : '规则扫描'
}

function reviewNote(): string {
  if (!audit.value) return ''
  if (audit.value.llm_review_used) {
    const model = audit.value.llm_review_model || llmReview.value?.model || '所选模型'
    return `已完成规则扫描，并由 ${model} 做 AI 深度分析。结果供决策参考，不阻断发布，不改动文件。`
  }
  if (llmReview.value?.status && ['failed', 'unparsed', 'skipped'].includes(llmReview.value.status)) {
    return '已完成规则扫描。AI 深度分析未完成，本报告以规则扫描结果为准。'
  }
  return '已对 Skill 压缩包完成规则扫描。结果供决策参考，不阻断发布，不改动文件。'
}

function summaryText(): string {
  if (!audit.value) return ''
  if (audit.value.status === 'failed' || audit.value.decision === 'failed') return '审查未完成，请排查后重新发起。'
  if (audit.value.decision === 'high_risk') return '高危风险集中在供应链依赖与权限控制，建议优先处理后再评估使用。'
  if (audit.value.decision === 'attention_required') return '存在若干风险，建议逐项确认后决定是否调整。'
  return '未发现明显高危风险。'
}

function downloadReport(): void {
  if (!audit.value) return
  const token = localStorage.getItem('aihelms_token')
  fetch(getAiPolicyReportDownloadUrl(audit.value.audit_id), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
    .then((res) => {
      if (!res.ok) throw new Error('下载失败')
      return res.blob()
    })
    .then((blob) => {
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `${audit.value!.audit_id}.md`
      link.click()
      URL.revokeObjectURL(link.href)
    })
    .catch((e) => toast.error((e as { message?: string }).message || '下载失败'))
}

onMounted(loadAudit)
</script>

<template>
  <div class="space-y-5">
    <button class="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700" @click="router.push('/ai-policies')">
      <ArrowLeft class="h-4 w-4" />
      返回 AI Policies
    </button>

    <div v-if="loading" class="flex items-center justify-center gap-2 py-20 text-sm text-slate-400">
      <Loader2 class="h-4 w-4 animate-spin" />
      加载中...
    </div>

    <template v-else-if="audit">
      <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div class="mb-4 flex items-center justify-between gap-3">
          <h2 class="text-lg font-semibold text-slate-900">1. 概览</h2>
          <button class="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:border-purple-300" @click="downloadReport">
            <Download class="h-4 w-4" />
            Markdown
          </button>
        </div>
        <div class="grid gap-5 lg:grid-cols-[180px_minmax(0,1fr)]">
          <div class="flex h-40 flex-col items-center justify-center rounded-2xl" :class="scoreTone()">
            <div class="text-5xl font-black leading-none">{{ isRunning ? `${progress.value}%` : scoreLabel }}</div>
            <div class="mt-3 text-base font-semibold">{{ isRunning ? '审查中' : severityLabel(audit.severity) }}</div>
          </div>
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2 text-sm text-slate-500">
              <span>风险 {{ riskCategoryCount }} 类 · {{ audit.findings_count }} 处</span>
              <span class="text-slate-300">|</span>
              <span>审查方式 {{ reviewMethod() }}</span>
            </div>
            <h1 class="mt-3 text-2xl font-bold text-slate-900">{{ audit.skill_name }} 安全审查结果</h1>
            <div class="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
              <div class="h-full rounded-full transition-all" :class="scoreBarClass()" :style="{ width: `${Math.min(100, audit.risk_score || 0)}%` }" />
            </div>
            <div class="mt-5 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div class="rounded-xl bg-slate-50 p-3">
                <div class="text-xs text-slate-500">报告编号</div>
                <div class="mt-1 break-all font-medium text-slate-900">{{ audit.audit_id }}</div>
              </div>
              <div class="rounded-xl bg-slate-50 p-3">
                <div class="text-xs text-slate-500">审查开始时间</div>
                <div class="mt-1 font-medium text-slate-900">{{ formatTime(audit.started_at || audit.created_at) }}</div>
              </div>
              <div class="rounded-xl bg-slate-50 p-3">
                <div class="text-xs text-slate-500">审查结束时间</div>
                <div class="mt-1 font-medium text-slate-900">{{ formatTime(audit.finished_at) }}</div>
              </div>
              <div class="rounded-xl bg-slate-50 p-3">
                <div class="text-xs text-slate-500">审查结论</div>
                <div class="mt-1 font-medium text-slate-900">{{ decisionLabel() }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="isRunning" class="rounded-xl border border-indigo-100 bg-white p-5 shadow-sm">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold text-slate-900">审查进度</h2>
            <p class="mt-1 text-sm text-slate-500">当前阶段：{{ progress.step }}</p>
          </div>
          <div class="text-right">
            <div class="text-2xl font-bold text-indigo-700">{{ progress.value }}%</div>
            <div class="text-xs text-slate-500">{{ progress.completed }}/{{ progress.total }} 项检查完成</div>
            <button
              class="mt-2 inline-flex items-center gap-1 rounded-lg border border-indigo-200 bg-white px-3 py-1.5 text-xs font-medium text-indigo-700 hover:border-indigo-300 disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              :disabled="refreshing"
              @click="refreshAudit"
            >
              <Loader2 v-if="refreshing" class="h-3.5 w-3.5 animate-spin" />
              {{ refreshing ? '刷新中' : '刷新' }}
            </button>
          </div>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-slate-200">
          <div class="h-full rounded-full bg-indigo-500 transition-all" :style="{ width: `${progress.value}%` }" />
        </div>
        <div class="mt-5 grid grid-cols-1 gap-3 md:grid-cols-4">
          <div v-for="step in progressSteps" :key="step.key" class="rounded-xl border border-slate-200 p-3">
            <component
              :is="stepIcon(step.state)"
              class="mb-2 h-5 w-5"
              :class="step.state === 'done' ? 'text-emerald-600' : step.state === 'running' ? 'animate-spin text-indigo-600' : step.state === 'failed' ? 'text-red-600' : 'text-slate-300'"
            />
            <div class="text-sm font-semibold text-slate-900">{{ step.label }}</div>
            <div class="mt-1 text-xs text-slate-500">{{ step.description }}</div>
          </div>
        </div>
      </div>

      <div class="space-y-5">
        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-semibold text-slate-900">2. 审查说明</h2>
          <p class="mt-2 text-sm leading-6 text-slate-600">{{ reviewNote() }}</p>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-semibold text-slate-900">3. 审查对象</h2>
          <div class="mt-4 grid gap-3 md:grid-cols-4">
            <div class="rounded-xl bg-slate-50 p-3">
              <div class="text-xs text-slate-500">Skill 名称</div>
              <div class="mt-1 font-semibold text-slate-900">{{ audit.skill_name }}</div>
            </div>
            <div class="rounded-xl bg-slate-50 p-3">
              <div class="text-xs text-slate-500">版本</div>
              <div class="mt-1 font-semibold text-slate-900">v{{ audit.skill_version || '-' }}</div>
            </div>
            <div class="rounded-xl bg-slate-50 p-3">
              <div class="text-xs text-slate-500">风险</div>
              <div class="mt-1 font-semibold text-slate-900">发现 {{ audit.findings_count }} 处</div>
            </div>
            <div class="rounded-xl bg-slate-50 p-3">
              <div class="text-xs text-slate-500">风险等级</div>
              <div class="mt-1 font-semibold text-slate-900">{{ severityLabel(audit.severity) }}</div>
            </div>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="mb-4 text-lg font-semibold text-slate-900">4. 风险等级分布</h2>
          <div v-if="allClear" class="rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-700">
            <div class="text-base font-semibold">未发现风险</div>
          </div>
          <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div v-for="bucket in severityBuckets" :key="bucket.key" class="rounded-xl border p-4" :class="bucket.className">
              <div class="text-sm font-semibold">{{ bucket.label }}</div>
              <div class="mt-2 text-3xl font-black">{{ bucket.value }}</div>
            </div>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-100 p-5">
            <button class="inline-flex items-center gap-1 text-left text-lg font-semibold text-slate-900" @click="detailSectionOpen = !detailSectionOpen">
              <component :is="detailSectionOpen ? ChevronDown : ChevronRight" class="h-5 w-5 text-slate-500" />
              5. 详细结果
            </button>
          </div>
          <div v-if="detailSectionOpen" class="space-y-4 p-5">
            <div v-if="riskCategories.length === 0" class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
              未发现问题。
            </div>

            <section v-for="category in riskCategories" :key="category.code" class="rounded-xl border border-slate-200 p-4">
              <button class="block w-full text-left" @click="toggleCategory(category)">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">{{ category.code }}</span>
                  <span class="rounded-full px-2 py-0.5 text-xs font-medium ring-1" :class="severityClass(category.severity)">{{ severityLabel(category.severity) }}</span>
                  <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">发现 {{ category.hitCount }} 处</span>
                </div>
                <h3 class="mt-2 text-base font-semibold text-slate-900">
                  {{ category.code }} {{ category.name }} · {{ severityLabel(category.severity) }} · {{ category.hitCount }} 处
                </h3>
                <span class="mt-2 inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                  <component :is="isCategoryExpanded(category) ? ChevronDown : ChevronRight" class="h-3.5 w-3.5" />
                  {{ isCategoryExpanded(category) ? '收起' : '展开查看明细' }}
                </span>
              </button>

              <div v-if="isCategoryExpanded(category)" class="mt-4 space-y-3">
                <article v-for="(finding, index) in category.findings" :key="groupKey(category, finding, index)" class="rounded-xl bg-slate-50 p-4">
                  <div class="mb-2 flex flex-wrap items-center gap-2">
                    <span class="rounded-full px-2 py-0.5 text-xs font-medium ring-1" :class="severityClass(finding.severity)">{{ severityLabel(finding.severity) }}</span>
                    <span class="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200">发现 {{ hitCount(finding) }} 处</span>
                    <span v-if="finding.must_review" class="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">建议复核</span>
                  </div>
                  <h4 class="text-sm font-semibold text-slate-900">{{ finding.title || '安全风险' }}</h4>
                  <p v-if="finding.description" class="mt-3 text-sm leading-6 text-slate-600">{{ finding.description }}</p>
                  <p v-if="finding.recommendation" class="mt-2 text-sm leading-6 text-slate-700">处理建议：{{ finding.recommendation }}</p>
                  <p v-if="llmReviewText(category.code)" class="mt-2 text-sm leading-6 text-indigo-700">AI 研判：{{ llmReviewText(category.code) }}</p>

                  <div class="mt-3 rounded-lg bg-white p-3 ring-1 ring-slate-200">
                    <div class="mb-2 flex items-center justify-between gap-2">
                      <div class="text-xs font-medium text-slate-500">文件</div>
                      <button
                        v-if="locationsOf(finding).length > 3"
                        class="text-xs font-medium text-purple-600 hover:text-purple-700"
                        type="button"
                        @click="toggleLocations(groupKey(category, finding, index))"
                      >
                        {{ isLocationsExpanded(groupKey(category, finding, index)) ? '收起' : `展开全部 ${locationsOf(finding).length} 处` }}
                      </button>
                    </div>
                    <div class="space-y-2">
                      <div v-for="location in shownLocations(finding, groupKey(category, finding, index))" :key="locationText(location)" class="rounded-lg border border-slate-100 p-3">
                        <div class="break-all font-mono text-xs text-slate-600">{{ locationText(location) }}</div>
                        <pre class="mt-2 max-h-44 overflow-auto rounded-lg bg-slate-900 p-3 text-xs leading-5 text-slate-100">{{ locationSnippet(location) }}</pre>
                      </div>
                    </div>
                  </div>
                </article>
              </div>
            </section>

            <div v-if="missedCategoryCount > 0" class="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
              其余 {{ missedCategoryCount }} 类未发现问题
            </div>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-semibold text-slate-900">6. 总结</h2>
          <p class="mt-2 text-sm leading-6 text-slate-600">{{ summaryText() }}</p>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-5 text-xs leading-relaxed text-slate-500 shadow-sm">
          <h2 class="mb-2 text-lg font-semibold text-slate-900">7. 声明</h2>
          风险分类参考 OWASP Agentic Skills Top 10。OWASP 内容遵循 CC BY-SA 4.0，OWASP 不对本产品或审查结果作认证或背书。
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-5 text-sm leading-6 text-slate-600 shadow-sm">
          <h2 class="mb-2 text-lg font-semibold text-slate-900">8. 参考</h2>
          OWASP Agentic Skills Top 10 · AIHelms 审查规则与报告模板
        </div>
      </div>
    </template>
  </div>
</template>
