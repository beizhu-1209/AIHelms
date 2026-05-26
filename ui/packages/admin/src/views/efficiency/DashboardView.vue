<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Sparkles, Download } from 'lucide-vue-next'
import {
  getEfficiencyComposition,
  getEfficiencyOverview,
  getEfficiencyRanking,
  getEfficiencyTrend,
  getKeyTypeComparison,
} from '@aihelms/shared'
import type {
  CompositionItem,
  EfficiencyKpi,
  KeyTypeItem,
  RankingItem,
  TrendItem,
} from '@aihelms/shared'

import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'
import TrendChart, { type TrendSeries } from './components/TrendChart.vue'
import CompositionDonut from './components/CompositionDonut.vue'
import PresetTabs from './components/PresetTabs.vue'
import { formatCost, formatCostShort, formatNumber, presetToRange } from './utils'

const kpi = ref<EfficiencyKpi | null>(null)
const trend = ref<TrendItem[]>([])
const composition = ref<CompositionItem[]>([])
const keyTypes = ref<KeyTypeItem[]>([])
const deptRanking = ref<RankingItem[]>([])
const modelRanking = ref<RankingItem[]>([])
const userRanking = ref<RankingItem[]>([])
const isLoading = ref(true)

const activePreset = ref('month')
const trendGranularity = ref<'day' | 'week' | 'month'>('day')

const COST_TYPE_META: Record<string, { name: string; color: string }> = {
  llm: { name: 'LLM 调用', color: '#6366f1' },
  mcp: { name: 'MCP 调用', color: '#ec4899' },
  skill: { name: 'Skill 使用', color: '#f59e0b' },
  agent: { name: '智能体运行', color: '#10b981' },
}

function metaOf(type: string) {
  return COST_TYPE_META[type] || { name: type, color: '#94a3b8' }
}

async function loadData() {
  isLoading.value = true
  const range = presetToRange(activePreset.value)
  const params = { start_date: range.start, end_date: range.end }
  try {
    const [a, b, c, d, e, f, g] = await Promise.all([
      getEfficiencyOverview(params),
      getEfficiencyTrend({ ...params, group_by: trendGranularity.value }),
      getEfficiencyComposition(params),
      getKeyTypeComparison(params),
      getEfficiencyRanking({ ...params, dimension: 'department', limit: 5 }),
      getEfficiencyRanking({ ...params, dimension: 'model', limit: 5 }),
      getEfficiencyRanking({ ...params, dimension: 'user', limit: 5 }),
    ])
    kpi.value = a
    trend.value = b
    composition.value = c
    keyTypes.value = d
    deptRanking.value = e
    modelRanking.value = f
    userRanking.value = g
  } finally {
    isLoading.value = false
  }
}

function changePreset(value: string) {
  activePreset.value = value
  loadData()
}

function changeGranularity(g: 'day' | 'week' | 'month') {
  trendGranularity.value = g
  loadData()
}

const trendSeries = computed<TrendSeries[]>(() => {
  if (trend.value.length === 0) return []
  const periods = Array.from(new Set(trend.value.map((t) => t.period))).sort()
  const types = Array.from(new Set(trend.value.map((t) => t.cost_type)))
  const seriesArr: TrendSeries[] = []
  // 总成本
  const totalByPeriod: Record<string, number> = {}
  for (const t of trend.value) {
    totalByPeriod[t.period] = (totalByPeriod[t.period] || 0) + t.cost
  }
  seriesArr.push({
    name: '总成本',
    color: '#1e293b',
    values: periods.map((p) => Math.round((totalByPeriod[p] || 0) * 100) / 100),
  })
  for (const type of types) {
    const m = metaOf(type)
    const byPeriod: Record<string, number> = {}
    for (const t of trend.value) {
      if (t.cost_type === type) byPeriod[t.period] = t.cost
    }
    seriesArr.push({
      name: m.name,
      color: m.color,
      values: periods.map((p) => Math.round((byPeriod[p] || 0) * 100) / 100),
    })
  }
  return seriesArr
})

const trendLabels = computed(() => {
  const periods = Array.from(new Set(trend.value.map((t) => t.period))).sort()
  return periods.map((p) => {
    const d = new Date(p)
    if (trendGranularity.value === 'month') return `${d.getMonth() + 1}月`
    return `${d.getMonth() + 1}/${d.getDate()}`
  })
})

const compositionData = computed(() => {
  if (composition.value.length === 0) return []
  return composition.value
    .map((c) => ({ name: metaOf(c.cost_type).name, value: c.cost, color: metaOf(c.cost_type).color }))
    .sort((a, b) => b.value - a.value)
})

const totalCostFormatted = computed(() => formatCostShort(kpi.value?.total_cost ?? 0))

const keyTypeMain = computed(() => keyTypes.value.find((k) => k.key_type === 'personal_main'))
const keyTypeScene = computed(() =>
  keyTypes.value.find((k) => k.key_type === 'personal_scene' || k.key_type === 'scene'),
)
const keyTotalCost = computed(() => keyTypes.value.reduce((s, k) => s + k.cost, 0))

