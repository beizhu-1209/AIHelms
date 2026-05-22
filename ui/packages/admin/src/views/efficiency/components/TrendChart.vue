<script setup lang="ts">
import { computed } from 'vue'

export interface TrendSeries {
  name: string
  color: string
  values: number[]
}

interface Props {
  labels: string[]
  series: TrendSeries[]
  height?: number
  yFormatter?: (v: number) => string
}

const props = withDefaults(defineProps<Props>(), {
  height: 240,
  yFormatter: (v: number) => v.toString(),
})

const padding = { top: 16, right: 16, bottom: 28, left: 48 }
const width = 720

const allValues = computed(() => props.series.flatMap((s) => s.values))
const maxValue = computed(() => {
  const m = Math.max(...allValues.value, 0)
  if (m === 0) return 100
  return Math.ceil(m * 1.1)
})

const chartWidth = computed(() => width - padding.left - padding.right)
const chartHeight = computed(() => props.height - padding.top - padding.bottom)

function xAt(idx: number): number {
  if (props.labels.length <= 1) return padding.left
  return padding.left + (idx / (props.labels.length - 1)) * chartWidth.value
}

function yAt(value: number): number {
  return padding.top + chartHeight.value - (value / maxValue.value) * chartHeight.value
}

const yTicks = computed(() => {
  const steps = 4
  return Array.from({ length: steps + 1 }, (_, i) => (maxValue.value / steps) * i)
})

function pathOf(values: number[]): string {
  return values.map((v, i) => `${i === 0 ? 'M' : 'L'}${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`).join(' ')
}

function areaOf(values: number[]): string {
  const top = pathOf(values)
  const baseY = yAt(0)
  return `${top} L${xAt(values.length - 1).toFixed(1)},${baseY.toFixed(1)} L${xAt(0).toFixed(1)},${baseY.toFixed(1)} Z`
}
</script>

<template>
  <div v-if="series.length === 0 || labels.length === 0" class="flex items-center justify-center text-sm text-slate-400" :style="{ height: `${height}px` }">
    暂无数据
  </div>
  <div v-else>
    <svg :viewBox="`0 0 ${width} ${height}`" class="w-full" preserveAspectRatio="none">
      <!-- Y 轴网格 -->
      <g>
        <line
          v-for="(t, i) in yTicks"
          :key="`grid-${i}`"
          :x1="padding.left"
          :y1="yAt(t)"
          :x2="width - padding.right"
          :y2="yAt(t)"
          stroke="#e2e8f0"
          stroke-dasharray="2 4"
          stroke-width="0.5"
        />
        <text
          v-for="(t, i) in yTicks"
          :key="`y-${i}`"
          :x="padding.left - 6"
          :y="yAt(t) + 3"
          text-anchor="end"
          font-size="8"
          fill="#94a3b8"
        >
          {{ yFormatter(t) }}
        </text>
      </g>

      <!-- X 轴标签 -->
      <g>
        <text
          v-for="(label, i) in labels"
          :key="`x-${i}`"
          :x="xAt(i)"
          :y="height - 8"
          text-anchor="middle"
          font-size="8"
          fill="#94a3b8"
        >
          {{ label }}
        </text>
      </g>

      <!-- 数据线 -->
      <g v-for="(s, idx) in series" :key="idx">
        <path
          :d="areaOf(s.values)"
          :fill="s.color"
          opacity="0.08"
        />
        <path
          :d="pathOf(s.values)"
          fill="none"
          :stroke="s.color"
          stroke-width="1.5"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
        <circle
          v-for="(v, i) in s.values"
          :key="i"
          :cx="xAt(i)"
          :cy="yAt(v)"
          r="2"
          :fill="s.color"
        />
      </g>
    </svg>

    <!-- Legend -->
    <div class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
      <div v-for="s in series" :key="s.name" class="flex items-center gap-1">
        <span class="h-1.5 w-1.5 rounded-sm" :style="{ background: s.color }"></span>
        <span class="text-slate-600">{{ s.name }}</span>
      </div>
    </div>
  </div>
</template>
