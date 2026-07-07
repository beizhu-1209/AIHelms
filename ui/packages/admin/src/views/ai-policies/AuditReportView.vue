<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getAiPolicyAudit,
  getAiPolicyRiskCatalog,
  getAiPolicyReportDownloadUrl,
  toast,
  type AiPolicyAudit,
  type AiPolicyAuditFileSummary,
  type AiPolicyFinding,
  type AiPolicyRiskCatalogItem,
} from '@aihelms/shared'
import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  Loader2,
  ScanLine,
} from 'lucide-vue-next'

interface RiskCategory {
  section: 'risk' | 'review'
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

interface LlmFindingReview {
  group_id: string
  finding_type?: string
  effective_severity?: string
  reason?: string
  recommendation?: string
}

interface LlmReviewSummary {
  status?: string
  model?: string
  overall_judgement?: string
  reason?: string
  message?: string
  finding_reviews?: LlmFindingReview[]
  category_reviews?: LlmCategoryReview[]
}

interface IntentAnalysis {
  declared_intent?: string
  actual_behavior?: string
  consistency?: string
  basis?: string
}

interface ExternalLinkSummary {
  url: string
  label?: string
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
const filesExpanded = ref(false)

const severityOrder: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
  info: 1,
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
const intentAnalysis = computed<IntentAnalysis | null>(() => {
  const raw = audit.value?.summary?.intent_analysis
  return raw && typeof raw === 'object' ? (raw as IntentAnalysis) : null
})

const riskFindings = computed(() =>
  findings.value.filter((finding) => finding.counts_toward_score !== false && ['critical', 'high', 'medium', 'low'].includes(finding.severity || '')),
)
const reviewFindings = computed(() =>
  findings.value.filter((finding) => finding.finding_type === 'review_note' && finding.counts_toward_score === false),
)
const packageFiles = computed<AiPolicyAuditFileSummary[]>(() => {
  const raw = audit.value?.summary?.files
  const findingStatuses = fileStatusesFromFindings()
  if (Array.isArray(raw)) {
    return (raw.filter((item) => item && typeof item === 'object') as AiPolicyAuditFileSummary[]).map((file) => {
      const fromFinding = findingStatuses.get(file.path)
      if (!fromFinding) return file
      const currentStatus = String(file.status || file.severity || '')
      const status = statusRank(fromFinding.status) > statusRank(currentStatus) ? fromFinding.status : currentStatus
      return {
        ...file,
        status: status as AiPolicyAuditFileSummary['status'],
        severity: status as AiPolicyAuditFileSummary['severity'],
        risk_count: Math.max(file.risk_count || 0, fromFinding.riskCount),
      }
    })
  }
  const files = new Map<string, AiPolicyAuditFileSummary>()
  findings.value.forEach((finding) => {
    locationsOf(finding).forEach((location) => {
      if (!location.file) return
      const fromFinding = findingStatuses.get(location.file)
      const status = fromFinding?.status || 'clean'
      files.set(location.file, {
        path: location.file,
        role_label: '文件',
        severity: status as AiPolicyAuditFileSummary['severity'],
        status: status as AiPolicyAuditFileSummary['status'],
        risk_count: fromFinding?.riskCount || 0,
      })
    })
  })
  return [...files.values()]
})
const shownPackageFiles = computed(() => (filesExpanded.value ? packageFiles.value : packageFiles.value.slice(0, 14)))
const externalLinks = computed<ExternalLinkSummary[]>(() => {
  const raw = audit.value?.summary?.external_links
  if (!Array.isArray(raw)) return []
  return raw.flatMap((item) => {
    if (typeof item === 'string') return [{ url: item }]
    if (!item || typeof item !== 'object') return []
    const record = item as Record<string, unknown>
    return typeof record.url === 'string' ? [{ url: record.url, label: typeof record.label === 'string' ? record.label : undefined }] : []
  })
})

const riskCategories = computed<RiskCategory[]>(() => categoriesFor(riskFindings.value, 'risk'))
const reviewCategories = computed<RiskCategory[]>(() => categoriesFor(reviewFindings.value, 'review'))

function categoriesFor(categoryFindings: AiPolicyFinding[], section: 'risk' | 'review'): RiskCategory[] {
  const items = referenceItems.value
    .map((item) => {
      const related = categoryFindings.filter((finding) => finding.category === item.code)
      return {
        section,
        ...item,
        findings: related,
        severity: highestSeverity(related),
        hitCount: related.reduce((sum, finding) => sum + hitCount(finding), 0),
      }
    })
    .filter((item) => item.findings.length > 0)
  return items.sort((a, b) => severityOrder[b.severity] - severityOrder[a.severity] || a.code.localeCompare(b.code))
}

const progress = computed<AuditProgress>(() => progressFromSummary())

const progressSteps = computed(() => [
  { key: 'prepare', label: '准备 Skill 包', description: '校验 zip 与基础信息', state: stepState(1) },
  { key: 'scan', label: '规则扫描', description: '检查危险代码、外传和依赖风险', state: stepState(2) },
  { key: 'classify', label: '风险归类', description: '整理风险类型和证据', state: stepState(3) },
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
  ;[...riskCategories.value, ...reviewCategories.value].forEach((item) => {
    initialExpanded[categorySectionKey(item)] = item.severity === 'critical' || item.severity === 'high'
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
    const total = typeof progress.total === 'number' ? progress.total : 4
    const value = typeof progress.value === 'number' ? progress.value : 0
    const completed = typeof progress.completed === 'number' ? progress.completed : 0
    if (audit.value?.status === 'queued' || audit.value?.status === 'running') {
      return {
        value: Math.min(99, Math.max(0, value)),
        completed: Math.min(Math.max(0, completed), Math.max(0, total - 1)),
        total,
        step: typeof progress.step === 'string' ? progress.step : '处理中',
      }
    }
    return {
      value,
      completed,
      total,
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
  return ['critical', 'high', 'medium', 'low', 'info'].find((level) => items.some((item) => item.severity === level)) || 'none'
}

function hitCount(finding: AiPolicyFinding): number {
  if (typeof finding.hit_count === 'number' && finding.hit_count > 0) return finding.hit_count
  if (Array.isArray(finding.locations) && finding.locations.length > 0) return finding.locations.length
  return 1
}

function statusRank(status: string): number {
  return {
    critical: 6,
    high: 5,
    medium: 4,
    low: 3,
    review: 2,
    info: 2,
    entry: 1,
    clean: 0,
    none: 0,
    unchecked: 0,
  }[status] ?? 0
}

function fileStatusesFromFindings(): Map<string, { status: string; riskCount: number }> {
  const statuses = new Map<string, { status: string; riskCount: number }>()
  findings.value.forEach((finding) => {
    if (finding.finding_type === 'false_positive') return
    const status = finding.counts_toward_score === false ? 'review' : finding.severity || 'review'
    locationsOf(finding).forEach((location) => {
      if (!location.file) return
      const current = statuses.get(location.file)
      const nextStatus = !current || statusRank(status) > statusRank(current.status) ? status : current.status
      statuses.set(location.file, {
        status: nextStatus,
        riskCount: (current?.riskCount || 0) + hitCount(finding),
      })
    })
  })
  return statuses
}

function decisionLabel(): string {
  if (!audit.value) return '-'
  if (audit.value.status === 'queued') return '排队中'
  if (audit.value.status === 'running') return '审查中'
  if (audit.value.status === 'failed' || audit.value.decision === 'failed') return '审查失败'
  if (audit.value.decision === 'high_risk') return '高风险'
  if (audit.value.severity === 'high' || audit.value.severity === 'critical') return '存在风险'
  if (audit.value.decision === 'attention_required') return '需关注'
  return '可信'
}

function severityLabel(severity?: string): string {
  return {
    critical: '严重',
    high: '高危',
    medium: '中危',
    low: '低危',
    info: '提示',
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

function scoreWidth(): string {
  return `${Math.min(100, Math.max(0, audit.value?.risk_score || 0))}%`
}

function fileCountText(): string {
  const raw = audit.value?.summary?.file_count
  if (typeof raw === 'number') return String(raw)
  if (packageFiles.value.length > 0) return String(packageFiles.value.length)
  return '-'
}

function packageSizeText(): string {
  return formatBytes(audit.value?.summary?.source_size_bytes)
}

function formatBytes(value: unknown): string {
  if (typeof value !== 'number' || value <= 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = value
  let index = 0
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return index === 0 ? `${Math.round(size)} ${units[index]}` : `${size.toFixed(1)} ${units[index]}`
}

function severityClass(severity?: string): string {
  if (severity === 'critical') return 'bg-red-50 text-red-700 ring-red-200'
  if (severity === 'high') return 'bg-orange-50 text-orange-700 ring-orange-200'
  if (severity === 'medium') return 'bg-amber-50 text-amber-700 ring-amber-200'
  if (severity === 'low') return 'bg-slate-100 text-slate-600 ring-slate-200'
  return 'bg-emerald-50 text-emerald-700 ring-emerald-200'
}

function fileStatusLabel(file: AiPolicyAuditFileSummary): string {
  const status = String(file.status || file.severity || '')
  const labels: Record<string, string> = {
    critical: '需关注',
    high: '需关注',
    medium: '需关注',
    low: '需关注',
    review: '建议复核',
    entry: '入口',
    clean: '未发现问题',
    unchecked: '未检查',
    none: '未发现问题',
    info: '建议复核',
  }
  return labels[status] || '未发现问题'
}

function fileStatusClass(file: AiPolicyAuditFileSummary): string {
  const status = file.status || file.severity || ''
  if (status === 'critical' || status === 'high') return 'bg-red-50 text-red-700 ring-red-200'
  if (status === 'medium' || status === 'review' || status === 'info') return 'bg-amber-50 text-amber-700 ring-amber-200'
  if (status === 'low') return 'bg-sky-50 text-sky-700 ring-sky-200'
  if (status === 'entry') return 'bg-indigo-50 text-indigo-700 ring-indigo-200'
  return 'bg-emerald-50 text-emerald-700 ring-emerald-200'
}

function fileDisplayName(path?: string): string {
  if (!path) return '未命名文件'
  const parts = path.split('/').filter(Boolean)
  return parts[parts.length - 1] || path
}

function elapsedTime(): string {
  if (!audit.value?.started_at || !audit.value?.finished_at) return '-'
  const start = new Date(audit.value.started_at).getTime()
  const end = new Date(audit.value.finished_at).getTime()
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return '-'
  const seconds = Math.round((end - start) / 1000)
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

function shortHash(value?: string): string {
  if (!value) return '-'
  return value.length > 16 ? `${value.slice(0, 8)}...${value.slice(-8)}` : value
}

function copyHash(): void {
  if (!audit.value?.source_sha256) return
  const write = navigator.clipboard?.writeText(audit.value.source_sha256)
  if (!write) {
    toast.error('复制失败')
    return
  }
  write.then(
    () => toast.success('SHA-256 已复制'),
    () => toast.error('复制失败'),
  )
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

function categorySectionKey(item: RiskCategory): string {
  return `${item.section}-${item.code}`
}

function isCategoryExpanded(item: RiskCategory): boolean {
  return expandedCategories.value[categorySectionKey(item)] ?? false
}

function toggleCategory(item: RiskCategory): void {
  expandedCategories.value = { ...expandedCategories.value, [categorySectionKey(item)]: !isCategoryExpanded(item) }
}

function groupKey(category: RiskCategory, finding: AiPolicyFinding, index: number): string {
  return finding.group_id || `${category.code}-${finding.rule_id || 'rule'}-${index}`
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

function llmFindingReview(groupId?: string): LlmFindingReview | null {
  if (!groupId) return null
  const reviews = llmReview.value?.finding_reviews || []
  return reviews.find((item) => item.group_id === groupId) || null
}

function llmReviewText(finding: AiPolicyFinding): string {
  if (!audit.value?.llm_review_used) return ''
  const review = llmFindingReview(finding.group_id)
  if (review) return [review.reason, review.recommendation].filter(Boolean).join('；')
  const categoryReview = llmCategoryReview(finding.category || '')
  if (!categoryReview || categoryReview.result === 'LLM 未单独研判') return ''
  return [categoryReview.result, categoryReview.reason, categoryReview.recommendation].filter(Boolean).join('；')
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

function chapterTwoTitle(): string {
  return '2. 意图与行为分析'
}

function behaviorSummary(): string {
  if (!audit.value) return ''
  if (audit.value.llm_review_used) {
    return llmReview.value?.overall_judgement || llmReview.value?.reason || reviewNote()
  }
  if (llmReview.value?.status && ['failed', 'unparsed', 'skipped'].includes(llmReview.value.status)) {
    return 'AI 深度审查未完成，本报告以规则扫描结果为准。'
  }
  return '未开启 AI 深度审查，本报告为规则初筛，可能存在误报。'
}

function findingScopeText(): string {
  const parts: string[] = []
  if (riskCategories.value.length > 0) {
    parts.push(`需要关注的风险 ${riskCategories.value.length} 类、${riskFindings.value.reduce((sum, finding) => sum + hitCount(finding), 0)} 处`)
  }
  if (reviewFindings.value.length > 0) {
    parts.push(`建议复核 ${reviewFindings.value.reduce((sum, finding) => sum + hitCount(finding), 0)} 处`)
  }
  return parts.join('；')
}

function declaredIntentText(): string {
  return intentAnalysis.value?.declared_intent || `该 Skill 名称为 ${audit.value?.skill_name || '-'}，规则扫描未提取到更完整的声明用途。`
}

function actualBehaviorText(): string {
  if (intentAnalysis.value?.actual_behavior) return intentAnalysis.value.actual_behavior
  const scope = findingScopeText()
  if (scope) return `规则扫描已完成，发现${scope}。未发现需要阻断发布的自动处置项。`
  return '规则扫描未发现明显高风险行为。'
}

function consistencyText(): string {
  if (intentAnalysis.value?.consistency) return intentAnalysis.value.consistency
  if (audit.value?.decision === 'high_risk') return '存在偏差'
  if (audit.value?.decision === 'attention_required') return '建议复核'
  if (audit.value?.status === 'failed') return '审查未完成'
  return '未发现明显偏差'
}

function basisText(): string {
  if (intentAnalysis.value?.basis) return intentAnalysis.value.basis
  const llmStatus = llmReview.value?.status
  const aiNote = llmStatus && ['failed', 'unparsed', 'skipped'].includes(llmStatus)
    ? 'AI 深度分析结果未形成可展示内容，本章依据规则扫描结果生成。'
    : ''
  return `${aiNote}${conclusionText()}`
}

function conclusionText(): string {
  if (audit.value?.decision === 'high_risk') return '发现需要优先关注的高风险行为，请结合下方证据复核。'
  if (audit.value?.decision === 'attention_required') return '规则扫描未发现高风险行为，中低风险项可按下方建议确认。'
  if (audit.value?.status === 'failed') return '审查未完成，请排查后重新发起。'
  return '未发现明显高风险行为。'
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
    <div class="flex flex-wrap items-center justify-between gap-3">
      <button class="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700" @click="router.push('/ai-policies')">
        <ArrowLeft class="h-4 w-4" />
        返回 AI Policies
      </button>
      <button v-if="audit && !loading" class="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:border-purple-300" @click="downloadReport">
        <Download class="h-4 w-4" />
        Markdown
      </button>
    </div>

    <div v-if="loading" class="flex items-center justify-center gap-2 py-20 text-sm text-slate-400">
      <Loader2 class="h-4 w-4 animate-spin" />
      加载中...
    </div>

    <template v-else-if="audit">
      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <main class="space-y-5">
          <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 class="text-lg font-semibold text-slate-900">1. 概览</h2>
            <div class="mt-4 grid gap-5 lg:grid-cols-[176px_minmax(0,1fr)]">
              <div class="flex h-40 flex-col items-center justify-center rounded-2xl" :class="scoreTone()">
                <div class="text-5xl font-black leading-none">{{ isRunning ? `${progress.value}%` : scoreLabel }}</div>
                <div class="mt-3 text-base font-semibold">{{ isRunning ? '审查中' : decisionLabel() }}</div>
              </div>
              <div class="min-w-0">
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div class="min-w-0">
                    <h1 class="break-words text-2xl font-semibold text-slate-900">{{ audit.skill_name }} · v{{ audit.skill_version || '-' }}</h1>
                    <p class="mt-1 text-sm text-slate-500">报告编号 {{ audit.audit_id }}</p>
                  </div>
                  <span class="shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ring-1" :class="severityClass(audit.severity)">
                    {{ decisionLabel() }}
                  </span>
                </div>
                <div class="mt-4 flex flex-wrap items-center gap-2 text-sm text-slate-500">
                  <span>{{ reviewMethod() }}</span>
                  <span class="text-slate-300">|</span>
                  <span>文件 {{ fileCountText() }}</span>
                  <span class="text-slate-300">|</span>
                  <span>包大小 {{ packageSizeText() }}</span>
                  <span class="text-slate-300">|</span>
                  <span>耗时 {{ elapsedTime() }}</span>
                  <span class="text-slate-300">|</span>
                  <span>SHA-256 {{ shortHash(audit.source_sha256) }}</span>
                  <button v-if="audit.source_sha256" class="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700" type="button" @click="copyHash">
                    <Copy class="h-3.5 w-3.5" />
                    复制
                  </button>
                </div>
                <div class="mt-4 flex items-center gap-3">
                  <div class="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                    <div class="h-full rounded-full transition-all" :class="scoreBarClass()" :style="{ width: scoreWidth() }" />
                  </div>
                  <span class="w-16 text-right text-sm font-semibold text-slate-600">{{ isRunning ? `${progress.value}/100` : `${scoreLabel}/100` }}</span>
                </div>
                <div class="mt-5 text-sm font-semibold text-slate-900">风险等级</div>
                <div class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div v-for="bucket in severityBuckets" :key="bucket.key" class="rounded-xl border p-4" :class="bucket.className">
                    <div class="text-sm font-semibold">{{ bucket.label }}</div>
                    <div class="mt-2 text-3xl font-black">{{ bucket.value }}</div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section v-if="isRunning" class="rounded-xl border border-indigo-100 bg-white p-5 shadow-sm">
            <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 class="text-lg font-semibold text-slate-900">审查进度</h2>
                <p class="mt-1 text-sm text-slate-500">当前阶段：{{ progress.step }}</p>
              </div>
              <div class="text-right">
                <div class="text-2xl font-bold text-indigo-700">{{ progress.value }}%</div>
                <div class="text-xs text-slate-500">{{ progress.completed }}/{{ progress.total }} 项检查完成</div>
                <button class="mt-2 inline-flex items-center gap-1 rounded-lg border border-indigo-200 bg-white px-3 py-1.5 text-xs font-medium text-indigo-700 hover:border-indigo-300 disabled:cursor-not-allowed disabled:opacity-60" type="button" :disabled="refreshing" @click="refreshAudit">
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
                <component :is="stepIcon(step.state)" class="mb-2 h-5 w-5" :class="step.state === 'done' ? 'text-emerald-600' : step.state === 'running' ? 'animate-spin text-indigo-600' : step.state === 'failed' ? 'text-red-600' : 'text-slate-300'" />
                <div class="text-sm font-semibold text-slate-900">{{ step.label }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ step.description }}</div>
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 class="text-lg font-semibold text-slate-900">{{ chapterTwoTitle() }}</h2>
            <div class="mt-4 space-y-4 text-sm leading-6 text-slate-600">
              <div>
                <div class="font-semibold text-slate-900">声明用途</div>
                <p class="mt-1">{{ declaredIntentText() }}</p>
              </div>
              <div>
                <div class="font-semibold text-slate-900">实际行为</div>
                <p class="mt-1">{{ actualBehaviorText() }}</p>
              </div>
              <div>
                <div class="font-semibold text-slate-900">一致性判断</div>
                <p class="mt-1">{{ consistencyText() }}</p>
              </div>
              <div>
                <div class="font-semibold text-slate-900">判断依据</div>
                <p class="mt-1">{{ basisText() }}</p>
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div class="border-b border-slate-100 p-5">
              <button class="inline-flex items-center gap-1 text-left text-lg font-semibold text-slate-900" @click="detailSectionOpen = !detailSectionOpen">
                <component :is="detailSectionOpen ? ChevronDown : ChevronRight" class="h-5 w-5 text-slate-500" />
                3. 详细结果
              </button>
            </div>
            <div v-if="detailSectionOpen" class="space-y-4 p-5">
              <div v-if="riskCategories.length === 0 && reviewCategories.length === 0" class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
                未发现问题。
              </div>

              <div v-if="riskCategories.length > 0" class="text-sm font-semibold text-slate-900">需要关注的风险</div>
              <section v-for="category in riskCategories" :key="categorySectionKey(category)" class="rounded-xl border border-slate-200 p-4">
                <button class="block w-full text-left" @click="toggleCategory(category)">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="rounded-full px-2 py-0.5 text-xs font-medium ring-1" :class="severityClass(category.severity)">{{ severityLabel(category.severity) }}</span>
                    <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">发现 {{ category.hitCount }} 处</span>
                  </div>
                  <h3 class="mt-2 text-base font-semibold text-slate-900">
                    {{ category.name }} · {{ severityLabel(category.severity) }} · {{ category.hitCount }} 处
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
                    </div>
                    <h4 class="text-sm font-semibold text-slate-900">{{ finding.title || '安全风险' }}</h4>
                    <p v-if="finding.description" class="mt-3 text-sm leading-6 text-slate-600">{{ finding.description }}</p>
                    <p v-if="finding.recommendation" class="mt-2 text-sm leading-6 text-slate-700">处理建议：{{ finding.recommendation }}</p>
                    <p v-if="llmReviewText(finding)" class="mt-2 text-sm leading-6 text-indigo-700">AI 研判：{{ llmReviewText(finding) }}</p>
                    <div class="mt-3 rounded-lg bg-white p-3 ring-1 ring-slate-200">
                      <div class="mb-2 flex flex-wrap items-center gap-2">
                        <div class="text-xs font-medium text-slate-500">文件</div>
                        <button v-if="locationsOf(finding).length > 3" class="text-xs font-medium text-purple-600 hover:text-purple-700" type="button" @click="toggleLocations(groupKey(category, finding, index))">
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

              <div v-if="riskCategories.length === 0 && reviewCategories.length > 0" class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                本次未发现需要立即关注的高风险项。
              </div>

              <div v-if="reviewCategories.length > 0" class="text-sm font-semibold text-amber-700">建议复核</div>
              <section v-for="category in reviewCategories" :key="categorySectionKey(category)" class="rounded-xl border border-amber-200 p-4">
                <button class="block w-full text-left" type="button" @click="toggleCategory(category)">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 ring-1 ring-amber-200">{{ severityLabel(category.severity) }}</span>
                    <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">发现 {{ category.hitCount }} 处</span>
                  </div>
                  <h3 class="mt-2 text-base font-semibold text-slate-900">
                    {{ category.name }} · {{ severityLabel(category.severity) }} · {{ category.hitCount }} 处
                  </h3>
                  <span class="mt-2 inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                    <component :is="isCategoryExpanded(category) ? ChevronDown : ChevronRight" class="h-3.5 w-3.5" />
                    {{ isCategoryExpanded(category) ? '收起' : '展开查看明细' }}
                  </span>
                </button>
                <div v-if="isCategoryExpanded(category)" class="mt-4 space-y-3">
                  <article v-for="(finding, index) in category.findings" :key="groupKey(category, finding, index)" class="rounded-xl bg-slate-50 p-4">
                    <div class="mb-2 flex flex-wrap items-center gap-2">
                      <span class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">建议复核</span>
                      <span class="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200">发现 {{ hitCount(finding) }} 处</span>
                    </div>
                    <h4 class="text-sm font-semibold text-slate-900">{{ finding.title || '建议复核' }}</h4>
                    <p class="mt-2 text-sm leading-6 text-slate-600">{{ finding.denoise_reason || finding.description || '该问题缺少可执行证据，建议复核。' }}</p>
                    <p v-if="llmReviewText(finding)" class="mt-2 text-sm leading-6 text-indigo-700">AI 研判：{{ llmReviewText(finding) }}</p>
                    <div class="mt-3 rounded-lg bg-white p-3 ring-1 ring-slate-200">
                      <div class="mb-2 flex flex-wrap items-center gap-2">
                        <div class="text-xs font-medium text-slate-500">文件</div>
                        <button v-if="locationsOf(finding).length > 3" class="text-xs font-medium text-purple-600 hover:text-purple-700" type="button" @click="toggleLocations(groupKey(category, finding, index))">
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
            </div>
          </section>

          <section class="rounded-xl border border-slate-200 bg-white p-5 text-xs leading-relaxed text-slate-500 shadow-sm">
            <h2 class="mb-2 text-lg font-semibold text-slate-900">4. 声明</h2>
            风险分类参考 OWASP Agentic Skills Top 10。OWASP 内容遵循 CC BY-SA 4.0，OWASP 不对本产品或审查结果作认证或背书。
            <div class="mt-2">参考：OWASP Agentic Skills Top 10；AIHelms 审查规则与报告模板。</div>
          </section>
        </main>

        <aside class="space-y-5 xl:sticky xl:top-5 xl:self-start">
          <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-base font-semibold text-slate-900">Skill 包文件 ({{ fileCountText() }})</h2>
            </div>
            <div v-if="packageFiles.length > 0" class="mt-4 divide-y divide-slate-100">
              <div v-for="file in shownPackageFiles" :key="file.path" class="flex items-start justify-between gap-3 py-2.5" :title="file.path">
                <div class="min-w-0">
                  <div class="truncate font-mono text-xs text-slate-700">{{ fileDisplayName(file.path) }}</div>
                  <div v-if="file.path !== fileDisplayName(file.path)" class="mt-0.5 truncate text-[11px] text-slate-400">
                    {{ file.path }}
                  </div>
                </div>
                <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1" :class="fileStatusClass(file)">
                  {{ fileStatusLabel(file) }}
                </span>
              </div>
              <button v-if="packageFiles.length > 14" class="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:border-purple-300 hover:text-purple-700" type="button" @click="filesExpanded = !filesExpanded">
                {{ filesExpanded ? '收起文件' : `展开全部 ${packageFiles.length} 个文件` }}
              </button>
            </div>
            <div v-else class="mt-4 rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm text-slate-500">
              本报告未记录文件清单。
            </div>
          </section>

          <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-base font-semibold text-slate-900">外部链接 ({{ externalLinks.length }})</h2>
            </div>
            <div v-if="externalLinks.length > 0" class="mt-4 space-y-2">
              <a v-for="link in externalLinks" :key="link.url" class="block truncate rounded-lg border border-slate-100 px-3 py-2 text-xs text-slate-600 hover:border-purple-200 hover:text-purple-700" :href="link.url" target="_blank" rel="noreferrer">
                {{ link.label || link.url }}
              </a>
            </div>
            <div v-else class="mt-4 rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm text-slate-500">
              未发现外部链接
            </div>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>
