<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getSkills,
  getSkillCategories,
  createSkillCategory,
  deleteSkillCategory,
  type Skill,
  type SkillCategory,
} from '@aihelms/shared'
import { toast, usePermission } from '@aihelms/shared'
import { Plus, Download, X } from 'lucide-vue-next'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()
const router = useRouter()

const skills = ref<Skill[]>([])
const categories = ref<SkillCategory[]>([])
const loading = ref(false)
const selectedCategory = ref<string | null>(null)
const showCategoryForm = ref(false)
const categoryFormName = ref('')
const categoryFormDescription = ref('')
const deleteCategoryTarget = ref<SkillCategory | null>(null)

const categoriesWithCount = computed(() => {
  const counts = new Map<string, number>()
  for (const s of skills.value) counts.set(s.category, (counts.get(s.category) || 0) + 1)
  return categories.value.map((c) => ({ ...c, count: counts.get(c.name) || 0 }))
})

const filteredSkills = computed(() => {
  if (!selectedCategory.value) return skills.value
  return skills.value.filter((s) => s.category === selectedCategory.value)
})

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const [skillsRes, catsRes] = await Promise.all([getSkills(1, 200), getSkillCategories()])
    skills.value = skillsRes.items
    categories.value = catsRes
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

function openDetail(skill: Skill): void {
  router.push(`/skills/${skill.id}`)
}

function openCreate(): void {
  router.push('/skills/new')
}

async function handleCreateCategory(): Promise<void> {
  if (!categoryFormName.value.trim()) {
    toast.error('请输入分类名称')
    return
  }
  try {
    await createSkillCategory({
      name: categoryFormName.value.trim(),
      description: categoryFormDescription.value.trim(),
    })
    toast.success('分类创建成功')
    showCategoryForm.value = false
    categoryFormName.value = ''
    categoryFormDescription.value = ''
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '创建失败')
  }
}

async function confirmDeleteCategory(): Promise<void> {
  if (!deleteCategoryTarget.value) return
  try {
    await deleteSkillCategory(deleteCategoryTarget.value.id)
    toast.success('分类删除成功')
    if (selectedCategory.value === deleteCategoryTarget.value.name) selectedCategory.value = null
    deleteCategoryTarget.value = null
    await loadData()
  } catch (e) {
    toast.error((e as { message?: string }).message || '删除失败')
  }
}

onMounted(loadData)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Skill 管理</h1>
        <p class="mt-1 text-sm text-slate-500">管理员上传 Anthropic Skill zip 包，用户领取后在本地 Agent 中使用</p>
      </div>
      <button
        v-if="hasPermission('skill:create')"
        class="flex items-center gap-1.5 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-purple-500"
        @click="openCreate"
      >
        <Plus class="h-4 w-4" />
        新建 Skill
      </button>
    </div>

    <!-- 分类筛选条 -->
    <div class="mb-5 flex flex-wrap items-center gap-2">
      <button
        class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
        :class="!selectedCategory ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
        @click="selectedCategory = null"
      >
        全部 ({{ skills.length }})
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
          v-if="hasPermission('skill:delete')"
          class="ml-1 hidden text-slate-400 hover:text-red-500 group-hover:inline-block"
          @click="deleteCategoryTarget = cat"
        >
          <X class="h-3 w-3" />
        </button>
      </div>
      <button
        v-if="hasPermission('skill:create')"
        class="rounded-full border border-dashed border-slate-300 px-3 py-1 text-xs text-slate-500 transition-colors hover:border-purple-500 hover:text-purple-600"
        @click="showCategoryForm = true"
      >
        + 新建分类
      </button>
    </div>

    <!-- 卡片网格 -->
    <div v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中...</div>
    <div v-else-if="filteredSkills.length === 0" class="py-20 text-center text-sm text-slate-400">
      暂无 Skill，点击右上角"新建 Skill"开始
    </div>
    <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <div
        v-for="skill in filteredSkills"
        :key="skill.id"
        class="group cursor-pointer rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-purple-300 hover:shadow-md"
        @click="openDetail(skill)"
      >
        <div class="mb-3 flex items-start justify-between">
          <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-50 to-blue-50 text-2xl">
            {{ skill.icon }}
          </div>
          <div class="flex flex-col items-end gap-1">
            <span v-if="skill.is_published" class="rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-600">
              已发布
            </span>
            <span v-if="skill.requires_approval" class="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-600">
              需审批
            </span>
          </div>
        </div>
        <h3 class="mb-1 truncate text-base font-semibold text-slate-900 group-hover:text-purple-700">
          {{ skill.name }}
        </h3>
        <p class="mb-3 line-clamp-2 text-xs text-slate-500" :title="skill.description">
          {{ skill.description || '无描述' }}
        </p>
        <div class="mb-3 flex flex-wrap gap-1">
          <span class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-600">{{ skill.category }}</span>
          <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">v{{ skill.version }}</span>
          <span v-for="tag in skill.tags.slice(0, 2)" :key="tag" class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
            {{ tag }}
          </span>
        </div>
        <div class="flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-400">
          <span class="flex items-center gap-1">
            <Download class="h-3 w-3" />
            {{ skill.install_count }} 次下载
          </span>
          <span v-if="skill.has_zip" class="text-green-600">已上传</span>
          <span v-else class="text-amber-600">未上传</span>
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
        <div class="mb-3">
          <label class="mb-1 block text-sm font-medium text-slate-700">名称</label>
          <input
            v-model="categoryFormName"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            placeholder="如：legal / dev / office"
          />
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-slate-700">描述（可选）</label>
          <input
            v-model="categoryFormDescription"
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div class="flex justify-end gap-3">
          <button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showCategoryForm = false">
            取消
          </button>
          <button class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700" @click="handleCreateCategory">
            创建
          </button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteCategoryTarget"
      title="删除分类"
      :message="`确认删除分类 ${deleteCategoryTarget?.name}？该分类下的 Skill 不会被删除，但需重新设置分类。`"
      @confirm="confirmDeleteCategory"
      @cancel="deleteCategoryTarget = null"
    />
  </div>
</template>
