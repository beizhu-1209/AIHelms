<script setup lang="ts">
import { computed, ref, toRefs, watch } from 'vue'
import { ChevronRight, Download } from 'lucide-vue-next'
import GlassCard from './GlassCard.vue'
import TooltipIcon from '../../../components/TooltipIcon.vue'
import Pagination from '../../../components/Pagination.vue'
import { formatCost, formatNumber, formatChange } from '../utils'
import type { AttributionRow, DateDetailRow, DetailTab, McpDetailRow, McpToolRow, ModelCredentialRow, ModelDetailRow, ScopeDetailRow, ScopeUserCostRow } from '../costTypes'

const props = defineProps<{
  activeDetailTab: DetailTab
  detailTabs: { key: DetailTab; label: string }[]
  isDetailLoading: boolean
  exporting: boolean
  dimensionLabel: string
  scopeDetail: ScopeDetailRow[]
  modelDetail: ModelDetailRow[]
  mcpDetail: McpDetailRow[]
  dateDetail: DateDetailRow[]
  attributionDetail: AttributionRow[]
  expandedScopeId: number | null
  scopeUsers: ScopeUserCostRow[]
  scopeUsersLoading: boolean
}>()

const emit = defineEmits<{
  tabChange: [tab: DetailTab]
  exportDetail: []
  toggleScopeUsers: [row: ScopeDetailRow]
  openModelLogs: [row: ModelDetailRow]
  openModelCredentialLogs: [row: ModelCredentialRow]
  openMcpLogs: [row: McpDetailRow]
  openMcpToolLogs: [row: McpDetailRow, tool: McpToolRow]
  openDateLogs: [tab: 'llm' | 'mcp', date: string]
  openAttributionLogs: [row: AttributionRow]
}>()

const { activeDetailTab, detailTabs, isDetailLoading, exporting, dimensionLabel, scopeDetail, modelDetail, mcpDetail, dateDetail, attributionDetail, expandedScopeId, scopeUsers, scopeUsersLoading } = toRefs(props)
const pageSize = ref(20)
const detailPage = ref(1)
watch(pageSize, () => { detailPage.value = 1 })
const expandedModelRows = ref<Set<string>>(new Set())
const expandedMcpRows = ref<Set<string>>(new Set())

watch(activeDetailTab, () => { detailPage.value = 1 })

const activeRows = computed(() => {
  if (activeDetailTab.value === 'model') return modelDetail.value
  if (activeDetailTab.value === 'mcp') return mcpDetail.value
  if (activeDetailTab.value === 'date') return dateDetail.value
  if (activeDetailTab.value === 'attribution') return attributionDetail.value
  return scopeDetail.value
})
const pageStart = computed(() => (detailPage.value - 1) * pageSize.value)
const pagedScopeDetail = computed(() => scopeDetail.value.slice(pageStart.value, pageStart.value + pageSize.value))
const pagedModelDetail = computed(() => modelDetail.value.slice(pageStart.value, pageStart.value + pageSize.value))
const pagedMcpDetail = computed(() => mcpDetail.value.slice(pageStart.value, pageStart.value + pageSize.value))
const pagedDateDetail = computed(() => dateDetail.value.slice(pageStart.value, pageStart.value + pageSize.value))
const pagedAttributionDetail = computed(() => attributionDetail.value.slice(pageStart.value, pageStart.value + pageSize.value))

function handleDetailTabChange(tab: DetailTab) { emit('tabChange', tab) }
function exportDetail() { emit('exportDetail') }
function toggleScopeUsers(row: ScopeDetailRow) { if (row.scope_id !== null) emit('toggleScopeUsers', row) }
function openModelLogs(row: ModelDetailRow) { emit('openModelLogs', row) }
function openModelCredentialLogs(row: ModelCredentialRow) { emit('openModelCredentialLogs', row) }
function openMcpLogs(row: McpDetailRow) { emit('openMcpLogs', row) }
function openMcpToolLogs(row: McpDetailRow, tool: McpToolRow) { emit('openMcpToolLogs', row, tool) }
function openDateLogs(tab: 'llm' | 'mcp', date: string) { emit('openDateLogs', tab, date) }
function openAttributionLogs(row: AttributionRow) { emit('openAttributionLogs', row) }

