<script setup lang="ts">
import { Download } from 'lucide-vue-next'
import GlassCard from './GlassCard.vue'
import type { AgentRow, ResourceRow } from '../adoptionTypes'

type LogTab = 'llm' | 'mcp' | 'skill' | 'agent'

function agentSparkline(values: number[]): string {
  if (values.length < 2) {
    return ''
  }
  const max = Math.max(...values) || 1
  return values
    .map((value, index) => `${index === 0 ? 'M' : 'L'}${(index / (values.length - 1)) * 48},${16 - (value / max) * 16}`)
    .join(' ')
}

function emitLog(tab: LogTab, params: Record<string, string | number>) {
  emit('openLogs', tab, params)
}

function emitResourceExport(type: 'mcp' | 'skill') {
  emit('exportResources', type)
}

function isExporting(key: string): boolean {
  return props.exportingKey === key
}

const props = defineProps<{
  agents: AgentRow[]
  mcpResources: ResourceRow[]
  skillResources: ResourceRow[]
  exportingKey: string
}>()

const emit = defineEmits<{
  openLogs: [tab: LogTab, params: Record<string, string | number>]
  exportAgents: []
  exportResources: [type: 'mcp' | 'skill']
}>()
</script>

<template>
  <GlassCard title="智能体使用明细" tooltip="基于智能体使用日志统计。用户数 = 所选时间内独立使用人数，调用次数 = 所选时间内会话数。">
    <template #action>
      <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" :disabled="isExporting('adoption_agents')" @click="emit('exportAgents')">
        <Download class="h-3.5 w-3.5" /> 导出
      </button>
    </template>
    <div class="max-h-[420px] overflow-auto">
      <table class="min-w-[820px] w-full text-xs">
        <thead>
          <tr class="border-b border-slate-100 text-left text-slate-500">
            <th class="px-5 py-3 font-medium">排名</th>
            <th class="px-3 py-3 font-medium">智能体</th>
            <th class="px-3 py-3 font-medium">平台</th>
            <th class="px-3 py-3 font-medium">归属部门</th>
            <th class="px-3 py-3 font-medium text-right">用户数</th>
            <th class="px-3 py-3 font-medium text-right">调用次数</th>
            <th class="px-3 py-3 font-medium">趋势</th>
            <th class="px-5 py-3 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="agent in agents" :key="agent.id" class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
            <td class="px-5 py-3">
              <span class="inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold" :class="agent.rank <= 3 ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-500'">{{ agent.rank }}</span>
            </td>
            <td class="px-3 py-3 font-medium text-slate-800">{{ agent.name }}</td>
            <td class="px-3 py-3 text-slate-600">{{ agent.platform }}</td>
            <td class="px-3 py-3 text-slate-600">{{ agent.department }}</td>
            <td class="px-3 py-3 text-right text-slate-700">{{ agent.user_count }}</td>
            <td class="px-3 py-3 text-right font-medium text-slate-900">{{ agent.monthly_calls.toLocaleString() }}</td>
            <td class="px-3 py-3">
              <svg v-if="agent.trend.length >= 2" width="48" height="16" viewBox="0 0 48 16" class="inline-block">
                <path :d="agentSparkline(agent.trend)" fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </td>
            <td class="px-5 py-3 text-right">
              <button class="rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" @click="emitLog('agent', { agent_id: agent.id })">使用日志</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="agents.length === 0" class="py-10 text-center text-sm text-slate-400">暂无数据</div>
    </div>
  </GlassCard>

  <GlassCard title="MCP 使用明细" padding="p-0" tooltip="基于 MCP 调用日志统计，并受顶部时间筛选联动。使用人数 = 有过调用的独立用户数。">
    <template #action>
      <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" :disabled="isExporting('adoption_mcp')" @click="emitResourceExport('mcp')">
        <Download class="h-3.5 w-3.5" /> 导出
      </button>
    </template>
    <div class="max-h-[360px] overflow-auto">
      <table class="min-w-[720px] w-full text-xs">
        <thead><tr class="border-b border-slate-100 text-left text-slate-500"><th class="px-5 py-3 font-medium">MCP Server</th><th class="px-3 py-3 font-medium text-right">使用人数</th><th class="px-3 py-3 font-medium text-right">调用次数</th><th class="px-5 py-3 font-medium text-right">操作</th></tr></thead>
        <tbody>
          <tr v-for="resource in mcpResources" :key="resource.id" class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
            <td class="px-5 py-3 font-medium text-slate-800">{{ resource.name }}</td>
            <td class="px-3 py-3 text-right text-slate-700">{{ resource.user_count }}</td>
            <td class="px-3 py-3 text-right font-medium text-slate-900">{{ resource.monthly_calls.toLocaleString() }}</td>
            <td class="px-5 py-3 text-right"><button class="rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" @click="emitLog('mcp', { server_id: resource.id })">调用日志</button></td>
          </tr>
        </tbody>
      </table>
      <div v-if="mcpResources.length === 0" class="py-8 text-center text-sm text-slate-400">暂无数据</div>
    </div>
  </GlassCard>

  <GlassCard title="Skill 使用明细" padding="p-0" tooltip="基于 Skill 使用日志统计，并受顶部时间筛选联动。安装人数 = 执行 install 的独立用户数；下载次数 = download 动作次数。">
    <template #action>
      <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" :disabled="isExporting('adoption_skill')" @click="emitResourceExport('skill')">
        <Download class="h-3.5 w-3.5" /> 导出
      </button>
    </template>
    <div class="max-h-[360px] overflow-auto">
      <table class="min-w-[720px] w-full text-xs">
        <thead><tr class="border-b border-slate-100 text-left text-slate-500"><th class="px-5 py-3 font-medium">Skill</th><th class="px-3 py-3 font-medium text-right">安装人数</th><th class="px-3 py-3 font-medium text-right">下载次数</th><th class="px-5 py-3 font-medium text-right">操作</th></tr></thead>
        <tbody>
          <tr v-for="resource in skillResources" :key="resource.id" class="border-b border-slate-50 transition-colors hover:bg-slate-50/50">
            <td class="px-5 py-3 font-medium text-slate-800">{{ resource.name }}</td>
            <td class="px-3 py-3 text-right text-slate-700">{{ resource.user_count }}</td>
            <td class="px-3 py-3 text-right font-medium text-slate-900">{{ resource.monthly_calls.toLocaleString() }}</td>
            <td class="px-5 py-3 text-right"><button class="rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" @click="emitLog('skill', { skill_id: resource.id })">使用日志</button></td>
          </tr>
        </tbody>
      </table>
      <div v-if="skillResources.length === 0" class="py-8 text-center text-sm text-slate-400">暂无数据</div>
    </div>
  </GlassCard>
</template>
