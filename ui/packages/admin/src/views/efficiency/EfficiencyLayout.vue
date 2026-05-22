<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const subtitle = computed(() => {
  const map: Record<string, string> = {
    EfficiencyDashboard: '企业 AI 投入全貌 · 数据 T+5min 延迟',
    EfficiencyAnalysis: '8 个分析维度自由钻取 · 表格 + 图表双形态',
    EfficiencyAgents: '场景 Key 专属视图 · 衡量定制智能体使用情况',
    EfficiencyModels: '部门 × 模型偏好 · 集中度分析 · 采购建议',
    EfficiencyBudget: '部门 / Key / 供应商预算执行 · 月底预测',
    EfficiencyReports: '数据 + AI 解读 · 周期性生成 · 决策建议跟踪',
    EfficiencyCapability: '评估员工 AI 使用深度与效率',
  }
  return map[String(route.name ?? '')] || 'AI 投资决策驾驶舱，多维度成本分析与洞察'
})

const title = computed(() => {
  const map: Record<string, string> = {
    EfficiencyDashboard: 'AI 投资决策驾驶舱',
    EfficiencyAnalysis: '多维度成本分析',
    EfficiencyAgents: '智能体经营分析',
    EfficiencyModels: '模型偏好分析',
    EfficiencyBudget: '预算管控',
    EfficiencyReports: 'AI 分析报告',
    EfficiencyCapability: 'AI 能力评估',
  }
  return map[String(route.name ?? '')] || 'AI 效能'
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
