<script setup lang="ts">
import { computed } from 'vue'
import type { AiKey } from '@aihelms/shared'

interface Props {
  /** 主 key 或场景 key，从中读 budget_limit / budget_duration / budget_used */
  keyData: AiKey | null | undefined
}

const props = defineProps<Props>()

const limit = computed(() => {
  const v = props.keyData?.budget_limit
  if (!v) return 0
  return Number(v) || 0
})

// budget_used 字段后端尚未返回（成本中心未上线），先按 0 占位
const used = computed(() => {
  const k = props.keyData as (AiKey & { budget_used?: string }) | null | undefined
  const v = k?.budget_used
  if (!v) return 0
  return Number(v) || 0
})

const percent = computed(() => {
  if (!limit.value) return 0
  return Math.min(100, (used.value / limit.value) * 100)
})

const periodLabel = computed(() => {
  const dur = props.keyData?.budget_duration
  if (!dur) return ''
  const m = String(dur).match(/^(\d+)d$/)
  if (!m) return dur
  const days = Number(m[1])
  if (days === 1) return '1天预算'
  if (days === 7) return '7天预算'
  if (days === 30) return '30天预算'
  return `${days}天预算`
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
  <div v-if="!keyData || limit <= 0" class="text-xs text-slate-400">未设置</div>
  <div v-else class="min-w-[140px]">
    <div class="mb-1 flex items-center justify-between text-xs">
      <span class="text-slate-500">{{ periodLabel }}</span>
      <span class="text-slate-600">{{ used.toFixed(2) }} / ¥{{ limit.toFixed(2) }}</span>
    </div>
    <div class="h-1.5 w-full overflow-hidden rounded-full" :class="trackColor">
      <div
        class="h-full rounded-full transition-all"
        :class="barColor"
        :style="{ width: percent + '%' }"
      />
    </div>
  </div>
</template>
