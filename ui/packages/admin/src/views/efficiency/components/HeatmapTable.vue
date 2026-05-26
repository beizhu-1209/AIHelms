<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  rowLabels: string[]
  colLabels: string[]
  /** values[rowIdx][colIdx] = number */
  values: number[][]
  formatter?: (v: number) => string
  cellHeight?: number
}

const props = withDefaults(defineProps<Props>(), {
  formatter: (v: number) => v.toString(),
  cellHeight: 44,
})

const maxValue = computed(() => {
  let m = 0
  for (const row of props.values) {
    for (const v of row) m = Math.max(m, v)
  }
  return m || 1
})

function intensity(v: number): number {
  if (v === 0) return 0
  const ratio = v / maxValue.value
  if (ratio >= 0.8) return 4
  if (ratio >= 0.55) return 3
  if (ratio >= 0.3) return 2
  if (ratio >= 0.1) return 1
  return 0
}

function cellBg(level: number): string {
  const map: Record<number, string> = {
    0: 'rgba(99,102,241,0.05)',
    1: 'rgba(99,102,241,0.2)',
    2: 'rgba(99,102,241,0.4)',
    3: 'rgba(99,102,241,0.6)',
    4: 'rgba(99,102,241,0.85)',
  }
  return map[level]
}

function cellColor(level: number): string {
  if (level >= 3) return 'white'
  if (level >= 2) return '#1a2332'
  if (level >= 1) return '#475569'
  return '#94a3b8'
}
</script>

<template>
  <div class="overflow-x-auto">
    <div
      v-if="rowLabels.length === 0 || colLabels.length === 0"
      class="py-10 text-center text-sm text-slate-400"
    >
      暂无数据
    </div>
    <table v-else class="w-full border-separate" style="border-spacing: 4px; min-width: 560px;">
      <thead>
        <tr>
          <th class="px-2 py-1.5 text-left text-xs font-normal text-slate-400">维度</th>
          <th
            v-for="col in colLabels"
            :key="col"
            class="px-2 py-1.5 text-center text-xs font-normal text-slate-600"
          >
            {{ col }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, ri) in rowLabels" :key="ri">
          <td class="px-2 py-1.5 text-xs font-medium text-slate-700">{{ row }}</td>
          <td
            v-for="(col, ci) in colLabels"
            :key="ci"
            class="text-center text-xs"
            :style="{
              background: cellBg(intensity(values[ri]?.[ci] ?? 0)),
              color: cellColor(intensity(values[ri]?.[ci] ?? 0)),
              borderRadius: '4px',
              height: cellHeight + 'px',
              fontWeight: intensity(values[ri]?.[ci] ?? 0) >= 4 ? 600 : 400,
            }"
          >
            {{ values[ri]?.[ci] ? formatter(values[ri][ci]) : '-' }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
