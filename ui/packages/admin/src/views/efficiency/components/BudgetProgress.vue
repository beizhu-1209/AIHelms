<script setup lang="ts">
interface Props {
  /** 0-100 */
  value: number
  height?: string
  showLabel?: boolean
}

withDefaults(defineProps<Props>(), {
  height: 'h-1.5',
  showLabel: false,
})

function colorClass(v: number): string {
  if (v >= 100) return 'bg-gradient-to-r from-red-500 to-rose-400'
  if (v >= 90) return 'bg-gradient-to-r from-orange-500 to-amber-400'
  if (v >= 80) return 'bg-gradient-to-r from-amber-500 to-yellow-400'
  return 'bg-gradient-to-r from-indigo-500 to-violet-400'
}
</script>

<template>
  <div class="flex items-center gap-2">
    <div class="flex-1 overflow-hidden rounded-full bg-slate-200/60" :class="height">
      <div
        :class="['h-full rounded-full transition-all', colorClass(value)]"
        :style="{ width: `${Math.min(value, 100)}%` }"
      />
    </div>
    <span v-if="showLabel" class="min-w-[44px] text-right text-xs font-medium text-slate-600">
      {{ value.toFixed(0) }}%
    </span>
  </div>
</template>
