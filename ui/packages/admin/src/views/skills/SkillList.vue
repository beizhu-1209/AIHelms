<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  createSkillCategory,
  createSkillSecurityAudit,
  deleteSkillCategory,
  getSkillCategories,
  getSkills,
  toast,
  type Skill,
  type SkillCategory,
  usePermission,
} from '@aihelms/shared'
import { Download, FileText, Package, Plus, Search, X } from 'lucide-vue-next'
import * as icons from 'lucide-vue-next'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

type PublishStatusFilter = 'all' | 'published' | 'unpublished'
type SecurityStatus = 'not_scanned' | 'queued' | 'running' | 'completed' | 'failed'
type SecurityDecision = 'passed' | 'attention_required' | 'high_risk' | 'failed'

interface SkillSecuritySummary {
  auditId: string
  status: SecurityStatus
  decision: SecurityDecision
  label: string
  score: number | null
  shortAdvice: string
}

const statusTone: Record<SecurityDecision | 'running' | 'not_scanned', string> = {
  passed: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  attention_required: 'bg-amber-50 text-amber-700 ring-amber-200',
  high_risk: 'bg-red-50 text-red-700 ring-red-200',
  failed: 'bg-stone-100 text-stone-700 ring-stone-200',
  running: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  not_scanned: 'bg-slate-100 text-slate-600 ring-slate-200',
}

const { hasPermission } = usePermission()
const router = useRouter()

const skills = ref<Skill[]>([])
const categories = ref<SkillCategory[]>([])
const loading = ref(false)
const selectedCategory = ref<string | null>(null)
const skillQuery = ref('')
const publishStatus = ref<PublishStatusFilter>('all')
const showCategoryForm = ref(false)
const categoryFormName = ref('')
const categoryFormDescription = ref('')
const deleteCategoryTarget = ref<SkillCategory | null>(null)
const runningSkillIds = ref<Set<number>>(new Set())

const categoriesWithCount = computed(() => {
  const counts = new Map<string, number>()
  for (const s of skills.value) counts.set(s.category, (counts.get(s.category) || 0) + 1)
  return categories.value.map((c) => ({ ...c, count: counts.get(c.name) || 0 }))
})

const filteredSkills = computed(() => {
  const normalizedQuery = skillQuery.value.trim().toLowerCase()
  return skills.value.filter((skill) => {
    const matchesCategory = !selectedCategory.value || skill.category === selectedCategory.value
    const matchesName = !normalizedQuery || skill.name.toLowerCase().includes(normalizedQuery)
    const matchesPublishStatus =
      publishStatus.value === 'all' ||
      (publishStatus.value === 'published' && skill.is_published) ||
      (publishStatus.value === 'unpublished' && !skill.is_published)
    return matchesCategory && matchesName && matchesPublishStatus
  })
})

