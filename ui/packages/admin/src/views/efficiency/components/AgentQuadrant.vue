<script setup lang="ts">
import { computed } from 'vue'

export interface QuadrantBubble {
  /** X 轴：调用量 */
  x: number
  /** Y 轴：增长率（百分比） */
  y: number
  /** 气泡大小：使用人数 */
  size: number
  label: string
  /** 分类，决定颜色 */
  category?: 'star' | 'potential' | 'cash_cow' | 'zombie'
}

interface Props {
  bubbles: QuadrantBubble[]
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  height: 380,
})

const width = 720
const padding = { top: 24, right: 24, bottom: 36, left: 56 }

const chartW = computed(() => width - padding.left - padding.right)
const chartH = computed(() => props.height - padding.top - padding.bottom)

const maxX = computed(() => Math.max(...props.bubbles.map((b) => b.x), 100))
const maxY = computed(() => Math.max(...props.bubbles.map((b) => Math.abs(b.y)), 50))
const maxSize = computed(() => Math.max(...props.bubbles.map((b) => b.size), 1))

// X 轴中线（调用量中位数水平），简化为最大值的 30%
const midX = computed(() => maxX.value * 0.3)
// Y 轴中线（0% 增长）
const midY = 0

function plotX(x: number): number {
  return padding.left + (x / maxX.value) * chartW.value
}

function plotY(y: number): number {
  const yRange = maxY.value * 2
  // Y=0 在中线
  return padding.top + chartH.value / 2 - (y / yRange) * chartH.value
}

function bubbleR(size: number): number {
  const min = 6
  const max = 20
  if (maxSize.value === 0) return min
  return min + (size / maxSize.value) * (max - min)
}

function bubbleColor(b: QuadrantBubble): string {
  // 自动归类
  const isHighCall = b.x >= midX.value
  const isGrowth = b.y >= midY
  if (isHighCall && isGrowth) return '#10b981' // 明星
  if (!isHighCall && isGrowth) return '#6366f1' // 潜力
  if (isHighCall && !isGrowth) return '#f59e0b' // 现金牛
  return '#ef4444' // 僵尸
}

function bubbleCategory(b: QuadrantBubble): string {
  const isHighCall = b.x >= midX.value
  const isGrowth = b.y >= midY
  if (isHighCall && isGrowth) return 'star'
  if (!isHighCall && isGrowth) return 'potential'
  if (isHighCall && !isGrowth) return 'cash_cow'
  return 'zombie'
}

const midXPlot = computed(() => plotX(midX.value))
const midYPlot = computed(() => plotY(midY))
</script>

<template>
  <div v-if="bubbles.length === 0" class="flex items-center justify-center text-sm text-slate-400" :style="{ height: `${height}px` }">
    暂无数据
  </div>
  <div v-else class="relative">
    <svg :viewBox="`0 0 ${width} ${height}`" class="w-full" preserveAspectRatio="none">
      <!-- 4 象限背景 -->
      <rect :x="midXPlot" :y="padding.top" :width="width - padding.right - midXPlot" :height="midYPlot - padding.top" fill="rgba(16,185,129,0.06)" />
      <rect :x="padding.left" :y="padding.top" :width="midXPlot - padding.left" :height="midYPlot - padding.top" fill="rgba(99,102,241,0.06)" />
      <rect :x="midXPlot" :y="midYPlot" :width="width - padding.right - midXPlot" :height="height - padding.bottom - midYPlot" fill="rgba(245,158,11,0.06)" />
      <rect :x="padding.left" :y="midYPlot" :width="midXPlot - padding.left" :height="height - padding.bottom - midYPlot" fill="rgba(239,68,68,0.06)" />

      <!-- 象限分割线 -->
      <line :x1="midXPlot" :y1="padding.top" :x2="midXPlot" :y2="height - padding.bottom" stroke="#cbd5e1" stroke-dasharray="4 4" />
      <line :x1="padding.left" :y1="midYPlot" :x2="width - padding.right" :y2="midYPlot" stroke="#cbd5e1" stroke-dasharray="4 4" />

      <!-- 象限标签 -->
      <text :x="width - padding.right - 8" :y="padding.top + 14" text-anchor="end" font-size="10" fill="#059669" font-weight="600">明星（推广）</text>
      <text :x="padding.left + 8" :y="padding.top + 14" font-size="10" fill="#4f46e5" font-weight="600">潜力（培育）</text>
      <text :x="width - padding.right - 8" :y="height - padding.bottom - 8" text-anchor="end" font-size="10" fill="#d97706" font-weight="600">现金牛（保留）</text>
      <text :x="padding.left + 8" :y="height - padding.bottom - 8" font-size="10" fill="#dc2626" font-weight="600">僵尸（下线）</text>

      <!-- 轴标签 -->
      <text :x="width / 2" :y="height - 6" text-anchor="middle" font-size="9" fill="#94a3b8">调用量 →</text>
      <text :x="14" :y="height / 2" text-anchor="middle" font-size="9" fill="#94a3b8" transform="rotate(-90 14 ${height/2})">↑ 增长率 %</text>

      <!-- 气泡 -->
      <g v-for="(b, i) in bubbles" :key="i">
        <circle
          :cx="plotX(b.x)"
          :cy="plotY(b.y)"
          :r="bubbleR(b.size)"
          :fill="bubbleColor(b)"
          fill-opacity="0.6"
          :stroke="bubbleColor(b)"
          stroke-width="1.5"
        />
        <text
          :x="plotX(b.x)"
          :y="plotY(b.y) + bubbleR(b.size) + 11"
          text-anchor="middle"
          font-size="9"
          fill="#1a2332"
        >
          {{ b.label }}
        </text>
      </g>
    </svg>
  </div>
</template>
