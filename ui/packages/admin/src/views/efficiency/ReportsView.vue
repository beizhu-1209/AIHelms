<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { FileText, Plus, ClipboardCopy } from 'lucide-vue-next'
import { createEfficiencyReport, getEfficiencyReport, getEfficiencyReports } from '@aihelms/shared'
import type { EfficiencyReport, EfficiencySuggestion } from '@aihelms/shared'

import GlassCard from './components/GlassCard.vue'
import SuggestionCard from './components/SuggestionCard.vue'
import { formatCost, presetToRange } from './utils'

const PERIODS = [
  { key: 'all', label: '全部' },
  { key: 'daily', label: '日报' },
  { key: 'weekly', label: '周报' },
  { key: 'monthly', label: '月报' },
  { key: 'quarterly', label: '季报' },
] as const

type PeriodKey = (typeof PERIODS)[number]['key']

const activePeriod = ref<PeriodKey>('all')
const reports = ref<EfficiencyReport[]>([])
const total = ref(0)
const isLoadingList = ref(true)

const selectedId = ref<number | null>(null)
const detail = ref<EfficiencyReport | null>(null)
const isLoadingDetail = ref(false)

const showCreateModal = ref(false)
const createForm = ref({
  report_type: 'monthly',
  model_used: '',
  preset: 'month',
})

async function loadReports() {
  isLoadingList.value = true
  try {
    const res = await getEfficiencyReports({ page: 1, page_size: 50 })
    reports.value = res.items
    total.value = res.total
    if (reports.value.length > 0 && !selectedId.value) {
      selectedId.value = reports.value[0].id
      await loadDetail(reports.value[0].id)
    }
  } finally {
    isLoadingList.value = false
  }
}

async function loadDetail(id: number) {
  isLoadingDetail.value = true
  try {
    detail.value = await getEfficiencyReport(id)
    selectedId.value = id
  } finally {
    isLoadingDetail.value = false
  }
}

const filteredReports = computed(() => {
  if (activePeriod.value === 'all') return reports.value
  return reports.value.filter((r) => r.report_type === activePeriod.value)
})

const reportTypeLabel: Record<string, string> = {
  daily: '日报',
  weekly: '周报',
  monthly: '月报',
  quarterly: '季报',
  custom: '临时报告',
}

const reportTypeBadge: Record<string, string> = {
  daily: 'bg-sky-100 text-sky-700',
  weekly: 'bg-violet-100 text-violet-700',
  monthly: 'bg-indigo-100 text-indigo-700',
  quarterly: 'bg-emerald-100 text-emerald-700',
  custom: 'bg-slate-100 text-slate-700',
}

function shortDate(d?: string | null): string {
  if (!d) return '-'
  return d.slice(0, 10)
}

const groupedSuggestions = computed(() => {
  if (!detail.value?.suggestions) return { high: [], medium: [], low: [], opportunity: [] }
  const groups: Record<string, EfficiencySuggestion[]> = {
    high: [],
    medium: [],
    low: [],
    opportunity: [],
  }
  for (const s of detail.value.suggestions) {
    if (groups[s.priority]) groups[s.priority].push(s)
  }
  return groups
})

function copyMarkdown() {
  if (detail.value?.content_md) {
    navigator.clipboard.writeText(detail.value.content_md)
  }
}

const isCreating = ref(false)

async function createReport() {
  if (isCreating.value) return
  isCreating.value = true
  try {
    const range = presetToRange(createForm.value.preset)
    await createEfficiencyReport({
      report_type: createForm.value.report_type,
      period_start: range.start,
      period_end: range.end,
      filters: {},
    })
    showCreateModal.value = false
    await loadReports()
  } finally {
    isCreating.value = false
  }
}

watch(activePeriod, () => {
  // 切换周期时如果当前选中的不在筛选结果里，自动切换到列表首条
  const inList = filteredReports.value.find((r) => r.id === selectedId.value)
  if (!inList && filteredReports.value.length > 0) {
    loadDetail(filteredReports.value[0].id)
  }
})