function getIconComponent(name: string) {
  return (icons as Record<string, unknown>)[name] || null
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const [skillsRes, catsRes] = await Promise.all([getSkills(1, 200), getSkillCategories()])
    skills.value = skillsRes.items
    categories.value = catsRes
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

function openDetail(skill: Skill): void {
  router.push(`/skills/${skill.id}`)
}

function openCreate(): void {
  router.push('/skills/new')
}

function openAiPolicies(skill: Skill): void {
  const security = getSkillSecuritySummaryForSkill(skill)
  if (!security.auditId) {
    toast.error('暂无可查看的审查报告')
    return
  }
  router.push(`/ai-policies/audits/${security.auditId}?skill_id=${skill.id}`)
}

async function startSecurityAudit(skill: Skill): Promise<void> {
  if (!skill.has_zip) {
    toast.error('请先上传 Skill zip 包')
    return
  }
  try {
    runningSkillIds.value = new Set([...runningSkillIds.value, skill.id])
    const audit = await createSkillSecurityAudit(skill.id)
    skill.security_status = audit.status
    skill.security_decision = audit.decision
    skill.security_severity = audit.severity
    skill.security_risk_score = audit.risk_score
    skill.latest_ai_policies_audit_code = audit.audit_id
    toast.success('已提交审查，可在 AI Policies 查看进度')
  } catch (e) {
    runningSkillIds.value = new Set([...runningSkillIds.value].filter((id) => id !== skill.id))
    toast.error((e as { message?: string }).message || '审查任务创建失败')
  }
}

function getSkillSecuritySummaryForSkill(skill: Skill): SkillSecuritySummary {
  if (!skill.has_zip) {
    return {
      auditId: '',
      status: 'not_scanned',
      decision: 'passed',
      label: '未上传',
      score: null,
      shortAdvice: '上传 zip 后可发起安全审查。',
    }
  }
  return {
    auditId: skill.latest_ai_policies_audit_code || '',
    status: runningSkillIds.value.has(skill.id) ? 'running' : (skill.security_status || 'not_scanned'),
    decision: (skill.security_decision || 'passed') as SecurityDecision,
    label: securityLabel(skill),
    score: skill.security_risk_score ?? null,
    shortAdvice: securityAdvice(skill),
  }
}

function securityLabel(skill: Skill): string {
  if (runningSkillIds.value.has(skill.id) || skill.security_status === 'queued' || skill.security_status === 'running') return '审查中'
  if (skill.security_status === 'failed' || skill.security_decision === 'failed') return '审查失败'
  if (skill.security_status !== 'completed') return '未审查'
  if (skill.security_decision === 'high_risk') return '高风险'
  if (skill.security_decision === 'attention_required') return '建议修改'
  return '通过'
}

function securityAdvice(skill: Skill): string {
  if (runningSkillIds.value.has(skill.id) || skill.security_status === 'queued' || skill.security_status === 'running') {
    return '正在检查 Skill 压缩包内容，完成后自动生成报告。'
  }
  if (skill.security_status === 'failed' || skill.security_decision === 'failed') {
    return '审查执行失败，请重新发起或检查 zip 文件。'
  }
  if (skill.security_status !== 'completed') return 'zip 已上传，点击审查后生成独立审查任务。'
  if (skill.security_decision === 'high_risk') return '发现高优先级风险，建议发布前复核。'
  if (skill.security_decision === 'attention_required') return '存在需要关注的风险点，建议按报告处理。'
  return '未发现明显高优先级风险。'
}

function securityBadgeClass(summary: SkillSecuritySummary): string {
  if (summary.status === 'running' || summary.status === 'queued') return statusTone.running
  if (summary.status === 'not_scanned') return statusTone.not_scanned
  return statusTone[summary.decision]
}

async function handleCreateCategory(): Promise<void> {
  if (!categoryFormName.value.trim()) {
    toast.error('请输入分类名称')
    return
  }
  try {
    await createSkillCategory({
      name: categoryFormName.value.trim(),
      description: categoryFormDescription.value.trim(),
    })
    toast.success('分类创建成功')
    showCategoryForm.value = false
    categoryFormName.value = ''
    categoryFormDescription.value = ''
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建失败')
  }
}

async function confirmDeleteCategory(): Promise<void> {
  if (!deleteCategoryTarget.value) return
  try {
    await deleteSkillCategory(deleteCategoryTarget.value.id)
    toast.success('分类删除成功')
    if (selectedCategory.value === deleteCategoryTarget.value.name) selectedCategory.value = null
    deleteCategoryTarget.value = null
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '删除失败')
  }
}

