<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getAgents,
  getAgentCategories,
  getAgentPlatforms,
  createAgentCategory,
  deleteAgentCategory,
  createAgentPlatform,
  deleteAgentPlatform,
  type Agent,
  type AgentCategory,
  type AgentPlatform,
} from '@aihelms/shared'
import { toast, usePermission } from '@aihelms/shared'
import { Plus, X } from 'lucide-vue-next'
import HostedIcon from '@aihelms/shared/src/components/HostedIcon.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()
const router = useRouter()

const agents = ref<Agent[]>([])
const categories = ref<AgentCategory[]>([])
const platforms = ref<AgentPlatform[]>([])
const loading = ref(false)
const selectedCategory = ref<string | null>(null)
const selectedPlatform = ref<string | null>(null)

const showCategoryForm = ref(false)
const categoryFormName = ref('')
const showPlatformForm = ref(false)
const platformFormName = ref('')
const platformFormLabel = ref('')

const deleteCategoryTarget = ref<AgentCategory | null>(null)
const deletePlatformTarget = ref<AgentPlatform | null>(null)

const categoriesWithCount = computed(() => {
  const counts = new Map<string, number>()
  for (const a of agents.value) counts.set(a.category, (counts.get(a.category) || 0) + 1)
  return categories.value.map((c) => ({ ...c, count: counts.get(c.name) || 0 }))
})

const platformsWithCount = computed(() => {
  const counts = new Map<string, number>()
  for (const a of agents.value) counts.set(a.platform, (counts.get(a.platform) || 0) + 1)
  return platforms.value.map((p) => ({ ...p, count: counts.get(p.name) || 0 }))
})

const filteredAgents = computed(() => {
  return agents.value.filter((a) => {
    if (selectedCategory.value && a.category !== selectedCategory.value) return false
    if (selectedPlatform.value && a.platform !== selectedPlatform.value) return false
    return true
  })
})

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const [agentsRes, catsRes, platsRes] = await Promise.all([
      getAgents(1, 200),
      getAgentCategories(),
      getAgentPlatforms(),
    ])
    agents.value = agentsRes.items
    categories.value = catsRes
    platforms.value = platsRes
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

function openDetail(agent: Agent): void {
  router.push(`/agents/${agent.id}`)
}

function openCreate(): void {
  router.push('/agents/new')
}

async function handleCreateCategory(): Promise<void> {
  if (!categoryFormName.value.trim()) {
    toast.error('请输入分类名称')
    return
  }
  try {
    await createAgentCategory({ name: categoryFormName.value.trim() })
    toast.success('分类创建成功')
    showCategoryForm.value = false
    categoryFormName.value = ''
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建失败')
  }
}

async function handleCreatePlatform(): Promise<void> {
  if (!platformFormLabel.value.trim()) {
    toast.error('请输入平台名称')
    return
  }
  try {
    const label = platformFormLabel.value.trim()
    await createAgentPlatform({
      name: label,
      label: label,
    })
    toast.success('平台创建成功')
    showPlatformForm.value = false
    platformFormName.value = ''
    platformFormLabel.value = ''
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建失败')
  }
}

async function confirmDeleteCategory(): Promise<void> {
  if (!deleteCategoryTarget.value) return
  try {
    await deleteAgentCategory(deleteCategoryTarget.value.id)
    toast.success('分类删除成功')
    if (selectedCategory.value === deleteCategoryTarget.value.name) selectedCategory.value = null
    deleteCategoryTarget.value = null
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '删除失败')
  }
}

async function confirmDeletePlatform(): Promise<void> {
  if (!deletePlatformTarget.value) return
  try {
    await deleteAgentPlatform(deletePlatformTarget.value.id)
    toast.success('平台删除成功')
    if (selectedPlatform.value === deletePlatformTarget.value.name) selectedPlatform.value = null
    deletePlatformTarget.value = null
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '删除失败')
  }
}

function statusColor(status: string): string {
  if (status === 'online') return 'bg-green-50 text-green-600'
  if (status === 'offline') return 'bg-slate-100 text-slate-500'
  return 'bg-amber-50 text-amber-600'
}

function getPlatformLabel(name: string): string {
  return platforms.value.find((p) => p.name === name)?.label || name
}

