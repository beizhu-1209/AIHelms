<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getAgentCenterV2, createResourceApplication, recordAgentUsage, toast } from '@aihelms/shared'
import type { HubAgent } from '@aihelms/shared'
import HostedIcon from '@aihelms/shared/src/components/HostedIcon.vue'
import { Bot, Search, ExternalLink } from 'lucide-vue-next'

const { t } = useI18n()

const agents = ref<HubAgent[]>([])
const myAgents = ref<number[]>([])
const isLoading = ref(true)
const search = ref('')
const categoryFilter = ref('')
const platformFilter = ref('')
const showApplyDialog = ref(false)
const applyTarget = ref<HubAgent | null>(null)
const applyReason = ref('')
const applyingId = ref<number | null>(null)

const categories = computed(() => {
  const set = new Set(agents.value.map(a => a.category).filter(Boolean))
  return Array.from(set).sort()
})

const platforms = computed(() => {
  const set = new Set(agents.value.map(a => a.platform).filter(Boolean))
  return Array.from(set).sort()
})

const filtered = computed(() => {
  return agents.value.filter(a => {
    if (categoryFilter.value && a.category !== categoryFilter.value) return false
    if (platformFilter.value && a.platform !== platformFilter.value) return false
    if (search.value) {
      const q = search.value.toLowerCase()
      if (!a.name.toLowerCase().includes(q) && !a.description?.toLowerCase().includes(q)) return false
    }
    return true
  })
})

function isOwned(agent: HubAgent): boolean {
  return myAgents.value.includes(agent.id)
}

function canDirectUse(agent: HubAgent): boolean {
  return !agent.requires_approval || isOwned(agent)
}

function handleOpen(agent: HubAgent): void {
  if (canDirectUse(agent)) {
    if (agent.chat_url) {
      recordAgentUsage(agent.id, '').catch(() => {})
      window.open(agent.chat_url, '_blank')
    }
  } else {
    applyTarget.value = agent
    applyReason.value = ''
    showApplyDialog.value = true
  }
}

async function submitApply(): Promise<void> {
  if (!applyTarget.value) return
  applyingId.value = applyTarget.value.id
  try {
    await createResourceApplication({
      resource_type: 'agent',
      resource_id: applyTarget.value.id,
      reason: applyReason.value.trim(),
    })
    toast.success(t('agent.toast.applySubmitted'))
    showApplyDialog.value = false
  } catch (e) {
    toast.error((e as { message?: string }).message || t('agent.toast.applyFailed'))
  } finally {
    applyingId.value = null
  }
}

