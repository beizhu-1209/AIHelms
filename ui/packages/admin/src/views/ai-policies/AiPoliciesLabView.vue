<script setup lang="ts">
import { computed, ref } from 'vue'
import { Bot, MessageSquareText, Plug, ShieldCheck } from 'lucide-vue-next'

type LabDomain = 'mcp' | 'agent' | 'prompt'

const activeDomain = ref<LabDomain>('mcp')
const domains = [
  {
    key: 'mcp' as const,
    label: 'MCP 审计',
    icon: Plug,
    description: '后续检查 MCP Server 工具权限、数据边界、外部连接和调用风险。',
  },
  {
    key: 'agent' as const,
    label: 'Agent 审计',
    icon: Bot,
    description: '后续检查智能体工具链、角色边界、系统提示词和执行路径风险。',
  },
  {
    key: 'prompt' as const,
    label: 'Prompt 审计',
    icon: MessageSquareText,
    description: '后续检查提示词注入、越权指令、敏感信息暴露和输出约束。',
  },
]

const activeInfo = computed(() => domains.find((item) => item.key === activeDomain.value) || domains[0])
</script>

<template>
  <div class="space-y-5">
    <div>
      <div class="mb-2 inline-flex items-center gap-2 rounded-full bg-purple-50 px-3 py-1 text-xs font-medium text-purple-700"><ShieldCheck class="h-3.5 w-3.5" />AI Policies</div>
      <h1 class="text-2xl font-bold text-slate-900">AI Policies 实验室</h1>
      <p class="mt-1 text-sm text-slate-500">查看即将接入的审计能力方向。</p>
    </div>
    <div class="grid gap-3 md:grid-cols-3">
      <button v-for="domain in domains" :key="domain.key" class="group rounded-xl border bg-white p-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md" :class="activeDomain === domain.key ? 'border-purple-300 ring-2 ring-purple-100' : 'border-slate-200 hover:border-purple-200'" @click="activeDomain = domain.key">
        <div class="flex items-start justify-between gap-3"><div class="flex items-center gap-2"><div class="flex h-9 w-9 items-center justify-center rounded-lg transition-colors" :class="activeDomain === domain.key ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-500 group-hover:bg-purple-50 group-hover:text-purple-700'"><component :is="domain.icon" class="h-5 w-5" /></div><div><div class="text-sm font-semibold text-slate-900">{{ domain.label }}</div><div class="mt-0.5 text-xs text-slate-500">规划中</div></div></div><span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">敬请期待</span></div>
        <p class="mt-3 line-clamp-2 text-xs leading-5 text-slate-500">{{ domain.description }}</p>
      </button>
    </div>
    <div class="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
      <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-slate-100 text-slate-500"><component :is="activeInfo.icon" class="h-7 w-7" /></div>
      <h2 class="mt-4 text-lg font-semibold text-slate-900">{{ activeInfo.label }}规划中，敬请期待</h2>
      <p class="mx-auto mt-2 max-w-2xl text-sm leading-6 text-slate-500">{{ activeInfo.description }}</p>
    </div>
  </div>
</template>
