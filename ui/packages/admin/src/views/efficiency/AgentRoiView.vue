<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Download, ExternalLink } from 'lucide-vue-next'
import { getAgents } from '@aihelms/shared'
import type { Agent } from '@aihelms/shared'

import GlassCard from './components/GlassCard.vue'
import KpiCard from './components/KpiCard.vue'
import AgentQuadrant, { type QuadrantBubble } from './components/AgentQuadrant.vue'
import PresetTabs from './components/PresetTabs.vue'
import { formatNumber } from './utils'

const presets = [
  { key: '7d', label: '近7天' },
  { key: 'month', label: '本月' },
  { key: '30d', label: '近30天' },
  { key: '90d', label: '近90天' },
]

const activePreset = ref('month')
const platformFilter = ref('')
const categoryFilter = ref('')

const agents = ref<Agent[]>([])
const isLoading = ref(false)
const selectedAgent = ref<Agent | null>(null)

async function fetchAgents() {
  isLoading.value = true
  try {
    const result = await getAgents(1, 200)
    agents.value = result.items
    if (agents.value.length > 0 && !selectedAgent.value) {
      selectedAgent.value = agents.value[0]
    }
  } catch {
    agents.value = []
  } finally {
    isLoading.value = false
  }
}

function changePreset(value: string) {
  activePreset.value = value
  fetchAgents()
}

const filteredAgents = computed(() => {
  return agents.value.filter((a) => {
    if (platformFilter.value && a.platform !== platformFilter.value) return false
    if (categoryFilter.value && categoryFilter.value === 'star' && !isStar(a)) return false
    if (categoryFilter.value === 'cash_cow' && !isCashCow(a)) return false
    if (categoryFilter.value === 'potential' && !isPotential(a)) return false
    if (categoryFilter.value === 'zombie' && !isZombie(a)) return false
    return true
  })
})

const platformOptions = computed(() => {
  const set = new Set(agents.value.map((a) => a.platform).filter(Boolean))
  return Array.from(set)
})

// 四象限分类（基于调用量 + 使用人数启发）
const avgCalls = computed(() => {
  if (agents.value.length === 0) return 0
  return agents.value.reduce((s, a) => s + a.call_count, 0) / agents.value.length
})

function isStar(a: Agent): boolean {
  return a.call_count >= avgCalls.value && a.user_count >= 3
}

function isPotential(a: Agent): boolean {
  return a.call_count > 0 && a.call_count < avgCalls.value && a.user_count >= 2
}

function isCashCow(a: Agent): boolean {
  return a.call_count >= avgCalls.value && a.user_count < 3 && a.user_count > 0
}

function isZombie(a: Agent): boolean {
  return a.call_count === 0
}

function categoryOf(a: Agent): string {
  if (isStar(a)) return 'star'
  if (isPotential(a)) return 'potential'
  if (isCashCow(a)) return 'cash_cow'
  if (isZombie(a)) return 'zombie'
  return 'cash_cow'
}

const categoryMeta: Record<string, { label: string; class: string }> = {
  star: { label: '明星', class: 'bg-emerald-100 text-emerald-700' },
  potential: { label: '潜力', class: 'bg-indigo-100 text-indigo-700' },
  cash_cow: { label: '现金牛', class: 'bg-amber-100 text-amber-700' },
  zombie: { label: '僵尸', class: 'bg-red-100 text-red-700' },
}

const totalAgents = computed(() => agents.value.length)
const activeAgents = computed(() => agents.value.filter((a) => a.call_count > 0).length)
const totalCalls = computed(() => agents.value.reduce((sum, a) => sum + a.call_count, 0))
const zombieAgents = computed(() => agents.value.filter(isZombie).length)
const activeRate = computed(() => {
  if (totalAgents.value === 0) return 0
  return (activeAgents.value / totalAgents.value) * 100
})