function keyTypePct(item: KeyTypeItem | undefined): string {
  if (!item || keyTotalCost.value === 0) return '0%'
  return `${((item.cost / keyTotalCost.value) * 100).toFixed(0)}%`
}

// 简化的 KPI sparkline：拿当期成本趋势作为示意
const kpiSparkline = computed(() => {
  if (trend.value.length === 0) return []
  const byPeriod: Record<string, number> = {}
  for (const t of trend.value) {
    byPeriod[t.period] = (byPeriod[t.period] || 0) + t.cost
  }
  return Object.keys(byPeriod).sort().map((p) => byPeriod[p])
})

onMounted(loadData)
</script>

<template>
  <div class="space-y-4">
    <!-- 工具栏 -->
    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-white/80 bg-white/60 px-4 py-2.5 shadow-sm backdrop-blur-xl">
      <span class="text-xs text-slate-500">时间范围</span>
      <PresetTabs :model-value="activePreset" @update:model-value="changePreset" />
      <div class="flex-1"></div>
      <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">
        <Download class="h-3.5 w-3.5" /> 导出报告
      </button>
      <button class="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-3 py-1 text-xs text-white hover:bg-indigo-700">
        <Sparkles class="h-3.5 w-3.5" /> 生成 AI 分析
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else>
      <!-- KPI 卡片 -->
      <div class="grid grid-cols-4 gap-4">
        <KpiCard
          label="本月 AI 总投入"
          :value="formatCost(kpi?.total_cost ?? 0)"
          :change="kpi?.cost_change ?? null"
          change-kind="up-bad"
          :sparkline="kpiSparkline"
          spark-color="#6366f1"
        />
        <KpiCard
          label="总调用次数"
          :value="formatNumber(kpi?.total_requests ?? 0)"
          :change="kpi?.requests_change ?? null"
          change-kind="up-good"
          :sparkline="kpiSparkline"
          spark-color="#10b981"
        />
        <KpiCard
          label="活跃 AI 用户"
          :value="(kpi?.active_users ?? 0).toString()"
          unit="人"
          change-kind="neutral"
          change-text="数据 T+5min"
          spark-color="#8b5cf6"
        />
        <KpiCard
          label="人均 AI 成本"
          :value="formatCost(kpi?.avg_cost_per_user ?? 0)"
          unit="/人"
          change-kind="neutral"
          change-text="基于活跃用户"
          spark-color="#10b981"
        />
      </div>

      <!-- 趋势 + 资源构成 -->
      <div class="grid grid-cols-3 gap-4">
        <GlassCard class="col-span-2" title="AI 成本趋势" subtitle="按资源类型分线 · 悬停查看明细">
          <template #action>
            <div class="inline-flex rounded-md bg-slate-100 p-0.5">
              <button
                v-for="g in [{ k: 'day', l: '日' }, { k: 'week', l: '周' }, { k: 'month', l: '月' }]"
                :key="g.k"
                class="rounded px-2.5 py-0.5 text-xs"
                :class="trendGranularity === g.k ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'"
                @click="changeGranularity(g.k as 'day' | 'week' | 'month')"
              >
                {{ g.l }}
              </button>
            </div>
          </template>
          <TrendChart
            :labels="trendLabels"
            :series="trendSeries"
            :height="240"
            :y-formatter="formatCostShort"
          />
        </GlassCard>

        <GlassCard title="资源类型构成" subtitle="本月各类资源成本占比">
          <CompositionDonut
            :data="compositionData"
            :center-value="totalCostFormatted"
            center-label="总投入"
            :formatter="formatCost"
          />
        </GlassCard>
      </div>

      <!-- 主 Key vs 场景 Key + 智能体价值速览 -->
      <div class="grid grid-cols-2 gap-4">
        <GlassCard title="主 Key vs 场景 Key" subtitle="人使用 AI 的成本 vs AI 自动运行的成本">
          <div class="grid grid-cols-2 gap-3">
            <div class="rounded-lg bg-indigo-50/70 p-4">
              <div class="text-xs text-slate-500">主 Key（人 + AI 协作）</div>
              <div class="mt-1 text-xl font-semibold text-slate-900">
                {{ formatCost(keyTypeMain?.cost ?? 0) }}
              </div>
              <div class="mt-1 text-xs text-slate-400">
                {{ keyTypePct(keyTypeMain) }} · {{ (keyTypeMain?.requests ?? 0).toLocaleString() }} 次调用
              </div>
            </div>
            <div class="rounded-lg bg-violet-50/70 p-4">
              <div class="text-xs text-slate-500">场景 Key（AI 自动化）</div>
              <div class="mt-1 text-xl font-semibold text-slate-900">
                {{ formatCost(keyTypeScene?.cost ?? 0) }}
              </div>
              <div class="mt-1 text-xs text-slate-400">
                {{ keyTypePct(keyTypeScene) }} · {{ (keyTypeScene?.requests ?? 0).toLocaleString() }} 次调用
              </div>
            </div>
          </div>
          <div class="mt-4 rounded-md border-l-4 border-indigo-400 bg-indigo-50/50 px-4 py-2.5 text-xs leading-relaxed text-slate-600">
            <strong class="text-slate-800">提示：</strong>
            主 Key 反映员工的 AI 使用情况，场景 Key 反映企业 AI 自动化程度。两者比例可看出 AI 在组织中的渗透深度。
          </div>
        </GlassCard>

        <GlassCard title="智能体使用速览" subtitle="本月场景 Key 调用排行（参考多维分析）">
          <div v-if="userRanking.length === 0" class="py-8 text-center text-sm text-slate-400">
            暂无场景 Key 数据
          </div>
          <div v-else class="grid grid-cols-2 gap-3">
            <div class="rounded-lg bg-emerald-50/60 p-3">
              <div class="text-xs text-emerald-700">活跃场景 Key</div>
              <div class="mt-1 text-lg font-semibold text-slate-900">{{ keyTypeScene?.requests ? '运行中' : '暂无' }}</div>
              <div class="mt-0.5 text-xs text-slate-400">基于本期调用统计</div>
            </div>
            <div class="rounded-lg bg-amber-50/60 p-3">
              <div class="text-xs text-amber-700">主 Key 调用</div>
              <div class="mt-1 text-lg font-semibold text-slate-900">
                {{ formatNumber(keyTypeMain?.requests ?? 0) }}
              </div>
              <div class="mt-0.5 text-xs text-slate-400">人 + AI 协作调用</div>
            </div>
          </div>
          <p class="mt-4 text-xs text-slate-500">
            详细的调用次数 / 活跃天数 / 使用人数分析请进入
            <router-link to="/efficiency/agents" class="text-indigo-600 hover:underline">智能体经营 →</router-link>
          </p>
        </GlassCard>
      </div>

      <!-- 三个排行榜 -->
      <div class="grid grid-cols-3 gap-4">
        <GlassCard title="部门成本 Top 5">
          <template #action>
            <router-link to="/efficiency/analysis" class="text-xs text-indigo-600 hover:underline">查看全部 →</router-link>
          </template>
          <table v-if="deptRanking.length > 0" class="mt-1 w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-slate-400">
                <th class="py-2 text-left font-medium">部门</th>
                <th class="py-2 text-right font-medium">成本</th>
                <th class="py-2 text-right font-medium">请求</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in deptRanking" :key="i" class="border-b border-slate-50 last:border-0">
                <td class="py-2.5 font-medium text-slate-700">{{ r.value || '未分配' }}</td>
                <td class="py-2.5 text-right font-semibold text-slate-900">{{ formatCost(r.cost) }}</td>
                <td class="py-2.5 text-right text-slate-500">{{ r.requests.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="py-6 text-center text-xs text-slate-400">暂无数据</div>
        </GlassCard>

        <GlassCard title="模型成本 Top 5">
          <template #action>
            <router-link to="/efficiency/models" class="text-xs text-indigo-600 hover:underline">查看全部 →</router-link>
          </template>
          <table v-if="modelRanking.length > 0" class="mt-1 w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-slate-400">
                <th class="py-2 text-left font-medium">模型</th>
                <th class="py-2 text-right font-medium">成本</th>
                <th class="py-2 text-right font-medium">调用</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in modelRanking" :key="i" class="border-b border-slate-50 last:border-0">
                <td class="py-2.5 truncate max-w-[160px] font-medium text-slate-700" :title="String(r.value)">{{ r.value }}</td>
                <td class="py-2.5 text-right font-semibold text-slate-900">{{ formatCost(r.cost) }}</td>
                <td class="py-2.5 text-right text-slate-500">{{ formatNumber(r.requests) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="py-6 text-center text-xs text-slate-400">暂无数据</div>
        </GlassCard>

        <GlassCard title="用户消耗 Top 5">
          <template #action>
            <router-link to="/efficiency/analysis" class="text-xs text-indigo-600 hover:underline">查看全部 →</router-link>
          </template>
          <table v-if="userRanking.length > 0" class="mt-1 w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-slate-400">
                <th class="py-2 text-left font-medium">用户</th>
                <th class="py-2 text-right font-medium">成本</th>
                <th class="py-2 text-right font-medium">调用</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in userRanking" :key="i" class="border-b border-slate-50 last:border-0">
                <td class="py-2.5 font-medium text-slate-700">{{ r.value || '匿名' }}</td>
                <td class="py-2.5 text-right font-semibold text-slate-900">{{ formatCost(r.cost) }}</td>
                <td class="py-2.5 text-right text-slate-500">{{ formatNumber(r.requests) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="py-6 text-center text-xs text-slate-400">暂无数据</div>
        </GlassCard>
      </div>
    </template>
  </div>
</template>
