<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Download } from 'lucide-vue-next'
import { getEfficiencyAnalysis, getEfficiencyRanking } from '@aihelms/shared'
import type { AnalysisItem, RankingItem } from '@aihelms/shared'

import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'
import HeatmapTable from './components/HeatmapTable.vue'
import CompositionDonut from './components/CompositionDonut.vue'
import PresetTabs from './components/PresetTabs.vue'
import BudgetProgress from './components/BudgetProgress.vue'
import { formatCost, formatCostShort, formatNumber, formatTokens, presetToRange } from './utils'

const DIMENSIONS = [
  { value: 'department', label: '部门' },
  { value: 'project', label: '项目' },
  { value: 'user', label: '用户' },
  { value: 'model', label: '模型' },
  { value: 'provider', label: '供应商' },
  { value: 'resource_type', label: '资源类型' },
  { value: 'key_type', label: 'Key 类型' },
] as const

const activeDim = ref<string>('department')
const activePreset = ref('month')
const costTypeFilter = ref<string>('')

const data = ref<AnalysisItem[]>([])
const heatmapRows = ref<string[]>([])
const heatmapCols = ref<string[]>([])
const heatmapValues = ref<number[][]>([])
const isLoading = ref(false)

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#a855f7', '#f43f5e']

async function loadData() {
  isLoading.value = true
  const range = presetToRange(activePreset.value)
  const params: Record<string, string> = { start_date: range.start, end_date: range.end }
  if (costTypeFilter.value) params.cost_type = costTypeFilter.value
  try {
    const res = await getEfficiencyAnalysis(activeDim.value, params)
    data.value = res
    if (activeDim.value === 'department') {
      await loadHeatmap(params)
    } else {
      heatmapRows.value = []
      heatmapCols.value = []
      heatmapValues.value = []
    }
  } finally {
    isLoading.value = false
  }
}

async function loadHeatmap(baseParams: Record<string, string>) {
  // 部门 × 模型热力图：取 Top 6 部门 × Top 6 模型
  const topDepts = data.value.slice(0, 6)
  const topModels = await getEfficiencyRanking({ ...baseParams, dimension: 'model', limit: 6 })
  heatmapRows.value = topDepts.map((d) => String(d.value || '未分配'))
  heatmapCols.value = topModels.map((m) => String(m.value))
  // 简化：用 ranking 数据作为近似（后端目前没有交叉聚合接口）
  // 真正的部门×模型矩阵 需要后端 cross 接口，这里做"按总占比分摊"近似
  const matrix: number[][] = []
  for (const dept of topDepts) {
    const row: number[] = []
    const totalDeptCost = dept.cost || 0
    const totalModelCost = topModels.reduce((s, m) => s + m.cost, 0) || 1
    for (const model of topModels) {
      // 按模型占总成本的比例分配该部门的成本
      row.push(Math.round((totalDeptCost * model.cost) / totalModelCost))
    }
    matrix.push(row)
  }
  heatmapValues.value = matrix
}

function switchDim(dim: string) {
  activeDim.value = dim
  loadData()
}

function changePreset(value: string) {
  activePreset.value = value
  loadData()
}

function changeCostType(value: string) {
  costTypeFilter.value = value
  loadData()
}

const totalCost = computed(() => data.value.reduce((s, d) => s + d.cost, 0))
const totalRequests = computed(() => data.value.reduce((s, d) => s + d.requests, 0))
const totalInputTokens = computed(() => data.value.reduce((s, d) => s + d.input_tokens, 0))
const totalOutputTokens = computed(() => data.value.reduce((s, d) => s + d.output_tokens, 0))
const avgCostPerRequest = computed(() =>
  totalRequests.value > 0 ? totalCost.value / totalRequests.value : 0,
)

function pctOfTotal(c: number): number {
  if (totalCost.value === 0) return 0
  return (c / totalCost.value) * 100
}

const donutData = computed(() => {
  const sorted = [...data.value].sort((a, b) => b.cost - a.cost).slice(0, 5)
  const rest = data.value.slice(5)
  const restCost = rest.reduce((s, d) => s + d.cost, 0)
  const arr = sorted.map((d, i) => ({
    name: String(d.value || '未分配'),
    value: d.cost,
    color: COLORS[i % COLORS.length],
  }))
  if (restCost > 0) arr.push({ name: `其他 ${rest.length} 项`, value: restCost, color: '#94a3b8' })
  return arr
})

onMounted(loadData)
</script>

