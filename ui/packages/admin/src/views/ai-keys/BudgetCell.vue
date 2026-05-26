<script setup lang="ts">
import { computed } from 'vue'
import type { AiKey } from '@aihelms/shared'

interface Props {
  keyData: AiKey | null | undefined
}

const props = defineProps<Props>()

const budgetInfo = computed(() => {
  const k = props.keyData
  if (!k) return null

  const scope = k.budget_scope || 'unified'
  const used = Number(k.budget_used ?? 0) || 0

  if (scope === 'unified') {
    const limit = Number(k.budget_limit) || 0
    if (!limit) return null
    return { type: 'unified', label: '总预算', total: limit, used, items: [] }
  }

  if (scope === 'per_type') {
    const modelsTotal = Number(k.budget_models_total) || 0
    const mcpsTotal = Number(k.budget_mcps_total) || 0
    const total = modelsTotal + mcpsTotal
    if (!total) return null
    const items: { label: string; limit: number }[] = []
    if (modelsTotal) items.push({ label: '模型', limit: modelsTotal })
    if (mcpsTotal) items.push({ label: 'MCP', limit: mcpsTotal })
    return { type: 'per_type', label: '分类预算', total, used, items }
  }

  if (scope === 'per_resource') {
    const modelBudgets = k.model_budgets || {}
    const mcpBudgets = k.mcp_budgets || {}
    const total = Object.values(modelBudgets).reduce((s, v) => s + (Number(v) || 0), 0)
      + Object.values(mcpBudgets).reduce((s, v) => s + (Number(v) || 0), 0)
    if (!total) return null
    return { type: 'per_resource', label: '按资源预算', total, used, items: [] }
  }

  return null
})

const percent = computed(() => {
  if (!budgetInfo.value || !budgetInfo.value.total) return 0
  return Math.min(100, (budgetInfo.value.used / budgetInfo.value.total) * 100)
})

const periodLabel = computed(() => {
  const dur = props.keyData?.budget_duration
  if (!dur) return ''
  const m = String(dur).match(/^(\d+)d$/)
  if (!m) return dur
  const days = Number(m[1])
  if (days === 1) return '/天'
  if (days === 7) return '/7天'
  if (days === 30) return '/月'
  return `/${days}天`
})

const barColor = computed(() => {
  const p = percent.value
  if (p < 60) return 'bg-green-500'
  if (p < 85) return 'bg-amber-500'
  return 'bg-red-500'
})

const trackColor = computed(() => {
  const p = percent.value
  if (p < 60) return 'bg-green-50'
  if (p < 85) return 'bg-amber-50'
  return 'bg-red-50'
})
</script>

<template>
  <div v-if="!budgetInfo" class="text-xs text-slate-400">未设置</div>
  <div v-else class="min-w-[160px]">
    <div class="mb-1 flex items-center justify-between text-xs">
      <span class="text-slate-500">{{ budgetInfo.label }}</span>
      <span class="text-slate-600">¥{{ budgetInfo.used.toFixed(2) }} / ¥{{ budgetInfo.total.toFixed(2) }}{{ periodLabel }}</span>
    </div>
    <div class="h-1.5 w-full overflow-hidden rounded-full" :class="trackColor">
      <div
        class="h-full rounded-full transition-all"
        :class="barColor"
        :style="{ width: percent + '%' }"
      />
    </div>
    <div v-if="budgetInfo.items.length" class="mt-0.5 flex gap-2 text-xs text-slate-400">
      <span v-for="item in budgetInfo.items" :key="item.label">{{ item.label }} ¥{{ item.limit }}</span>
    </div>
  </div>
</template>