onMounted(loadReports)
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-[300px_1fr] gap-4">
      <!-- 左侧：周期 + 列表 -->
      <div class="space-y-3">
        <div class="rounded-xl border border-white/80 bg-white/60 p-1 shadow-sm backdrop-blur-xl">
          <div class="flex gap-0.5">
            <button
              v-for="p in PERIODS"
              :key="p.key"
              class="flex-1 rounded-md px-2 py-1.5 text-xs transition-colors"
              :class="activePeriod === p.key
                ? 'bg-indigo-50 font-medium text-indigo-700'
                : 'text-slate-500 hover:bg-slate-50'"
              @click="activePeriod = p.key"
            >
              {{ p.label }}
            </button>
          </div>
        </div>

        <GlassCard padding="p-0">
          <div class="border-b border-slate-100 px-4 py-3 text-xs text-slate-500">
            历史报告（{{ filteredReports.length }} 期）
          </div>
          <div v-if="isLoadingList" class="flex justify-center py-12">
            <div class="h-6 w-6 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
          </div>
          <div v-else-if="filteredReports.length === 0" class="py-12 text-center text-xs text-slate-400">
            暂无报告
          </div>
          <div v-else class="max-h-[600px] overflow-y-auto">
            <button
              v-for="r in filteredReports"
              :key="r.id"
              class="block w-full border-b border-slate-50 px-4 py-3 text-left transition-colors hover:bg-indigo-50/40 last:border-0"
              :class="selectedId === r.id ? 'border-l-2 border-l-indigo-500 bg-indigo-50/60' : ''"
              @click="loadDetail(r.id)"
            >
              <div class="flex items-start justify-between gap-2">
                <strong class="text-sm text-slate-800">{{ shortDate(r.period_start) }} ~ {{ shortDate(r.period_end) }}</strong>
                <span class="rounded px-1.5 py-0.5 text-[10px]" :class="reportTypeBadge[r.report_type]">
                  {{ reportTypeLabel[r.report_type] || r.report_type }}
                </span>
              </div>
              <p class="mt-1 truncate text-xs text-slate-500">{{ r.summary || '生成中...' }}</p>
              <p class="mt-0.5 text-xs text-slate-400">
                {{ r.model_used || '--' }} · {{ shortDate(r.created_at) }}
              </p>
            </button>
          </div>
        </GlassCard>

        <button
          class="flex w-full items-center justify-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50/40 px-4 py-3 text-sm text-indigo-700 transition-colors hover:bg-indigo-100/60"
          @click="showCreateModal = true"
        >
          <Plus class="h-4 w-4" /> 生成新报告
        </button>
      </div>

      <!-- 右侧：报告详情 -->
      <div class="space-y-3">
        <div v-if="!detail" class="flex h-96 items-center justify-center rounded-xl border border-white/80 bg-white/60 shadow-sm backdrop-blur-xl">
          <div class="text-center">
            <FileText class="mx-auto h-10 w-10 text-slate-300" />
            <p class="mt-2 text-sm text-slate-500">从左侧选择一份报告查看详情</p>
          </div>
        </div>

        <template v-else>
          <!-- 报告头部 -->
          <GlassCard>
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="text-xl font-semibold text-slate-900">
                  {{ shortDate(detail.period_start) }} ~ {{ shortDate(detail.period_end) }}
                  {{ reportTypeLabel[detail.report_type] || detail.report_type }}
                </div>
                <p class="mt-1 text-xs text-slate-500">
                  生成时间：{{ shortDate(detail.created_at) }} · 使用模型：{{ detail.model_used || '--' }}
                  <span v-if="detail.generation_cost">· 生成成本 {{ formatCost(detail.generation_cost) }}</span>
                </p>
              </div>
              <div class="flex gap-2">
                <button
                  class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50"
                  @click="copyMarkdown"
                >
                  <ClipboardCopy class="h-3.5 w-3.5" /> 复制 Markdown
                </button>
                <button class="rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">
                  导出 PDF
                </button>
              </div>
            </div>
          </GlassCard>

          <!-- 执行摘要 -->
          <GlassCard title="执行摘要" subtitle="30 秒读完核心结论">
            <div
              v-if="detail.summary && detail.summary !== '报告生成中...'"
              class="rounded-lg bg-gradient-to-br from-indigo-50/70 to-violet-50/40 p-4 text-sm leading-relaxed text-slate-700"
            >
              {{ detail.summary }}
            </div>
            <div v-else class="rounded-lg bg-amber-50/50 p-4 text-sm text-amber-700">
              报告生成中... 请稍后刷新查看
            </div>
          </GlassCard>

          <!-- 关键发现与建议 -->
          <GlassCard title="关键发现与建议" :subtitle="`共 ${detail.suggestions?.length ?? 0} 条`">
            <div v-if="!detail.suggestions || detail.suggestions.length === 0" class="py-6 text-center text-sm text-slate-400">
              本报告暂无建议
            </div>
            <div v-else class="space-y-3">
              <div v-for="key in ['high', 'medium', 'low', 'opportunity']" :key="key">
                <SuggestionCard
                  v-for="s in groupedSuggestions[key]"
                  :key="s.id"
                  :suggestion="s"
                  class="mb-2"
                />
              </div>
            </div>
          </GlassCard>

          <!-- 详细分析（Markdown） -->
          <GlassCard v-if="detail.content_md" title="详细分析" subtitle="数据 + AI 解读">
            <div class="prose prose-sm max-w-none whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
              {{ detail.content_md }}
            </div>
          </GlassCard>
        </template>
      </div>
    </div>

    <!-- 创建报告弹窗 -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-xl border border-white/80 bg-white p-6 shadow-2xl">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-base font-semibold text-slate-900">生成新报告</h3>
          <button class="text-slate-400 hover:text-slate-600" @click="showCreateModal = false">×</button>
        </div>
        <div class="space-y-3">
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-600">报告类型</label>
            <select v-model="createForm.report_type" class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm">
              <option value="daily">日报</option>
              <option value="weekly">周报</option>
              <option value="monthly">月报</option>
              <option value="quarterly">季报</option>
              <option value="custom">临时报告</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-600">时间范围</label>
            <select v-model="createForm.preset" class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm">
              <option value="month">本月</option>
              <option value="last_month">上月</option>
              <option value="7d">近 7 天</option>
              <option value="30d">近 30 天</option>
              <option value="90d">近 90 天</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-600">生成模型（可选）</label>
            <input
              v-model="createForm.model_used"
              type="text"
              placeholder="如 claude-3-5-sonnet（留空使用默认）"
              class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button
            class="rounded-md border border-slate-200 bg-white px-4 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            @click="showCreateModal = false"
          >
            取消
          </button>
          <button
            class="rounded-md bg-indigo-600 px-4 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
            :disabled="isCreating"
            @click="createReport"
          >
            {{ isCreating ? '生成中...' : '生成' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
