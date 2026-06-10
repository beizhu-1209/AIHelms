<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LlmLogsTab from './tabs/LlmLogsTab.vue'
import McpLogsTab from './tabs/McpLogsTab.vue'
import SkillLogsTab from './tabs/SkillLogsTab.vue'
import AgentLogsTab from './tabs/AgentLogsTab.vue'

const route = useRoute()
const router = useRouter()

const TABS = [
  { value: 'llm', label: '模型调用', component: LlmLogsTab },
  { value: 'mcp', label: 'MCP 调用', component: McpLogsTab },
  { value: 'skill', label: 'Skill 使用', component: SkillLogsTab },
  { value: 'agent', label: '智能体使用', component: AgentLogsTab },
] as const

type TabValue = typeof TABS[number]['value']

function readTabFromUrl(): TabValue {
  const t = route.query.tab as string
  if (TABS.some((x) => x.value === t)) return t as TabValue
  return 'llm'
}

const activeTab = ref<TabValue>(readTabFromUrl())

const currentComponent = computed(() => TABS.find((t) => t.value === activeTab.value)?.component)

function switchTab(tab: TabValue): void {
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

watch(() => route.query.tab, () => {
  activeTab.value = readTabFromUrl()
})

onMounted(() => {
  if (!route.query.tab) {
    router.replace({ query: { ...route.query, tab: activeTab.value } })
  }
})
</script>

<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-slate-900">日志管理</h1>
      <p class="mt-1 text-sm text-slate-500">
        查看用户的模型 / MCP / Skill / 智能体调用记录
      </p>
    </div>

    <div class="mb-4 flex gap-1 rounded-xl bg-slate-100 p-1">
      <button
        v-for="tab in TABS"
        :key="tab.value"
        class="flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        :class="activeTab === tab.value
          ? 'bg-white text-purple-700 shadow-sm'
          : 'text-slate-600 hover:text-slate-900'"
        @click="switchTab(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>

    <component :is="currentComponent" :key="activeTab" />
  </div>
</template>
