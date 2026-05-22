<script setup lang="ts">
import { computed } from 'vue'

export interface ParetoItem {
  label: string
  value: number
}

interface Props {
  data: ParetoItem[]
  threshold?: number
  height?: number
  formatter?: (v: number) => string
}

const props = withDefaults(defineProps<Props>(), {
  threshold: 80,
  height: 240,
  formatter: (v: number) => v.toString(),
})

const sorted = computed(() => [...props.data].sort((a, b) => b.value - a.value))
const total = computed(() => sorted.value.reduce((s, d) => s + d.value, 0))

const enriched = computed(() => {
  let cum = 0
  return sorted.value.map((d) => {
    cum += d.value
    return {
      ...d,
      pct: total.value > 0 ? (d.value / total.value) * 100 : 0,
      cumPct: total.value > 0 ? (cum / total.value) * 100 : 0,
    }
  })
})

const width = 720
const padding = { top: 16, right: 48, bottom: 36, left: 48 }
const chartW = computed(() => width - padding.left - padding.right)
const chartH = computed(() => props.height - padding.top - padding.bottom)
const maxBar = computed(() => Math.max(...enriched.value.map((d) => d.value), 1))

function barX(i: number): number {
  const n = enriched.value.length
  const colW = chartW.value / n
  return padding.left + i * colW + colW * 0.15
}

function barW(): number {
  const n = enriched.value.length
  if (n === 0) return 0
  return (chartW.value / n) * 0.7
}

function barY(v: number): number {
  return padding.top + chartH.value - (v / maxBar.value) * chartH.value
}

function barH(v: number): number {
  return (v / maxBar.value) * chartH.value
}

function lineY(pct: number): number {
  return padding.top + chartH.value - (pct / 100) * chartH.value
}

function lineX(i: number): number {
  const n = enriched.value.length
  const colW = chartW.value / n
  return padding.left + i * colW + colW / 2
}

const linePath = computed(() => {
  return enriched.value.map((d, i) => `${i === 0 ? 'M' : 'L'}${lineX(i)},${lineY(d.cumPct)}`).join(' ')
})

const thresholdY = computed(() => lineY(props.threshold))

const mainCount = computed(() => {
  let c = 0
  for (const d of enriched.value) {
    c++
    if (d.cumPct >= props.threshold) break
  }
  return c
})
</script>

<template>
  <div v-if="enriched.length === 0" class="flex items-center justify-center text-sm text-slate-400" :style="{ height: `${height}px` }">
    暂无数据
  </div>
  <div v-else>
    <svg :viewBox="`0 0 ${width} ${height}`" class="w-full" preserveAspectRatio="none">
      <!-- Y 轴左：金额 -->
      <text :x="padding.left - 6" :y="padding.top - 4" text-anchor="end" font-size="8" fill="#94a3b8">金额</text>
      <!-- Y 轴右：百分比 -->
      <text :x="width - padding.right + 6" :y="padding.top - 4" font-size="8" fill="#94a3b8">累计 %</text>

      <!-- 80% 阈值线 -->
      <line :x1="padding.left" :y1="thresholdY" :x2="width - padding.right" :y2="thresholdY" stroke="#f59e0b" stroke-width="1" stroke-dasharray="4 4" />
      <text :x="width - padding.right + 4" :y="thresholdY + 3" font-size="8" fill="#f59e0b">{{ threshold }}%</text>

      <!-- 柱 -->
      <rect
        v-for="(d, i) in enriched"
        :key="`bar-${i}`"
        :x="barX(i)"
        :y="barY(d.value)"
        :width="barW()"
        :height="barH(d.value)"
        :fill="i < mainCount ? '#6366f1' : '#cbd5e1'"
        rx="2"
      />

      <!-- X 标签 -->
      <text
        v-for="(d, i) in enriched"
        :key="`xl-${i}`"
        :x="lineX(i)"
        :y="height - 16"
        text-anchor="middle"
        font-size="8"
        fill="#475569"
      >
        {{ d.label.length > 8 ? d.label.slice(0, 8) + '…' : d.label }}
      </text>
      <text
        v-for="(d, i) in enriched"
        :key="`xc-${i}`"
        :x="lineX(i)"
        :y="height - 4"
        text-anchor="middle"
        font-size="8"
        fill="#94a3b8"
      >
        {{ d.cumPct.toFixed(0) }}%
      </text>

      <!-- 累计折线 -->
      <path :d="linePath" fill="none" stroke="#ec4899" stroke-width="1.5" />
      <circle
        v-for="(d, i) in enriched"
        :key="`pt-${i}`"
        :cx="lineX(i)"
        :cy="lineY(d.cumPct)"
        r="2"
        fill="#ec4899"
      />
    </svg>
  </div>
</template>