function formatTokenCount(value: number | null | undefined): string {
  return Math.round(value || 0).toLocaleString()
}
function formatTokenBreakdown(row: { input_tokens: number; output_tokens: number; cache_read_tokens: number; cache_creation_tokens: number }): string {
  return `${formatTokenCount(row.input_tokens)} / ${formatTokenCount(row.output_tokens)} / ${formatTokenCount(row.cache_read_tokens)} / ${formatTokenCount(row.cache_creation_tokens)}`
}
function formatResourceName(name: string): string {
  if (name === 'llm') return 'LLM'
  if (name === 'mcp') return 'MCP'
  return name
}
function modelRowKey(row: ModelDetailRow): string { return row.model_id || row.model }
function isModelExpanded(row: ModelDetailRow): boolean { return expandedModelRows.value.has(modelRowKey(row)) }
function toggleModelExpanded(row: ModelDetailRow) {
  const next = new Set(expandedModelRows.value)
  const key = modelRowKey(row)
  next.has(key) ? next.delete(key) : next.add(key)
  expandedModelRows.value = next
}
function credentialDisplay(row: ModelCredentialRow): string {
  const provider = row.provider_name && row.provider_name !== '--' ? row.provider_name : row.provider_type
  return `${provider || '--'} / ${row.credential_name || '--'}`
}
function mcpRowKey(row: McpDetailRow): string { return String(row.server_id || row.server) }
function isMcpExpanded(row: McpDetailRow): boolean { return expandedMcpRows.value.has(mcpRowKey(row)) }
function toggleMcpExpanded(row: McpDetailRow) {
  const next = new Set(expandedMcpRows.value)
  const key = mcpRowKey(row)
  next.has(key) ? next.delete(key) : next.add(key)
  expandedMcpRows.value = next
}
</script>

