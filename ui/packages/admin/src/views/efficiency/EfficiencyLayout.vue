<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const title = computed(() => {
  const map: Record<string, string> = {
    EfficiencyOverview: '总览',
    EfficiencyAdoption: '落地',
    EfficiencyCost: '成本',
    EfficiencyBudget: '预算',
    EfficiencyReports: '报告',
  }
  return map[String(route.name ?? '')] || 'AI 效能'
})

const subtitle = computed(() => {
  const map: Record<string, string> = {
    EfficiencyOverview: '上了 AI 效果怎么样？',
    EfficiencyAdoption: '谁在用 AI？用得深不深？',
    EfficiencyCost: '钱花在哪里？花得合不合理？',
    EfficiencyBudget: '预算够不够？会不会超？谁在超？',
    EfficiencyReports: '自动生成可汇报的 AI 经营分析报告',
  }
  return map[String(route.name ?? '')] || ''
})
</script>

<template>
  <div class="min-h-full">
    <div class="mb-5 flex items-end justify-between gap-4 border-b border-slate-200/60 pb-4">
      <div>
        <h1 class="text-xl font-semibold tracking-tight text-slate-900">{{ title }}</h1>
        <p class="mt-1 text-xs text-slate-500">{{ subtitle }}</p>
      </div>
    </div>
    <router-view />
  </div>
</template>
