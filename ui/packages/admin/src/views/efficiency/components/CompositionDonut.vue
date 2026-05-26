<script setup lang="ts">
import { computed } from 'vue'

export interface DonutSlice {
  name: string
  value: number
  color: string
}

interface Props {
  data: DonutSlice[]
  centerValue?: string
  centerLabel?: string
  size?: number
  formatter?: (v: number) => string
}

const props = withDefaults(defineProps<Props>(), {
  centerValue: '',
  centerLabel: '',
  size: 160,
  formatter: (v: number) => v.toString(),
})

const total = computed(() => props.data.reduce((s, d) => s + d.value, 0))

const segments = computed(() => {
  if (total.value === 0) return []
  let cumulative = 0
  return props.data.map((d) => {
    const fraction = d.value / total.value
    const start = cumulative
    cumulative += fraction
    return {
      ...d,
      fraction,
      start,
      end: cumulative,
      pct: fraction * 100,
    }
  })
})

const radius = computed(() => props.size / 2)
const innerRadius = computed(() => radius.value * 0.6)
const cx = computed(() => radius.value)
const cy = computed(() => radius.value)

function arcPath(start: number, end: number): string {
  if (end - start >= 1) {
    // 完整圆环
    return `M ${cx.value} ${cy.value - radius.value}
            A ${radius.value} ${radius.value} 0 1 1 ${cx.value - 0.01} ${cy.value - radius.value}
            L ${cx.value - 0.01} ${cy.value - innerRadius.value}
            A ${innerRadius.value} ${innerRadius.value} 0 1 0 ${cx.value} ${cy.value - innerRadius.value} Z`
  }
  const startAngle = start * 2 * Math.PI - Math.PI / 2
  const endAngle = end * 2 * Math.PI - Math.PI / 2
  const largeArc = end - start > 0.5 ? 1 : 0

  const x1 = cx.value + radius.value * Math.cos(startAngle)
  const y1 = cy.value + radius.value * Math.sin(startAngle)
  const x2 = cx.value + radius.value * Math.cos(endAngle)
  const y2 = cy.value + radius.value * Math.sin(endAngle)
  const x3 = cx.value + innerRadius.value * Math.cos(endAngle)
  const y3 = cy.value + innerRadius.value * Math.sin(endAngle)
  const x4 = cx.value + innerRadius.value * Math.cos(startAngle)
  const y4 = cy.value + innerRadius.value * Math.sin(startAngle)

  return `M ${x1} ${y1}
          A ${radius.value} ${radius.value} 0 ${largeArc} 1 ${x2} ${y2}
          L ${x3} ${y3}
          A ${innerRadius.value} ${innerRadius.value} 0 ${largeArc} 0 ${x4} ${y4} Z`
}
</script>

<template>
  <div class="flex flex-col items-center gap-4">
    <div v-if="total === 0" class="flex items-center justify-center text-sm text-slate-400" :style="{ width: `${size}px`, height: `${size}px` }">
      暂无数据
    </div>
    <div v-else class="relative" :style="{ width: `${size}px`, height: `${size}px` }">
      <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
        <path
          v-for="(seg, i) in segments"
          :key="i"
          :d="arcPath(seg.start, seg.end)"
          :fill="seg.color"
          stroke="white"
          stroke-width="1"
        />
      </svg>
      <div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <div v-if="centerValue" class="text-lg font-semibold text-slate-900">{{ centerValue }}</div>
        <div v-if="centerLabel" class="text-xs text-slate-500">{{ centerLabel }}</div>
      </div>
    </div>

    <div class="w-full space-y-2">
      <div v-for="(seg, i) in segments" :key="i" class="flex items-center gap-2 text-xs">
        <span class="h-2 w-2 rounded-sm" :style="{ background: seg.color }"></span>
        <span class="flex-1 text-slate-600">{{ seg.name }}</span>
        <span class="font-semibold text-slate-900">{{ formatter(seg.value) }}</span>
        <span class="w-10 text-right text-slate-400">{{ seg.pct.toFixed(1) }}%</span>
      </div>
    </div>
  </div>
</template>
