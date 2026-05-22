<script setup lang="ts">
export interface SuggestionData {
  id?: number
  title: string
  description: string
  priority: 'high' | 'medium' | 'low' | 'opportunity'
  expected_impact?: string
  status?: 'pending' | 'accepted' | 'rejected' | 'implemented'
}

interface Props {
  suggestion: SuggestionData
}

defineProps<Props>()
defineEmits<{
  'update-status': [id: number, status: 'accepted' | 'rejected' | 'implemented']
}>()

const priorityClass: Record<string, string> = {
  high: 'border-l-red-400 bg-red-50/40',
  medium: 'border-l-amber-400 bg-amber-50/40',
  low: 'border-l-indigo-400 bg-indigo-50/40',
  opportunity: 'border-l-emerald-400 bg-emerald-50/40',
}

const badgeClass: Record<string, string> = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-indigo-100 text-indigo-700',
  opportunity: 'bg-emerald-100 text-emerald-700',
}

const priorityLabel: Record<string, string> = {
  high: '高优先级',
  medium: '中优先级',
  low: '低优先级',
  opportunity: '机会',
}
</script>

<template>
  <div
    class="rounded-md border-l-4 px-4 py-3"
    :class="priorityClass[suggestion.priority] || priorityClass.medium"
  >
    <div class="mb-1.5 flex items-start justify-between gap-2">
      <div class="flex items-center gap-2">
        <span class="rounded px-2 py-0.5 text-xs font-medium" :class="badgeClass[suggestion.priority]">
          {{ priorityLabel[suggestion.priority] }}
        </span>
        <strong class="text-sm text-slate-800">{{ suggestion.title }}</strong>
      </div>
      <div v-if="suggestion.id && suggestion.status === 'pending'" class="flex shrink-0 gap-1">
        <button
          class="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-50"
          @click="$emit('update-status', suggestion.id!, 'accepted')"
        >
          已采纳
        </button>
        <button
          class="rounded border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-50"
          @click="$emit('update-status', suggestion.id!, 'rejected')"
        >
          已拒绝
        </button>
      </div>
      <span
        v-else-if="suggestion.status && suggestion.status !== 'pending'"
        class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
      >
        {{ suggestion.status === 'accepted' ? '已采纳' : suggestion.status === 'rejected' ? '已拒绝' : '已实施' }}
      </span>
    </div>
    <p class="text-xs leading-relaxed text-slate-600">{{ suggestion.description }}</p>
    <p v-if="suggestion.expected_impact" class="mt-1.5 text-xs text-slate-400">
      预计影响：{{ suggestion.expected_impact }}
    </p>
  </div>
</template>