<template>
  <div class="space-y-4">
    <!-- 维度切换 -->
    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-white/80 bg-white/60 px-4 py-2.5 shadow-sm backdrop-blur-xl">
      <span class="text-xs text-slate-500">分析维度</span>
      <div class="inline-flex flex-wrap gap-1 rounded-lg bg-slate-100/80 p-1">
        <button
          v-for="dim in DIMENSIONS"
          :key="dim.value"
          class="rounded-md px-3 py-1 text-xs transition-colors"
          :class="activeDim === dim.value
            ? 'bg-white font-medium text-slate-900 shadow-sm'
            : 'text-slate-500 hover:text-slate-700'"
          @click="switchDim(dim.value)"
        >
          {{ dim.label }}
        </button>
      </div>
    </div>

    <!-- 筛选条件 -->
    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-white/80 bg-white/60 px-4 py-2.5 shadow-sm backdrop-blur-xl">
      <span class="text-xs text-slate-500">时间</span>
      <PresetTabs :model-value="activePreset" @update:model-value="changePreset" />

      <span class="ml-3 text-xs text-slate-500">资源类型</span>
      <select
        :value="costTypeFilter"
        class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700"
        @change="changeCostType(($event.target as HTMLSelectElement).value)"
      >
        <option value="">全部</option>
        <option value="llm">LLM</option>
        <option value="mcp">MCP</option>
      </select>

      <div class="flex-1"></div>
      <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">
        <Download class="h-3.5 w-3.5" /> 导出 Excel
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-16">
      <div class="h-6 w-6 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else>
      <!-- KPI 摘要 -->
      <div class="grid grid-cols-5 gap-4">
        <KpiCard label="分析范围内成本" :value="formatCost(totalCost)" change-kind="neutral" change-text="基于聚合表" />
        <KpiCard label="维度数量" :value="data.length.toString()" unit="项" change-kind="neutral" change-text="筛选后" />
        <KpiCard label="总调用次数" :value="formatNumber(totalRequests)" change-kind="neutral" change-text="" />
        <KpiCard label="均次成本" :value="formatCost(avgCostPerRequest)" change-kind="neutral" change-text="" />
        <KpiCard
          label="总 Token 量"
          :value="formatTokens(totalInputTokens + totalOutputTokens)"
          change-kind="neutral"
          change-text=""
        />
      </div>

      <!-- 主分析表 -->
      <GlassCard
        title="维度明细"
        :subtitle="`共 ${data.length} 条记录 · 按成本降序`"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">维度值</th>
                <th class="py-2.5 text-right font-medium">总成本</th>
                <th class="py-2.5 text-right font-medium">外部成本</th>
                <th class="py-2.5 text-right font-medium">请求数</th>
                <th class="py-2.5 text-right font-medium">输入 Token</th>
                <th class="py-2.5 text-right font-medium">输出 Token</th>
                <th class="py-2.5 text-right font-medium">均次</th>
                <th class="py-2.5 pl-4 font-medium">占比</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(item, idx) in data"
                :key="idx"
                class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40"
              >
                <td class="py-3 font-medium text-slate-800">{{ item.value || '未分配' }}</td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(item.cost) }}</td>
                <td class="py-3 text-right text-slate-500">{{ formatCost(item.external_cost) }}</td>
                <td class="py-3 text-right text-slate-700">{{ formatNumber(item.requests) }}</td>
                <td class="py-3 text-right text-slate-500">{{ formatTokens(item.input_tokens) }}</td>
                <td class="py-3 text-right text-slate-500">{{ formatTokens(item.output_tokens) }}</td>
                <td class="py-3 text-right text-slate-500">
                  {{ item.requests > 0 ? formatCost(item.cost / item.requests) : '-' }}
                </td>
                <td class="py-3 pl-4 w-44">
                  <BudgetProgress :value="pctOfTotal(item.cost)" :show-label="true" />
                </td>
              </tr>
              <tr v-if="data.length === 0">
                <td colspan="8" class="py-12 text-center text-sm text-slate-400">该维度暂无数据</td>
              </tr>
            </tbody>
            <tfoot v-if="data.length > 0">
              <tr class="border-t border-slate-200 text-xs">
                <td class="py-2.5 font-medium text-slate-500">合计</td>
                <td class="py-2.5 text-right font-semibold text-slate-900">{{ formatCost(totalCost) }}</td>
                <td colspan="6"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </GlassCard>

      <!-- 热力图 + 占比环形 -->
      <div v-if="activeDim === 'department'" class="grid grid-cols-3 gap-4">
        <GlassCard class="col-span-2" title="部门 × 模型 交叉分析" subtitle="深色 = 该部门在该模型上花费高（基于占比近似分摊）">
          <HeatmapTable
            :row-labels="heatmapRows"
            :col-labels="heatmapCols"
            :values="heatmapValues"
            :formatter="formatCostShort"
          />
        </GlassCard>

        <GlassCard title="部门成本占比" subtitle="Top 5 + 其他">
          <CompositionDonut
            :data="donutData"
            :center-value="String(data.length)"
            :center-label="`个${DIMENSIONS.find((d) => d.value === activeDim)?.label}`"
            :formatter="formatCost"
          />
        </GlassCard>
      </div>

      <GlassCard v-else title="占比分布" subtitle="Top 5 + 其他">
        <div class="max-w-md">
          <CompositionDonut
            :data="donutData"
            :center-value="String(data.length)"
            :center-label="`个${DIMENSIONS.find((d) => d.value === activeDim)?.label}`"
            :formatter="formatCost"
          />
        </div>
      </GlassCard>
    </template>
  </div>
</template>
