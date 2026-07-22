<script setup lang="ts">
import GlassCard from './GlassCard.vue'
import { formatBigToken, formatCost, formatNumber } from '../utils'
import type { UserTop10Row } from '../costTypes'

type Metric = 'cost' | 'tokens' | 'requests'

const props = defineProps<{
  metric: Metric
  rows: UserTop10Row[]
  loading: boolean
}>()

const emit = defineEmits<{
  metricChange: [metric: Metric]
}>()

const tabs: { key: Metric; label: string }[] = [
  { key: 'cost', label: '成本' },
  { key: 'tokens', label: 'Token' },
  { key: 'requests', label: '调用次数' },
]

function metricLabel(): string {
  if (props.metric === 'tokens') return 'Token'
  if (props.metric === 'requests') return '调用次数'
  return '成本(元)'
}

function metricValue(row: UserTop10Row): string {
  if (props.metric === 'tokens') return formatBigToken(row.total_tokens)
  if (props.metric === 'requests') return formatNumber(row.requests)
  return formatCost(row.internal_cost)
}
</script>

<template>
  <GlassCard title="人员 Top10" tooltip="按所选口径取前 10 名，随时间/维度/scope 联动。">
    <div class="mb-3 flex gap-1 rounded-lg bg-slate-100 p-1">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="rounded-md px-3 py-1.5 text-xs transition-colors"
        :class="metric === tab.key ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'"
        @click="emit('metricChange', tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="h-6 w-6 animate-spin rounded-full border-3 border-blue-500 border-t-transparent"></div>
    </div>
    <div v-else class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
            <th class="py-2.5 font-medium">序号</th>
            <th class="py-2.5 font-medium">姓名</th>
            <th class="py-2.5 font-medium">部门</th>
            <th class="py-2.5 text-right font-medium">{{ metricLabel() }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.user_id" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
            <td class="py-3 text-slate-400">{{ row.rank }}</td>
            <td class="py-3 font-medium text-slate-800">{{ row.user_name }}</td>
            <td class="py-3 text-slate-500">{{ row.department || '-' }}</td>
            <td class="py-3 text-right font-medium text-slate-800">{{ metricValue(row) }}</td>
          </tr>
          <tr v-if="rows.length === 0"><td colspan="4" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
        </tbody>
      </table>
    </div>
  </GlassCard>
</template>
