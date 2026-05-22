<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Download } from 'lucide-vue-next'
import { getEfficiencyAnalysis, getEfficiencyRanking } from '@aihelms/shared'
import type { AnalysisItem, RankingItem } from '@aihelms/shared'

import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'
import ParetoChart from './components/ParetoChart.vue'
import PresetTabs from './components/PresetTabs.vue'
import { formatCost, formatCostShort, formatNumber, presetToRange } from './utils'

const TABS = [
  { key: 'preference', label: '部门 × 模型偏好' },
  { key: 'concentration', label: '集中度（80/20）' },
  { key: 'comparison', label: '部门内模型对比' },
] as const

type TabKey = (typeof TABS)[number]['key']

const activeTab = ref<TabKey>('preference')
const activePreset = ref('month')
const sortBy = ref<'cost' | 'requests' | 'pct'>('cost')

const modelData = ref<AnalysisItem[]>([])
const deptData = ref<AnalysisItem[]>([])
const rankingData = ref<RankingItem[]>([])
const isLoading = ref(true)

interface DeptModelRow {
  department: string
  totalCost: number
  totalRequests: number
  /** 各模型在该部门的成本（按比例近似） */
  modelCost: Record<string, number>
}

const deptModelMatrix = ref<DeptModelRow[]>([])

async function loadData() {
  isLoading.value = true
  const range = presetToRange(activePreset.value)
  const params = { start_date: range.start, end_date: range.end }
  try {
    const [modelRes, deptRes, rankRes] = await Promise.all([
      getEfficiencyAnalysis('model', params),
      getEfficiencyAnalysis('department', params),
      getEfficiencyRanking({ ...params, dimension: 'model', limit: 30 }),
    ])
    modelData.value = modelRes
    deptData.value = deptRes
    rankingData.value = rankRes
    buildMatrix()
  } finally {
    isLoading.value = false
  }
}

function buildMatrix() {
  // 用 Top 6 模型 + 全部部门，按比例近似分摊
  const topModels = [...modelData.value].sort((a, b) => b.cost - a.cost).slice(0, 6)
  const totalModelCost = topModels.reduce((s, m) => s + m.cost, 0) || 1
  deptModelMatrix.value = deptData.value.map((dept) => {
    const modelCost: Record<string, number> = {}
    for (const m of topModels) {
      modelCost[String(m.value)] = Math.round((dept.cost * m.cost) / totalModelCost)
    }
    return {
      department: String(dept.value || '未分配'),
      totalCost: dept.cost,
      totalRequests: dept.requests,
      modelCost,
    }
  })
}

function changePreset(value: string) {
  activePreset.value = value
  loadData()
}

const topModels = computed(() => [...modelData.value].sort((a, b) => b.cost - a.cost).slice(0, 6))

const totalCost = computed(() => modelData.value.reduce((s, m) => s + m.cost, 0))

// KPI
const kpiActiveModels = computed(() => modelData.value.length)
const kpiMainModels = computed(() => {
  if (totalCost.value === 0) return 0
  const sorted = [...modelData.value].sort((a, b) => b.cost - a.cost)
  let cum = 0
  let count = 0
  for (const m of sorted) {
    cum += m.cost
    count++
    if (cum / totalCost.value >= 0.8) break
  }
  return count
})
const kpiLongTail = computed(() => Math.max(0, kpiActiveModels.value - kpiMainModels.value))
const kpiOptimizable = computed(() => {
  // 启发式：长尾模型成本之和 × 0.3 作为可优化金额
  const sorted = [...modelData.value].sort((a, b) => b.cost - a.cost)
  const longTail = sorted.slice(kpiMainModels.value)
  return longTail.reduce((s, m) => s + m.cost, 0) * 0.3
})

// 帕累托数据
const paretoData = computed(() =>
  rankingData.value.map((r) => ({
    label: String(r.value),
    value: r.cost,
  })),
)

function pctOf(cost: number, total: number): number {
  if (total === 0) return 0
  return (cost / total) * 100
}

function pctClass(p: number): string {
  if (p >= 50) return 'bg-indigo-200/70 font-semibold text-indigo-900'
  if (p >= 25) return 'bg-indigo-100 text-indigo-800'
  if (p >= 10) return 'bg-slate-100 text-slate-700'
  return 'text-slate-400'
}