onMounted(async () => {
  try {
    const data = await getAgentCenterV2()
    agents.value = data.agents.items ?? []
    const mainKey = data.keys.personal.main_key
    myAgents.value = mainKey?.agents ?? []
  } catch { /* */ }
  finally { isLoading.value = false }
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-6 py-8">
    <div class="mb-6">
      <h1 class="text-xl font-bold text-slate-900">{{ t('agent.title') }}</h1>
      <p class="mt-1 text-sm text-slate-500">{{ t('agent.subtitle') }}</p>
    </div>

    <!-- 筛选 -->
    <div class="mb-5 space-y-3">
      <div class="relative">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input v-model="search" type="text" :placeholder="t('agent.search.placeholder')"
          class="h-10 w-full max-w-md rounded-lg border border-slate-200/60 bg-white/70 pl-9 pr-3 text-sm backdrop-blur placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
      </div>
      <div class="flex flex-wrap gap-2">
        <button @click="categoryFilter = ''"
          class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
          :class="!categoryFilter ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'">
          {{ t('agent.filter.all') }}
        </button>
        <button v-for="cat in categories" :key="cat" @click="categoryFilter = cat"
          class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
          :class="categoryFilter === cat ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'">
          {{ cat }}
        </button>
      </div>
      <div v-if="platforms.length > 1" class="flex flex-wrap gap-2">
        <span class="text-xs text-slate-400 leading-6">{{ t('agent.filter.platform') }}</span>
        <button @click="platformFilter = ''"
          class="rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors"
          :class="!platformFilter ? 'bg-blue-100 text-blue-700' : 'bg-slate-50 text-slate-500 hover:bg-slate-100'">
          {{ t('agent.filter.all') }}
        </button>
        <button v-for="p in platforms" :key="p" @click="platformFilter = p"
          class="rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors"
          :class="platformFilter === p ? 'bg-blue-100 text-blue-700' : 'bg-slate-50 text-slate-500 hover:bg-slate-100'">
          {{ p }}
        </button>
      </div>
    </div>

    <!-- 卡片 -->
    <div v-if="isLoading" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="i in 6" :key="i" class="h-48 animate-pulse rounded-2xl bg-white/70" />
    </div>
    <div v-else-if="!filtered.length" class="rounded-2xl border border-slate-200/60 bg-white/70 p-12 text-center backdrop-blur">
      <Bot class="mx-auto h-10 w-10 text-slate-300" />
      <p class="mt-3 text-sm text-slate-400">{{ t('agent.empty') }}</p>
    </div>
    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="agent in filtered" :key="agent.id"
        class="group flex min-h-[180px] cursor-pointer flex-col rounded-2xl border border-slate-200/60 bg-white/70 p-5 backdrop-blur transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-500/5"
        @click="handleOpen(agent)"
      >
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-purple-100 to-blue-100">
            <HostedIcon :src="agent.icon_url" :size="20" :alt="agent.name" />
          </div>
          <div class="min-w-0 flex-1">
            <h3 class="truncate text-sm font-semibold text-slate-900">{{ agent.name }}</h3>
            <p class="truncate text-xs text-slate-400">{{ agent.platform }}</p>
          </div>
          <ExternalLink v-if="canDirectUse(agent) && agent.chat_url" class="h-4 w-4 shrink-0 text-slate-300 opacity-0 transition-opacity group-hover:opacity-100" />
          <span v-else-if="!canDirectUse(agent)" class="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-600">{{ t('agent.badge.requiresApproval') }}</span>
        </div>

        <div v-if="agent.tags?.length" class="mt-3 flex flex-wrap gap-1.5">
          <span v-for="tag in agent.tags.slice(0, 3)" :key="tag"
            class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{{ tag }}</span>
        </div>

        <p class="mt-2.5 flex-1 text-xs leading-relaxed text-slate-500 line-clamp-3">{{ agent.description || t('agent.fallback.noDescription') }}</p>

        <div class="mt-3 flex items-center gap-3 text-xs text-slate-400">
          <span v-if="agent.status === 'online'" class="flex items-center gap-1">
            <span class="h-1.5 w-1.5 rounded-full bg-green-500" />
            {{ t('agent.status.online') }}
          </span>
          <span v-else class="flex items-center gap-1">
            <span class="h-1.5 w-1.5 rounded-full bg-slate-300" />
            {{ t('agent.status.offline') }}
          </span>
          <span v-if="agent.user_count">{{ t('agent.usage.people', { count: agent.user_count }) }}</span>
        </div>
      </div>
    </div>

    <!-- 申请对话框 -->
    <Teleport to="body">
      <div v-if="showApplyDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" @click.self="showApplyDialog = false">
        <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
          <h3 class="text-lg font-semibold text-slate-900">{{ t('agent.apply.title') }}</h3>
          <p class="mt-1 text-sm text-slate-500">{{ applyTarget?.name }}</p>
          <textarea
            v-model="applyReason"
            rows="3"
            :placeholder="t('agent.apply.placeholder')"
            class="mt-4 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-purple-500 focus:outline-none"
          />
          <div class="mt-4 flex justify-end gap-3">
            <button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showApplyDialog = false">{{ t('common.action.cancel') }}</button>
            <button
              class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
              :disabled="applyingId !== null"
              @click="submitApply"
            >
              {{ applyingId ? t('agent.apply.submitting') : t('agent.apply.submit') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