<template>
      <GlassCard>
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-1">
            <span class="text-sm font-semibold text-slate-900">成本明细</span>
            <TooltipIcon text="明细随顶部时间、资源类型和归属维度联动。成本流水用于按日期、资源对象、使用人、AI Key和归属维度对账；Token数为实际Token数量。" />
          </div>
          <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" :disabled="exporting" @click="exportDetail">
            <Download class="h-3.5 w-3.5" /> {{ exporting ? '导出中' : '导出' }}
          </button>
        </div>

        <div class="mb-3 flex gap-1 rounded-lg bg-slate-100 p-1">
          <button v-for="tab in detailTabs" :key="tab.key" class="rounded-md px-3 py-1.5 text-xs transition-colors" :class="activeDetailTab === tab.key ? 'bg-white font-medium text-blue-700 shadow-sm' : 'text-slate-600 hover:bg-slate-50'" @click="handleDetailTabChange(tab.key)">{{ tab.label }}</button>
        </div>

        <div v-if="isDetailLoading" class="flex items-center justify-center py-10">
          <div class="h-6 w-6 animate-spin rounded-full border-3 border-blue-500 border-t-transparent"></div>
        </div>

        <div v-else>
          <div class="max-h-[520px] overflow-auto">
            <table v-if="activeDetailTab === 'department'" class="min-w-[1320px] w-full text-sm">
              <thead class="sticky top-0 z-10 bg-white">
                <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                  <th class="py-2.5 font-medium">{{ dimensionLabel }}</th>
                  <th class="py-2.5 text-right font-medium">LLM内部成本</th>
                  <th class="py-2.5 text-right font-medium">MCP内部成本</th>
                  <th class="py-2.5 text-right font-medium">内部总成本</th>
                  <th class="py-2.5 text-right font-medium">外部总成本</th>
                  <th class="py-2.5 text-right font-medium">差额</th>
                  <th class="py-2.5 text-right font-medium">请求数</th>
                  <th class="py-2.5 text-right font-medium">
                    <div>Token</div>
                    <div class="text-[10px] font-normal text-slate-300">输入/输出/缓存命中/缓存创建</div>
                  </th>
                  <th class="py-2.5 text-right font-medium">人均成本</th>
                  <th class="py-2.5 text-right font-medium">活跃人均成本</th>
                  <th class="py-2.5 text-right font-medium">内部总成本环比</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="row in pagedScopeDetail" :key="row.scope_name || row.department">
                  <tr class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                    <td class="py-3 font-medium text-slate-800">
                      <button
                        type="button"
                        class="inline-flex items-center gap-1 text-left hover:text-blue-700"
                        :class="row.scope_id !== null ? 'cursor-pointer' : 'cursor-default'"
                        @click="toggleScopeUsers(row)"
                      >
                        <ChevronRight class="h-3.5 w-3.5 shrink-0 transition-transform" :class="expandedScopeId === row.scope_id ? 'rotate-90' : ''" />
                        <span>{{ row.scope_name || row.department }}</span>
                      </button>
                    </td>
                    <td class="py-3 text-right text-slate-700">{{ formatCost(row.llm_cost) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatCost(row.mcp_cost) }}</td>
                    <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.total_cost) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatCost(row.external_cost) }}</td>
                    <td class="py-3 text-right" :class="row.cost_diff >= 0 ? 'text-emerald-600' : 'text-red-500'">{{ formatCost(row.cost_diff) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatNumber(row.requests) }}</td>
                    <td class="py-3 text-right text-slate-600 whitespace-nowrap">{{ formatTokenBreakdown(row) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatCost(row.per_capita_cost) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatCost(row.active_per_capita_cost) }}</td>
                    <td class="py-3 text-right" :class="row.cost_change !== null && row.cost_change > 0 ? 'text-red-500' : 'text-emerald-600'">{{ formatChange(row.cost_change) }}</td>
                  </tr>
                  <tr v-if="expandedScopeId === row.scope_id" class="border-b border-slate-100 bg-slate-50/60">
                    <td colspan="11" class="px-4 py-3">
                      <div v-if="scopeUsersLoading" class="py-6 text-center text-sm text-slate-400">加载中...</div>
                      <table v-else class="w-full text-xs">
                        <thead class="text-slate-400">
                          <tr class="text-left">
                            <th class="py-1.5 font-medium">姓名</th>
                            <th class="py-1.5 font-medium">部门</th>
                            <th class="py-1.5 text-right font-medium">内部成本</th>
                            <th class="py-1.5 text-right font-medium">外部成本</th>
                            <th class="py-1.5 text-right font-medium">差额</th>
                            <th class="py-1.5 text-right font-medium">请求数</th>
                            <th class="py-1.5 text-right font-medium">
                              <div>Token</div>
                              <div class="text-[10px] font-normal text-slate-300">输入/输出/缓存命中/缓存创建</div>
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="user in scopeUsers" :key="user.user_id" class="border-t border-slate-200/70">
                            <td class="py-2 font-medium text-slate-800">{{ user.user_name }}</td>
                            <td class="py-2 text-slate-500">{{ user.department || '-' }}</td>
                            <td class="py-2 text-right font-medium text-slate-800">{{ formatCost(user.internal_cost) }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatCost(user.external_cost) }}</td>
                            <td class="py-2 text-right" :class="user.cost_diff >= 0 ? 'text-emerald-600' : 'text-red-500'">{{ formatCost(user.cost_diff) }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatNumber(user.requests) }}</td>
                            <td class="py-2 text-right text-slate-600 whitespace-nowrap">{{ formatTokenBreakdown(user) }}</td>
                          </tr>
                          <tr v-if="scopeUsers.length === 0"><td colspan="7" class="py-6 text-center text-slate-400">暂无人员明细</td></tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                </template>
                <tr v-if="scopeDetail.length === 0"><td colspan="11" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
              </tbody>
            </table>

            <table v-else-if="activeDetailTab === 'model'" class="min-w-[1120px] w-full text-sm">
              <thead class="sticky top-0 z-10 bg-white">
                <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                  <th class="py-2.5 font-medium">模型</th>
                  <th class="py-2.5 text-right font-medium">请求数</th>
                  <th class="py-2.5 text-right font-medium">Token数</th>
                  <th class="py-2.5 text-right font-medium">缓存读</th>
                  <th class="py-2.5 text-right font-medium">缓存写</th>
                  <th class="py-2.5 text-right font-medium">内部成本</th>
                  <th class="py-2.5 text-right font-medium">外部成本</th>
                  <th class="py-2.5 text-right font-medium">差额</th>
                  <th class="py-2.5 text-right font-medium">占比</th>
                  <th class="py-2.5 text-right font-medium">均次成本</th>
                  <th class="py-2.5 text-right font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="row in pagedModelDetail" :key="modelRowKey(row)">
                  <tr class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                    <td class="py-3 font-medium text-slate-800">
                      <button
                        type="button"
                        class="inline-flex max-w-[260px] items-center gap-1 text-left hover:text-blue-700"
                        :class="row.credentials?.length ? 'cursor-pointer' : 'cursor-default'"
                        @click="row.credentials?.length && toggleModelExpanded(row)"
                      >
                        <ChevronRight class="h-3.5 w-3.5 shrink-0 transition-transform" :class="isModelExpanded(row) ? 'rotate-90' : ''" />
                        <span class="truncate" :title="row.model">{{ row.model }}</span>
                      </button>
                      <div class="ml-5 mt-0.5 truncate text-[11px] font-normal text-slate-400" :title="row.model_id">{{ row.model_id }}</div>
                    </td>
                    <td class="py-3 text-right text-slate-700">{{ formatNumber(row.requests) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatTokenCount(row.tokens) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatTokenCount(row.cache_read_tokens) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatTokenCount(row.cache_creation_tokens) }}</td>
                    <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.internal_cost) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatCost(row.external_cost) }}</td>
                    <td class="py-3 text-right" :class="row.cost_diff >= 0 ? 'text-emerald-600' : 'text-red-500'">{{ formatCost(row.cost_diff) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ (row.ratio * 100).toFixed(1) }}%</td>
                    <td class="py-3 text-right text-slate-700">{{ formatCost(row.avg_cost) }}</td>
                    <td class="py-3 text-right"><button class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 hover:bg-slate-50" @click="openModelLogs(row)">日志</button></td>
                  </tr>
                  <tr v-if="isModelExpanded(row)" class="border-b border-slate-100 bg-slate-50/60">
                    <td colspan="11" class="px-4 py-3">
                      <table class="w-full text-xs">
                        <thead class="text-slate-400">
                          <tr class="text-left">
                            <th class="py-1.5 font-medium">凭证</th>
                            <th class="py-1.5 font-medium">路由模型</th>
                            <th class="py-1.5 text-right font-medium">请求数</th>
                            <th class="py-1.5 text-right font-medium">Token数</th>
                            <th class="py-1.5 text-right font-medium">缓存读</th>
                            <th class="py-1.5 text-right font-medium">缓存写</th>
                            <th class="py-1.5 text-right font-medium">内部成本</th>
                            <th class="py-1.5 text-right font-medium">外部成本</th>
                            <th class="py-1.5 text-right font-medium">差额</th>
                            <th class="py-1.5 text-right font-medium">均次成本</th>
                            <th class="py-1.5 text-right font-medium">操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="credential in row.credentials" :key="`${modelRowKey(row)}-${credential.credential_id}-${credential.route_model}`" class="border-t border-slate-200/70">
                            <td class="py-2 text-slate-700">
                              <div class="font-medium text-slate-800">{{ credentialDisplay(credential) }}</div>
                              <div v-if="credential.deployment_name" class="mt-0.5 text-slate-400">{{ credential.deployment_name }}</div>
                            </td>
                            <td class="py-2 text-slate-600">{{ credential.route_model }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatNumber(credential.requests) }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatTokenCount(credential.tokens) }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatTokenCount(credential.cache_read_tokens) }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatTokenCount(credential.cache_creation_tokens) }}</td>
                            <td class="py-2 text-right font-medium text-slate-800">{{ formatCost(credential.internal_cost) }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatCost(credential.external_cost) }}</td>
                            <td class="py-2 text-right" :class="credential.cost_diff >= 0 ? 'text-emerald-600' : 'text-red-500'">{{ formatCost(credential.cost_diff) }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatCost(credential.avg_cost) }}</td>
                            <td class="py-2 text-right"><button class="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-600 hover:bg-slate-50" @click="openModelCredentialLogs(credential)">日志</button></td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                </template>
                <tr v-if="modelDetail.length === 0"><td colspan="11" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
              </tbody>
            </table>


            <table v-else-if="activeDetailTab === 'mcp'" class="min-w-[980px] w-full text-sm">
              <thead class="sticky top-0 z-10 bg-white">
                <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                  <th class="py-2.5 font-medium">MCP服务</th>
                  <th class="py-2.5 text-right font-medium">调用数</th>
                  <th class="py-2.5 text-right font-medium">Tool数</th>
                  <th class="py-2.5 text-right font-medium">内部成本</th>
                  <th class="py-2.5 text-right font-medium">外部成本</th>
                  <th class="py-2.5 text-right font-medium">差额</th>
                  <th class="py-2.5 text-right font-medium">占比</th>
                  <th class="py-2.5 text-right font-medium">均次成本</th>
                  <th class="py-2.5 text-right font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="row in pagedMcpDetail" :key="mcpRowKey(row)">
                  <tr class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                    <td class="py-3 font-medium text-slate-800">
                      <button
                        type="button"
                        class="inline-flex max-w-[260px] items-center gap-1 text-left hover:text-blue-700"
                        :class="row.tools?.length ? 'cursor-pointer' : 'cursor-default'"
                        @click="row.tools?.length && toggleMcpExpanded(row)"
                      >
                        <ChevronRight class="h-3.5 w-3.5 shrink-0 transition-transform" :class="isMcpExpanded(row) ? 'rotate-90' : ''" />
                        <span class="truncate" :title="row.server">{{ row.server }}</span>
                      </button>
                      <div class="ml-5 mt-0.5 truncate text-[11px] font-normal text-slate-400" :title="row.server_code">{{ row.server_code }}</div>
                    </td>
                    <td class="py-3 text-right text-slate-700">{{ formatNumber(row.requests) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ row.tool_count }}</td>
                    <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.internal_cost) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ formatCost(row.external_cost) }}</td>
                    <td class="py-3 text-right" :class="row.cost_diff >= 0 ? 'text-emerald-600' : 'text-red-500'">{{ formatCost(row.cost_diff) }}</td>
                    <td class="py-3 text-right text-slate-700">{{ (row.ratio * 100).toFixed(1) }}%</td>
                    <td class="py-3 text-right text-slate-700">{{ formatCost(row.avg_cost) }}</td>
                    <td class="py-3 text-right"><button class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 hover:bg-slate-50" @click="openMcpLogs(row)">日志</button></td>
                  </tr>
                  <tr v-if="isMcpExpanded(row)" class="border-b border-slate-100 bg-slate-50/60">
                    <td colspan="9" class="px-4 py-3">
                      <table class="w-full text-xs">
                        <thead class="text-slate-400">
                          <tr class="text-left">
                            <th class="py-1.5 font-medium">Tool</th>
                            <th class="py-1.5 text-right font-medium">调用数</th>
                            <th class="py-1.5 text-right font-medium">内部成本</th>
                            <th class="py-1.5 text-right font-medium">外部成本</th>
                            <th class="py-1.5 text-right font-medium">差额</th>
                            <th class="py-1.5 text-right font-medium">均次成本</th>
                            <th class="py-1.5 text-right font-medium">操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="tool in row.tools" :key="`${mcpRowKey(row)}-${tool.namespaced_tool_name || tool.tool_name}`" class="border-t border-slate-200/70">
                            <td class="py-2 font-medium text-slate-800">{{ tool.tool_name }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatNumber(tool.requests) }}</td>
                            <td class="py-2 text-right font-medium text-slate-800">{{ formatCost(tool.internal_cost) }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatCost(tool.external_cost) }}</td>
                            <td class="py-2 text-right" :class="tool.cost_diff >= 0 ? 'text-emerald-600' : 'text-red-500'">{{ formatCost(tool.cost_diff) }}</td>
                            <td class="py-2 text-right text-slate-600">{{ formatCost(tool.avg_cost) }}</td>
                            <td class="py-2 text-right"><button class="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-600 hover:bg-slate-50" @click="openMcpToolLogs(row, tool)">日志</button></td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                </template>
                <tr v-if="mcpDetail.length === 0"><td colspan="9" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
              </tbody>
            </table>

            <table v-else-if="activeDetailTab === 'attribution'" class="min-w-[2320px] w-full text-sm">
              <thead class="sticky top-0 z-10 bg-white">
                <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                  <th class="py-2.5 font-medium">日期</th>
                  <th class="py-2.5 font-medium">资源类型</th>
                  <th class="py-2.5 font-medium">成本对象</th>
                  <th class="py-2.5 font-medium">使用人</th>
                  <th class="py-2.5 font-medium">AI Key</th>
                  <th class="py-2.5 font-medium">归属{{ dimensionLabel }}</th>
                  <th class="py-2.5 text-right font-medium">调用数</th>
                  <th class="py-2.5 text-right font-medium">输入Token</th>
                  <th class="py-2.5 text-right font-medium">输出Token</th>
                  <th class="py-2.5 text-right font-medium">缓存命中Token</th>
                  <th class="py-2.5 text-right font-medium">缓存创建Token</th>
                  <th class="py-2.5 text-right font-medium">内部输入</th>
                  <th class="py-2.5 text-right font-medium">内部输出</th>
                  <th class="py-2.5 text-right font-medium">内部缓存命中</th>
                  <th class="py-2.5 text-right font-medium">内部缓存创建</th>
                  <th class="py-2.5 text-right font-medium">内部成本</th>
                  <th class="py-2.5 text-right font-medium">外部输入</th>
                  <th class="py-2.5 text-right font-medium">外部输出</th>
                  <th class="py-2.5 text-right font-medium">外部缓存命中</th>
                  <th class="py-2.5 text-right font-medium">外部缓存创建</th>
                  <th class="py-2.5 text-right font-medium">外部成本</th>
                  <th class="py-2.5 text-right font-medium">差额</th>
                  <th class="py-2.5 text-right font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in pagedAttributionDetail" :key="`${row.date}-${row.resource_type}-${row.cost_object}-${row.user_name}-${row.key_name}`" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                  <td class="py-3 text-slate-700">{{ row.date }}</td>
                  <td class="py-3 text-slate-700">{{ formatResourceName(row.resource_type) }}</td>
                  <td class="py-3 font-medium text-slate-800">{{ row.cost_object }}</td>
                  <td class="py-3 text-slate-700">{{ row.user_name }}</td>
                  <td class="py-3 text-slate-700">{{ row.key_name }}</td>
                  <td class="py-3 text-slate-700">{{ row.scope_name }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatNumber(row.requests) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatTokenCount(row.input_tokens) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatTokenCount(row.output_tokens) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatTokenCount(row.cache_read_tokens) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatTokenCount(row.cache_creation_tokens) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.internal_input_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.internal_output_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.internal_cache_read_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.internal_cache_creation_cost) }}</td>
                  <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.internal_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.external_input_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.external_output_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.external_cache_read_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.external_cache_creation_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.external_cost) }}</td>
                  <td class="py-3 text-right" :class="row.cost_diff >= 0 ? 'text-emerald-600' : 'text-red-500'">{{ formatCost(row.cost_diff) }}</td>
                  <td class="py-3 text-right"><button class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 hover:bg-slate-50" @click="openAttributionLogs(row)">日志</button></td>
                </tr>
                <tr v-if="attributionDetail.length === 0"><td colspan="23" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
              </tbody>
            </table>

            <table v-else class="min-w-[980px] w-full text-sm">
              <thead class="sticky top-0 z-10 bg-white">
                <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                  <th class="py-2.5 font-medium">日期</th>
                  <th class="py-2.5 text-right font-medium">LLM内部成本</th>
                  <th class="py-2.5 text-right font-medium">MCP内部成本</th>
                  <th class="py-2.5 text-right font-medium">内部总成本</th>
                  <th class="py-2.5 text-right font-medium">外部总成本</th>
                  <th class="py-2.5 text-right font-medium">差额</th>
                  <th class="py-2.5 text-right font-medium">请求数</th>
                  <th class="py-2.5 text-right font-medium">活跃用户</th>
                  <th class="py-2.5 text-right font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in pagedDateDetail" :key="row.date" class="border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
                  <td class="py-3 font-medium text-slate-800">{{ row.date }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.llm_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.mcp_cost) }}</td>
                  <td class="py-3 text-right font-semibold text-slate-900">{{ formatCost(row.total_cost) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatCost(row.external_cost) }}</td>
                  <td class="py-3 text-right" :class="row.cost_diff >= 0 ? 'text-emerald-600' : 'text-red-500'">{{ formatCost(row.cost_diff) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ formatNumber(row.requests) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ row.active_users }}</td>
                  <td class="py-3 text-right"><div class="inline-flex gap-1.5"><button class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 hover:bg-slate-50" @click="openDateLogs('llm', row.date)">LLM</button><button class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 hover:bg-slate-50" @click="openDateLogs('mcp', row.date)">MCP</button></div></td>
                </tr>
                <tr v-if="dateDetail.length === 0"><td colspan="9" class="py-12 text-center text-sm text-slate-400">暂无数据</td></tr>
              </tbody>
            </table>
          </div>

          <Pagination
            v-if="activeRows.length > 0"
            :page="detailPage"
            v-model:page-size="pageSize"
            :total="activeRows.length"
            @change="detailPage = $event"
          />
        </div>
      </GlassCard>
</template>