onMounted(loadData)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Skill 管理</h1>
        <p class="mt-1 text-sm text-slate-500">管理 Skill zip 包、发布状态和安全审查结果。</p>
      </div>
      <button
        v-if="hasPermission('skill:create')"
        class="flex items-center gap-1.5 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-purple-500"
        @click="openCreate"
      >
        <Plus class="h-4 w-4" />
        新建 Skill
      </button>
    </div>

    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap items-center gap-2">
        <button
          class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
          :class="!selectedCategory ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          @click="selectedCategory = null"
        >
          全部 ({{ skills.length }})
        </button>
        <div v-for="cat in categoriesWithCount" :key="cat.id" class="group flex items-center">
          <button
            class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
            :class="selectedCategory === cat.name ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
            @click="selectedCategory = cat.name"
          >
            {{ cat.name }} ({{ cat.count }})
          </button>
          <button
            v-if="hasPermission('skill:delete')"
            class="ml-1 hidden text-slate-400 hover:text-red-500 group-hover:inline-block"
            @click="deleteCategoryTarget = cat"
          >
            <X class="h-3 w-3" />
          </button>
        </div>
        <button
          v-if="hasPermission('skill:create')"
          class="rounded-full border border-dashed border-slate-300 px-3 py-1 text-xs text-slate-500 transition-colors hover:border-purple-500 hover:text-purple-600"
          @click="showCategoryForm = true"
        >
          + 新建分类
        </button>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <label class="relative block">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            v-model="skillQuery"
            class="h-9 w-56 rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-700 shadow-sm focus:border-purple-500 focus:outline-none"
            placeholder="搜索 Skill 名称"
          />
        </label>
        <select
          v-model="publishStatus"
          class="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 shadow-sm focus:border-purple-500 focus:outline-none"
        >
          <option value="all">全部发布状态</option>
          <option value="published">已发布</option>
          <option value="unpublished">未发布</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中...</div>
    <div v-else-if="filteredSkills.length === 0" class="py-20 text-center text-sm text-slate-400">
      没有符合当前筛选条件的 Skill
    </div>
    <div v-else class="grid auto-rows-fr grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <div
        v-for="skill in filteredSkills"
        :key="skill.id"
        class="group flex h-full min-h-[292px] cursor-pointer flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-all hover:-translate-y-0.5 hover:border-purple-300 hover:shadow-md"
        @click="openDetail(skill)"
      >
        <div class="shrink-0 p-4">
          <div class="mb-3 flex items-start justify-between">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-50 to-blue-50">
              <component
                :is="getIconComponent(skill.icon)"
                v-if="skill.icon && getIconComponent(skill.icon)"
                class="h-5 w-5 text-purple-600"
              />
              <Package v-else class="h-5 w-5 text-slate-400" />
            </div>
            <div class="flex flex-col items-end gap-1">
              <span v-if="skill.is_published" class="rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-600">
                已发布
              </span>
              <span v-if="skill.requires_approval" class="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-600">
                需审批
              </span>
            </div>
          </div>
          <h3 class="mb-1 truncate text-base font-semibold text-slate-900 group-hover:text-purple-700">
            {{ skill.name }}
          </h3>
          <p class="min-h-[32px] text-xs leading-4 text-slate-500 line-clamp-2" :title="skill.description">
            {{ skill.description || '无描述' }}
          </p>
          <div class="mt-3 flex min-h-[20px] flex-wrap gap-1">
            <span class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-600">{{ skill.category }}</span>
            <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">v{{ skill.version }}</span>
            <span v-for="tag in skill.tags.slice(0, 2)" :key="tag" class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
              {{ tag }}
            </span>
          </div>
        </div>

        <div v-if="skill.has_zip" class="mx-4 mb-3 flex h-[112px] shrink-0 flex-col justify-between rounded-xl border border-slate-100 bg-slate-50 p-3" @click.stop>
          <div class="flex items-center justify-between gap-2">
            <span class="text-[11px] font-medium text-slate-500">AI Policies</span>
            <span
              class="rounded-full px-2 py-0.5 text-[10px] font-medium ring-1"
              :class="securityBadgeClass(getSkillSecuritySummaryForSkill(skill))"
            >
              {{ getSkillSecuritySummaryForSkill(skill).label }}
            </span>
          </div>
          <template v-if="getSkillSecuritySummaryForSkill(skill).status === 'not_scanned'">
            <button
              class="w-full rounded-lg bg-purple-600 px-3 py-2 text-xs font-medium text-white hover:bg-purple-500"
              @click.stop="startSecurityAudit(skill)"
            >
              审查
            </button>
          </template>
          <template v-else-if="getSkillSecuritySummaryForSkill(skill).status === 'running' || getSkillSecuritySummaryForSkill(skill).status === 'queued'">
            <div class="flex items-center justify-between gap-2">
              <span class="line-clamp-1 text-[11px] text-slate-500">{{ getSkillSecuritySummaryForSkill(skill).shortAdvice }}</span>
              <button
                class="shrink-0 rounded-md bg-indigo-50 px-2 py-1 text-[11px] font-medium text-indigo-700 ring-1 ring-indigo-100"
                disabled
              >
                审查中
              </button>
            </div>
          </template>
          <template v-else>
            <div class="line-clamp-1 text-[11px] text-slate-500">{{ getSkillSecuritySummaryForSkill(skill).shortAdvice }}</div>
            <div class="grid grid-cols-2 gap-2">
              <button
                class="rounded-lg bg-white px-3 py-2 text-xs font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-100"
                @click.stop="startSecurityAudit(skill)"
              >
                重新审查
              </button>
              <button
                class="rounded-lg bg-purple-600 px-3 py-2 text-xs font-medium text-white hover:bg-purple-500"
                @click.stop="openAiPolicies(skill)"
              >
                <FileText class="mr-1 inline h-3 w-3" />
                查看报告
              </button>
            </div>
          </template>
        </div>

        <div class="mt-auto flex items-center justify-between border-t border-slate-100 bg-slate-50/60 px-4 py-3 text-xs text-slate-400">
          <span class="flex items-center gap-1">
            <Download class="h-3 w-3" />
            {{ skill.install_count }} 次下载
          </span>
          <button
            v-if="skill.has_zip && getSkillSecuritySummaryForSkill(skill).status !== 'not_scanned'"
            class="inline-flex items-center gap-1 text-purple-600 hover:text-purple-700"
            @click.stop="openAiPolicies(skill)"
          >
            <FileText class="h-3 w-3" />
            {{ getSkillSecuritySummaryForSkill(skill).status === 'running' || getSkillSecuritySummaryForSkill(skill).status === 'queued' ? '看进度' : '看报告' }}
          </button>
          <span v-else-if="skill.has_zip" class="text-green-600">已上传</span>
          <span v-else class="text-amber-600">未上传</span>
        </div>
      </div>
    </div>

    <div
      v-if="showCategoryForm"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
    >
      <div class="w-full max-w-sm rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">新建分类</h3>
        <div class="mb-3">
          <label class="mb-1 block text-sm font-medium text-slate-700">名称</label>
          <input
            v-model="categoryFormName"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            placeholder="如：legal / dev / office"
          />
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-slate-700">描述（可选）</label>
          <input
            v-model="categoryFormDescription"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div class="flex justify-end gap-3">
          <button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showCategoryForm = false">
            取消
          </button>
          <button class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700" @click="handleCreateCategory">
            创建
          </button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteCategoryTarget"
      title="删除分类"
      :message="`确认删除分类 ${deleteCategoryTarget?.name}？该分类下的 Skill 不会被删除，但需重新设置分类。`"
      @confirm="confirmDeleteCategory"
      @cancel="deleteCategoryTarget = null"
    />
  </div>
</template>
