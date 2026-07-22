<script setup lang="ts">
type Metric = 'cost' | 'tokens' | 'requests'

interface LeaderboardRow {
  rank: number
  user_id: number
  user_name: string
  department: string
  internal_cost: number
  total_tokens: number
  requests: number
}

const props = defineProps<{
  metric: Metric
  rows: LeaderboardRow[]
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
  return '内部成本'
}

function formatBigToken(value: number): string {
  if (value >= 1e9) return (value / 1e9).toFixed(1) + 'B'
  if (value >= 1e6) return (value / 1e6).toFixed(1) + 'M'
  if (value >= 1e3) return (value / 1e3).toFixed(1) + 'K'
  return String(value)
}

function metricValue(row: LeaderboardRow): string {
  if (props.metric === 'tokens') return formatBigToken(row.total_tokens)
  if (props.metric === 'requests') return row.requests.toLocaleString()
  return `¥${row.internal_cost.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}
</script>

<template>
  <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
    <div class="mb-4 flex items-center justify-between">
      <h3 class="text-sm font-semibold text-slate-900">人员 Top10</h3>
      <div class="flex gap-1 rounded-lg bg-slate-100 p-1">
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
    </div>
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="h-6 w-6 animate-spin rounded-full border-3 border-purple-500 border-t-transparent"></div>
    </div>
    <div v-else class="overflow-hidden rounded-lg border border-slate-100">
      <table class="w-full text-xs">
        <thead class="bg-slate-50 text-left text-slate-500">
          <tr>
            <th class="px-3 py-2 font-medium">序号</th>
            <th class="px-3 py-2 font-medium">姓名</th>
            <th class="px-3 py-2 font-medium">部门</th>
            <th class="px-3 py-2 text-right font-medium">{{ metricLabel() }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.user_id" class="border-t border-slate-100 hover:bg-slate-50">
            <td class="px-3 py-2 text-slate-400">{{ row.rank }}</td>
            <td class="px-3 py-2 font-medium text-slate-700">{{ row.user_name }}</td>
            <td class="px-3 py-2 text-slate-500">{{ row.department || '-' }}</td>
            <td class="px-3 py-2 text-right font-medium text-slate-900">{{ metricValue(row) }}</td>
          </tr>
          <tr v-if="rows.length === 0"><td colspan="4" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