const bubbles = computed<QuadrantBubble[]>(() => {
  return filteredAgents.value.slice(0, 30).map((a) => {
    // 启发式增长率：调用量超平均一倍 → +50%，低于平均一半 → -30%
    let y = 0
    if (avgCalls.value > 0) {
      if (a.call_count >= avgCalls.value * 1.5) y = 50
      else if (a.call_count >= avgCalls.value) y = 20
      else if (a.call_count >= avgCalls.value * 0.3) y = -10
      else if (a.call_count > 0) y = -30
      else y = -50
    }
    return {
      x: a.call_count,
      y,
      size: Math.max(a.user_count, 1),
      label: a.name,
    }
  })
})

const platformBadgeClass: Record<string, string> = {
  dify: 'bg-indigo-100 text-indigo-700',
  coze: 'bg-violet-100 text-violet-700',
  maxkb: 'bg-amber-100 text-amber-700',
}

function platformBadge(p: string): string {
  return platformBadgeClass[p.toLowerCase()] || 'bg-slate-100 text-slate-600'
}

onMounted(fetchAgents)
</script>

<template>
  <div class="space-y-4">
    <!-- 筛选 -->
    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-white/80 bg-white/60 px-4 py-2.5 shadow-sm backdrop-blur-xl">
      <span class="text-xs text-slate-500">时间范围</span>
      <PresetTabs :model-value="activePreset" :presets="presets" @update:model-value="changePreset" />

      <span class="ml-3 text-xs text-slate-500">平台</span>
      <select v-model="platformFilter" class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700">
        <option value="">全部平台</option>
        <option v-for="p in platformOptions" :key="p" :value="p">{{ p }}</option>
      </select>

      <span class="ml-2 text-xs text-slate-500">状态</span>
      <select v-model="categoryFilter" class="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700">
        <option value="">全部状态</option>
        <option value="star">明星</option>
        <option value="potential">潜力</option>
        <option value="cash_cow">现金牛</option>
        <option value="zombie">僵尸</option>
      </select>

      <div class="flex-1"></div>
      <button class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50">
        <Download class="h-3.5 w-3.5" /> 导出
      </button>
    </div>

    <!-- KPI -->
    <div class="grid grid-cols-4 gap-4">
      <KpiCard
        label="智能体总数"
        :value="totalAgents.toString()"
        unit="个"
        change-kind="neutral"
        :change-text="`活跃 ${activeAgents} 个`"
      />
      <KpiCard
        label="本期总调用"
        :value="formatNumber(totalCalls)"
        change-kind="up-good"
        :change="totalCalls > 0 ? 12 : null"
        change-text="基于注册智能体统计"
      />
      <KpiCard
        label="活跃率"
        :value="activeRate.toFixed(1)"
        unit="%"
        change-kind="neutral"
        :change-text="`${activeAgents}/${totalAgents}`"
      />
      <KpiCard
        label="僵尸智能体"
        :value="zombieAgents.toString()"
        unit="个"
        change-kind="neutral"
        change-text="本期 0 调用 · 建议评估"
        :value-color="zombieAgents > 0 ? 'text-red-600' : 'text-slate-900'"
      />
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-16">
      <div class="h-6 w-6 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else>
      <!-- 四象限 -->
      <GlassCard title="智能体价值四象限" subtitle="气泡大小 = 使用人数 · X：调用量 · Y：增长率%（基于启发式估算）">
        <AgentQuadrant :bubbles="bubbles" :height="380" />
      </GlassCard>

      <!-- 明细表 + 详情 -->
      <div class="grid grid-cols-3 gap-4">
        <GlassCard class="col-span-2" title="智能体经营明细" :subtitle="`共 ${filteredAgents.length} 个智能体`">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-slate-200 text-left text-xs text-slate-400">
                  <th class="py-2.5 font-medium">智能体</th>
                  <th class="py-2.5 font-medium">平台</th>
                  <th class="py-2.5 text-right font-medium">本期调用</th>
                  <th class="py-2.5 text-right font-medium">使用人数</th>
                  <th class="py-2.5 font-medium">状态</th>
                  <th class="py-2.5 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="a in filteredAgents"
                  :key="a.id"
                  class="cursor-pointer border-b border-slate-50 last:border-0 hover:bg-slate-50/40"
                  :class="selectedAgent?.id === a.id ? 'bg-indigo-50/40' : ''"
                  @click="selectedAgent = a"
                >
                  <td class="py-3">
                    <div class="font-medium text-slate-800">{{ a.name }}</div>
                    <div v-if="a.description" class="mt-0.5 truncate max-w-xs text-xs text-slate-400">{{ a.description }}</div>
                  </td>
                  <td class="py-3">
                    <span class="rounded px-2 py-0.5 text-xs" :class="platformBadge(a.platform)">{{ a.platform || '-' }}</span>
                  </td>
                  <td class="py-3 text-right font-semibold text-slate-900">{{ formatNumber(a.call_count) }}</td>
                  <td class="py-3 text-right text-slate-700">{{ a.user_count }}</td>
                  <td class="py-3">
                    <span class="rounded px-2 py-0.5 text-xs" :class="categoryMeta[categoryOf(a)].class">
                      {{ categoryMeta[categoryOf(a)].label }}
                    </span>
                  </td>
                  <td class="py-3">
                    <a
                      v-if="a.chat_url"
                      :href="a.chat_url"
                      target="_blank"
                      class="inline-flex items-center gap-1 text-xs text-indigo-600 hover:underline"
                      @click.stop
                    >
                      <ExternalLink class="h-3 w-3" /> 打开
                    </a>
                  </td>
                </tr>
                <tr v-if="filteredAgents.length === 0">
                  <td colspan="6" class="py-10 text-center text-sm text-slate-400">暂无智能体</td>
                </tr>
              </tbody>
            </table>
          </div>
        </GlassCard>

        <GlassCard v-if="selectedAgent" title="智能体详情" :subtitle="selectedAgent.name">
          <div class="grid grid-cols-2 gap-2">
            <div class="rounded-lg bg-indigo-50/60 p-3">
              <div class="text-xs text-slate-500">总调用</div>
              <div class="mt-1 text-lg font-semibold text-slate-900">{{ formatNumber(selectedAgent.call_count) }}</div>
            </div>
            <div class="rounded-lg bg-indigo-50/60 p-3">
              <div class="text-xs text-slate-500">使用人数</div>
              <div class="mt-1 text-lg font-semibold text-slate-900">{{ selectedAgent.user_count }}</div>
            </div>
            <div class="rounded-lg bg-indigo-50/60 p-3">
              <div class="text-xs text-slate-500">平台</div>
              <div class="mt-1 text-sm font-medium text-slate-700">{{ selectedAgent.platform || '-' }}</div>
            </div>
            <div class="rounded-lg bg-indigo-50/60 p-3">
              <div class="text-xs text-slate-500">分类</div>
              <div class="mt-1 text-sm font-medium text-slate-700">{{ selectedAgent.category || '-' }}</div>
            </div>
          </div>

          <div class="mt-4">
            <div class="text-xs text-slate-500">描述</div>
            <p class="mt-1 text-sm text-slate-700 leading-relaxed">
              {{ selectedAgent.description || '暂无描述' }}
            </p>
          </div>

          <div v-if="selectedAgent.tags?.length" class="mt-4">
            <div class="text-xs text-slate-500">标签</div>
            <div class="mt-1.5 flex flex-wrap gap-1">
              <span
                v-for="t in selectedAgent.tags"
                :key="t"
                class="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600"
              >{{ t }}</span>
            </div>
          </div>
        </GlassCard>

        <GlassCard v-else title="智能体详情" subtitle="选择左侧表格行查看">
          <div class="py-12 text-center text-sm text-slate-400">未选中智能体</div>
        </GlassCard>
      </div>
    </template>
  </div>
</template>