onMounted(loadData)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">智能体管理</h1>
        <p class="mt-1 text-sm text-slate-500">纳管外部 Agent 平台（Dify / Coze / 自研等），用户通过 web 端使用</p>
      </div>
      <button
        v-if="hasPermission('agent:create')"
        class="flex items-center gap-1.5 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-purple-500"
        @click="openCreate"
      >
        <Plus class="h-4 w-4" />
        新建智能体
      </button>
    </div>

    <!-- 分类筛选条 -->
    <div class="mb-3 flex flex-wrap items-center gap-2">
      <span class="text-xs font-medium text-slate-400">分类：</span>
      <button
        class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
        :class="!selectedCategory ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
        @click="selectedCategory = null"
      >
        全部 ({{ agents.length }})
      </button>
      <div v-for="cat in categoriesWithCount" :key="cat.id" class="group flex items-center">
        <button
          class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
          :class="selectedCategory === cat.name ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          @click="selectedCategory = cat.name"
        >
          {{ cat.name }} ({{ cat.count }})
        </button>
        <button
          v-if="hasPermission('agent:delete')"
          class="ml-1 hidden text-slate-400 hover:text-red-500 group-hover:inline-block"
          @click="deleteCategoryTarget = cat"
        >
          <X class="h-3 w-3" />
        </button>
      </div>
      <button
        v-if="hasPermission('agent:create')"
        class="rounded-full border border-dashed border-slate-300 px-3 py-1 text-xs text-slate-500 hover:border-purple-500 hover:text-purple-600"
        @click="showCategoryForm = true"
      >
        + 新建分类
      </button>
    </div>

    <!-- 平台筛选条 -->
    <div class="mb-5 flex flex-wrap items-center gap-2">
      <span class="text-xs font-medium text-slate-400">平台：</span>
      <button
        class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
        :class="!selectedPlatform ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
        @click="selectedPlatform = null"
      >
        全部
      </button>
      <div v-for="plat in platformsWithCount" :key="plat.id" class="group flex items-center">
        <button
          class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
          :class="selectedPlatform === plat.name ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          @click="selectedPlatform = plat.name"
        >
          {{ plat.label }} ({{ plat.count }})
        </button>
        <button
          v-if="hasPermission('agent:delete')"
          class="ml-1 hidden text-slate-400 hover:text-red-500 group-hover:inline-block"
          @click="deletePlatformTarget = plat"
        >
          <X class="h-3 w-3" />
        </button>
      </div>
      <button
        v-if="hasPermission('agent:create')"
        class="rounded-full border border-dashed border-slate-300 px-3 py-1 text-xs text-slate-500 hover:border-blue-500 hover:text-blue-600"
        @click="showPlatformForm = true"
      >
        + 新建平台
      </button>
    </div>

    <!-- 卡片网格 -->
    <div v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中...</div>
    <div v-else-if="filteredAgents.length === 0" class="py-20 text-center text-sm text-slate-400">
      暂无智能体，点击右上角"新建智能体"开始
    </div>
    <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <div
        v-for="agent in filteredAgents"
        :key="agent.id"
        class="group cursor-pointer rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-purple-300 hover:shadow-md"
        @click="openDetail(agent)"
      >
        <div class="mb-3 flex items-start justify-between">
          <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-50 to-blue-50">
            <HostedIcon :src="agent.icon_url" :size="24" :alt="agent.name" />
          </div>
          <div class="flex flex-col items-end gap-1">
            <span class="rounded-full px-2 py-0.5 text-[10px] font-medium" :class="statusColor(agent.status)">
              {{ agent.status }}
            </span>
            <span v-if="agent.is_published" class="rounded-full bg-green-50 px-2 py-0.5 text-[10px] text-green-600">
              已发布
            </span>
            <span v-if="agent.requires_approval" class="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] text-amber-600">
              需审批
            </span>
          </div>
        </div>
        <h3 class="mb-1 truncate text-base font-semibold text-slate-900 group-hover:text-purple-700">
          {{ agent.name }}
        </h3>
        <p class="mb-3 line-clamp-2 text-xs text-slate-500" :title="agent.description">
          {{ agent.description || '无描述' }}
        </p>
        <div class="flex flex-wrap gap-1">
          <span class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-600">
            {{ getPlatformLabel(agent.platform) }}
          </span>
          <span class="rounded bg-purple-50 px-1.5 py-0.5 text-[10px] text-purple-600">
            {{ agent.category }}
          </span>
          <span v-for="tag in agent.tags.slice(0, 2)" :key="tag" class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
            {{ tag }}
          </span>
        </div>
      </div>
    </div>

    <!-- 新建分类弹窗 -->
    <div
      v-if="showCategoryForm"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
    >
      <div class="w-full max-w-sm rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">新建分类</h3>
        <input
          v-model="categoryFormName"
          class="mb-4 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          placeholder="如：office / customer / hr"
        />
        <div class="flex justify-end gap-3">
          <button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showCategoryForm = false">取消</button>
          <button class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700" @click="handleCreateCategory">创建</button>
        </div>
      </div>
    </div>

    <!-- 新建平台弹窗 -->
    <div
      v-if="showPlatformForm"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
    >
      <div class="w-full max-w-sm rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">新建平台</h3>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-slate-700">平台名称</label>
          <input
            v-model="platformFormLabel"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="如：Dify / Coze / 自研"
          />
        </div>
        <div class="flex justify-end gap-3">
          <button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showPlatformForm = false">取消</button>
          <button class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700" @click="handleCreatePlatform">创建</button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteCategoryTarget"
      title="删除分类"
      :message="`确认删除分类 ${deleteCategoryTarget?.name}？该分类下的智能体不会被删除。`"
      @confirm="confirmDeleteCategory"
      @cancel="deleteCategoryTarget = null"
    />
    <ConfirmDialog
      :visible="!!deletePlatformTarget"
      title="删除平台"
      :message="`确认删除平台 ${deletePlatformTarget?.label}？该平台下的智能体不会被删除。`"
      @confirm="confirmDeletePlatform"
      @cancel="deletePlatformTarget = null"
    />
  </div>
</template>
