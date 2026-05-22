<script setup lang="ts">
import { computed } from 'vue'
import { TrendingUp, TrendingDown, Minus } from 'lucide-vue-next'

interface Props {
  label: string
  value: string | number
  unit?: string
  change?: number | null
  changeText?: string
  /** 'up-bad' 表示数值上涨是负面（如成本），'up-good' 表示上涨是正面（如调用量） */
  changeKind?: 'up-bad' | 'up-good' | 'neutral'
  sparkline?: number[]
  sparkColor?: string
  valueColor?: string
}

const props = withDefaults(defineProps<Props>(), {
  unit: '',
  change: null,
  changeText: '',
  changeKind: 'up-bad',
  sparkline: () => [],
  sparkColor: '#6366f1',
  valueColor: '',
})

const sparkPath = computed(() => {
  const pts = props.sparkline
  if (pts.length < 2) return ''
  const max = Math.max(...pts)
  const min = Math.min(...pts)
  const range = max - min || 1
  const w = 80
  const h = 28
  return pts
    .map((p, i) => {
      const x = (i / (pts.length - 1)) * w
      const y = h - ((p - min) / range) * h
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

const changeColor = computed(() => {
  if (props.change === null || props.change === undefined) return 'text-slate-400'
  if (props.changeKind === 'neutral') return 'text-slate-500'
  const isPositive = props.change > 0
  if (props.changeKind === 'up-bad') return isPositive ? 'text-red-500' : 'text-emerald-600'
  return isPositive ? 'text-emerald-600' : 'text-red-500'
})

const changeIcon = computed(() => {
  if (props.change === null || props.change === undefined || props.change === 0) return Minus
  return props.change > 0 ? TrendingUp : TrendingDown
})

const changeLabel = computed(() => {
  if (props.changeText) return props.changeText
  if (props.change === null || props.change === undefined) return '--'
  const sign = props.change > 0 ? '+' : ''
  return `${sign}${props.change.toFixed(1)}%`
})
</script>

<template>
  <div class="relative overflow-hidden rounded-xl border border-white/80 bg-white/70 px-5 py-4 shadow-sm backdrop-blur-xl">
    <div class="text-xs text-slate-500">{{ label }}</div>
    <div class="mt-1.5 flex items-baseline gap-1">
      <span class="text-2xl font-semibold tracking-tight" :class="valueColor || 'text-slate-900'">
        {{ value }}
      </span>
      <span v-if="unit" class="text-sm text-slate-400">{{ unit }}</span>
    </div>
    <div class="mt-1.5 flex items-center gap-1 text-xs" :class="changeColor">
      <component :is="changeIcon" class="h-3 w-3" />
      <span>{{ changeLabel }}</span>
    </div>
    <svg
      v-if="sparkline.length >= 2"
      class="absolute right-3 top-3 opacity-70"
      width="80"
      height="28"
      viewBox="0 0 80 28"
    >
      <path :d="sparkPath" fill="none" :stroke="sparkColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
    </svg>
  </div>
</template>