// 偏好画像（基于该部门最大占比模型类型推导）
function profileBadge(row: DeptModelRow): { label: string; class: string } {
  if (row.totalCost === 0) return { label: '无数据', class: 'bg-slate-100 text-slate-500' }
  const max = Object.entries(row.modelCost).sort((a, b) => b[1] - a[1])[0]
  if (!max) return { label: '混合', class: 'bg-slate-100 text-slate-600' }
  const name = max[0].toLowerCase()
  if (name.includes('claude') || name.includes('coder')) return { label: '代码偏好', class: 'bg-indigo-100 text-indigo-700' }
  if (name.includes('gpt-4') || name.includes('gpt4')) return { label: '通用对话', class: 'bg-violet-100 text-violet-700' }
  if (name.includes('qwen') || name.includes('文心') || name.includes('豆包')) return { label: '中文文案', class: 'bg-amber-100 text-amber-700' }
  if (name.includes('deepseek')) return { label: '高性价比', class: 'bg-emerald-100 text-emerald-700' }
  if (name.includes('embedding') || name.includes('rerank')) return { label: '检索增强', class: 'bg-pink-100 text-pink-700' }
  return { label: '通用模型', class: 'bg-slate-100 text-slate-600' }
}

const sortedDeptMatrix = computed(() => {
  const arr = [...deptModelMatrix.value]
  if (sortBy.value === 'requests') arr.sort((a, b) => b.totalRequests - a.totalRequests)
  else arr.sort((a, b) => b.totalCost - a.totalCost)
  return arr
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
        <Download class="h-3.5 w-3.5" /> 导出
      </button>
    </div>

    <!-- KPI -->
    <div class="grid grid-cols-4 gap-4">
      <KpiCard
        label="在用模型数"
        :value="kpiActiveModels.toString()"
        unit="个"
        change-kind="neutral"
        :change-text="kpiActiveModels >= 10 ? '分散度偏高' : '集中度健康'"
      />
      <KpiCard
        label="主力模型"
        :value="kpiMainModels.toString()"
        unit="个"
        change-kind="neutral"
        :change-text="`占 80% 调用成本`"
      />
      <KpiCard
        label="长尾模型"
        :value="kpiLongTail.toString()"
        unit="个"
        change-kind="neutral"
        change-text="月成本占比低 · 可评估"
      />
      <KpiCard
        label="可优化金额"
        :value="formatCost(kpiOptimizable)"
        change-kind="up-good"
        :change-text="totalCost > 0 ? `约 ${((kpiOptimizable / totalCost) * 100).toFixed(1)}% 节省空间` : '基于启发式估算'"
        value-color="text-emerald-600"
        :sparkline="[]"
      />
    </div>

    <!-- Tab 切换 -->
    <div class="flex gap-1 rounded-xl border border-white/80 bg-white/60 p-1 shadow-sm backdrop-blur-xl">
      <button
        v-for="t in TABS"
        :key="t.key"
        class="rounded-md px-3 py-1.5 text-sm transition-colors"
        :class="activeTab === t.key
          ? 'bg-indigo-50 font-medium text-indigo-700'
          : 'text-slate-600 hover:bg-slate-100'"
        @click="activeTab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-16">
      <div class="h-6 w-6 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else>
      <!-- Tab 1: 部门偏好矩阵 -->
      <GlassCard
        v-if="activeTab === 'preference'"
        title="部门模型偏好矩阵"
        subtitle="行总和 ≈ 100% · 显示每个部门 Top 模型使用结构（按比例近似分摊）"
      >
        <template #action>
          <select v-model="sortBy" class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700">
            <option value="cost">按成本</option>
            <option value="requests">按调用量</option>
          </select>
        </template>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">部门</th>
                <th class="py-2.5 font-medium">画像</th>
                <th
                  v-for="m in topModels"
                  :key="String(m.value)"
                  class="py-2.5 text-right font-medium"
                >
                  {{ m.value }}
                </th>
                <th class="py-2.5 text-right font-medium">总成本</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in sortedDeptMatrix"
                :key="row.department"
                class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40"
              >
                <td class="py-3 font-medium text-slate-800">{{ row.department }}</td>
                <td class="py-3">
                  <span class="rounded px-2 py-0.5 text-xs" :class="profileBadge(row).class">
                    {{ profileBadge(row).label }}
                  </span>
                </td>
                <td
                  v-for="m in topModels"
                  :key="String(m.value)"
                  class="py-3 text-right rounded text-xs"
                  :class="pctClass(pctOf(row.modelCost[String(m.value)] || 0, row.totalCost))"
                >
                  <div>{{ pctOf(row.modelCost[String(m.value)] || 0, row.totalCost).toFixed(0) }}%</div>
                  <div class="text-[10px] opacity-70">{{ formatCostShort(row.modelCost[String(m.value)] || 0) }}</div>
                </td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.totalCost) }}</td>
              </tr>
              <tr v-if="sortedDeptMatrix.length === 0">
                <td :colspan="topModels.length + 3" class="py-12 text-center text-sm text-slate-400">
                  暂无部门数据
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassCard>

      <!-- Tab 2: 集中度 -->
      <div v-if="activeTab === 'concentration'" class="grid grid-cols-3 gap-4">
        <GlassCard class="col-span-2" title="模型集中度" subtitle="80/20 帕累托分析 · 柱：成本 · 折线：累计占比">
          <ParetoChart :data="paretoData" :threshold="80" :height="300" />
        </GlassCard>

        <GlassCard title="模型分类汇总">
          <div class="space-y-2">
            <div class="flex items-center justify-between rounded-md bg-emerald-50/60 px-3 py-2.5 text-xs">
              <span class="text-emerald-700">主力模型（贡献 80% 成本）</span>
              <strong class="text-slate-900">{{ kpiMainModels }} 个</strong>
            </div>
            <div class="flex items-center justify-between rounded-md bg-amber-50/60 px-3 py-2.5 text-xs">
              <span class="text-amber-700">中间层模型</span>
              <strong class="text-slate-900">{{ Math.max(0, Math.min(kpiLongTail, 4)) }} 个</strong>
            </div>
            <div class="flex items-center justify-between rounded-md bg-red-50/60 px-3 py-2.5 text-xs">
              <span class="text-red-700">长尾模型（建议下线）</span>
              <strong class="text-slate-900">{{ Math.max(0, kpiLongTail - 4) }} 个</strong>
            </div>
          </div>
          <div class="mt-4 text-xs text-slate-500 leading-relaxed">
            主力模型支撑大部分业务，长尾模型需评估保留必要性。点击具体模型可查看
            <router-link to="/efficiency/analysis" class="text-indigo-600 hover:underline">明细分析</router-link>。
          </div>
        </GlassCard>
      </div>

      <!-- Tab 3: 部门内对比 -->
      <GlassCard
        v-if="activeTab === 'comparison'"
        title="部门内模型对比"
        subtitle="同部门下不同模型的均次成本对比 · 用于找替换空间"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                <th class="py-2.5 font-medium">部门</th>
                <th class="py-2.5 font-medium">主用模型</th>
                <th class="py-2.5 text-right font-medium">本期成本</th>
                <th class="py-2.5 text-right font-medium">调用次数</th>
                <th class="py-2.5 text-right font-medium">均次成本</th>
                <th class="py-2.5 font-medium">建议</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in sortedDeptMatrix"
                :key="row.department"
                class="border-b border-slate-50 last:border-0"
              >
                <td class="py-3 font-medium text-slate-800">{{ row.department }}</td>
                <td class="py-3 text-slate-700">
                  {{ Object.entries(row.modelCost).sort((a, b) => b[1] - a[1])[0]?.[0] || '-' }}
                </td>
                <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.totalCost) }}</td>
                <td class="py-3 text-right text-slate-500">{{ formatNumber(row.totalRequests) }}</td>
                <td class="py-3 text-right text-slate-700">
                  {{ row.totalRequests > 0 ? formatCost(row.totalCost / row.totalRequests) : '-' }}
                </td>
                <td class="py-3 text-xs text-slate-500">
                  {{ row.totalCost > 0 && row.totalRequests > 0 && row.totalCost / row.totalRequests > 0.5 ? '可评估替换' : '保持' }}
                </td>
              </tr>
              <tr v-if="sortedDeptMatrix.length === 0">
                <td colspan="6" class="py-12 text-center text-sm text-slate-400">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassCard>
    </template>
  </div>
</template>
