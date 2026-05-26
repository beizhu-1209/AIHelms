<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getSkillById,
  getSkillCategories,
  createSkill,
  updateSkill,
  deleteSkill,
  getSkillDownloadUrl,
  type Skill,
  type SkillCategory,
} from '@aihelms/shared'
import { toast, usePermission } from '@aihelms/shared'
import { ArrowLeft, Trash2, Download } from 'lucide-vue-next'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import IconPicker from '../../components/IconPicker.vue'

const { hasPermission } = usePermission()
const route = useRoute()
const router = useRouter()

const isNew = computed(() => route.params.id === 'new')
const skillId = computed(() => (isNew.value ? null : Number(route.params.id)))

const skill = ref<Skill | null>(null)
const categories = ref<SkillCategory[]>([])
const loading = ref(false)
const saving = ref(false)
const showDelete = ref(false)

const form = ref({
  name: '',
  icon: '📦',
  description: '',
  category: 'general',
  version: '1.0.0',
  tags: '',
  usage_instructions: '',
  is_published: false,
  requires_approval: false,
})
const zipFile = ref<File | null>(null)

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const cats = await getSkillCategories()
    categories.value = cats
    if (!isNew.value && skillId.value) {
      const s = await getSkillById(skillId.value)
      skill.value = s
      form.value = {
        name: s.name,
        icon: s.icon,
        description: s.description,
        category: s.category,
        version: s.version,
        tags: (s.tags || []).join(', '),
        usage_instructions: s.usage_instructions,
        is_published: s.is_published,
        requires_approval: s.requires_approval,
      }
    } else {
      form.value.category = cats[0]?.name || 'general'
    }
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleZipChange(event: Event): void {
  const target = event.target as HTMLInputElement
  zipFile.value = target.files?.[0] || null
}

async function handleSave(): Promise<void> {
  if (!form.value.name) {
    toast.error('请填写名称')
    return
  }
  saving.value = true
  try {
    const tags = form.value.tags
      ? form.value.tags.split(',').map((t) => t.trim()).filter(Boolean)
      : []
    const payload = {
      name: form.value.name,
      icon: form.value.icon,
      description: form.value.description,
      category: form.value.category,
      version: form.value.version,
      tags,
      usage_instructions: form.value.usage_instructions,
      is_published: form.value.is_published,
      requires_approval: form.value.requires_approval,
      zip_file: zipFile.value,
    }
    if (isNew.value) {
      await createSkill(payload)
      toast.success('Skill 创建成功')
      router.push('/skills')
    } else if (skillId.value) {
      await updateSkill(skillId.value, payload)
      toast.success('Skill 更新成功')
      router.push('/skills')
    }
  } catch (e) {
    toast.error((e as { message?: string }).message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(): Promise<void> {
  if (!skillId.value) return
  try {
    await deleteSkill(skillId.value)
    toast.success('Skill 删除成功')
    router.push('/skills')
  } catch (e) {
    toast.error((e as { message?: string }).message || '删除失败')
  }
}

function downloadZip(): void {
  if (!skill.value?.has_zip) return
  const url = getSkillDownloadUrl(skill.value.id)
  const token = localStorage.getItem('aihelms_token')
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then((res) => res.blob())
    .then((blob) => {
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = skill.value!.zip_filename || `${skill.value!.name}.zip`
      link.click()
      URL.revokeObjectURL(link.href)
    })
    .then(() => loadData())
}

onMounted(loadData)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <button
        class="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
        @click="router.push('/skills')"
      >
        <ArrowLeft class="h-4 w-4" />
        返回列表
      </button>
      <div v-if="!isNew && hasPermission('skill:delete')" class="flex gap-2">
        <button
          class="flex items-center gap-1 rounded-lg bg-red-50 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-100"
          @click="showDelete = true"
        >
          <Trash2 class="h-4 w-4" />
          删除
        </button>
      </div>
    </div>

    <div v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中...</div>
    <template v-else>
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 class="mb-5 text-xl font-bold text-slate-900">
          {{ isNew ? '新建 Skill' : `编辑：${form.name || ''}` }}
        </h1>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">名称 *</label>
            <input
              v-model="form.name"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div>
            <IconPicker v-model="form.icon" label="图标" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">分类</label>
            <select
              v-model="form.category"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            >
              <option v-for="c in categories" :key="c.id" :value="c.name">{{ c.name }}</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">版本</label>
            <input
              v-model="form.version"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div class="col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">标签（逗号分隔）</label>
            <input
              v-model="form.tags"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
              placeholder="legal, ocr, markdown"
            />
          </div>
          <div class="col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">描述</label>
            <textarea
              v-model="form.description"
              rows="2"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div class="col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">使用说明（支持 Markdown）</label>
            <textarea
              v-model="form.usage_instructions"
              rows="8"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div class="col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">
              上传 zip 包
              <span v-if="!isNew && skill?.has_zip" class="text-xs text-slate-400">（不上传则保留原文件）</span>
            </label>
            <div class="flex items-center gap-3">
              <input
                type="file"
                accept=".zip"
                class="block flex-1 text-sm text-slate-700 file:mr-3 file:rounded-md file:border-0 file:bg-purple-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-purple-700 hover:file:bg-purple-100"
                @change="handleZipChange"
              />
              <button
                v-if="!isNew && skill?.has_zip"
                class="flex items-center gap-1 rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-200"
                @click="downloadZip"
              >
                <Download class="h-3 w-3" />
                下载当前
              </button>
            </div>
            <div v-if="zipFile" class="mt-1 text-xs text-slate-500">
              已选择：{{ zipFile.name }} ({{ Math.round(zipFile.size / 1024) }} KB)
            </div>
            <div v-else-if="!isNew && skill?.zip_filename" class="mt-1 text-xs text-slate-500">
              当前文件：{{ skill.zip_filename }} ({{ Math.round((skill.zip_size || 0) / 1024) }} KB)
              · 已下载 {{ skill.install_count }} 次
            </div>
          </div>
          <div class="col-span-2 flex items-center gap-4">
            <label class="flex items-center gap-2 text-sm text-slate-700">
              <input v-model="form.is_published" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
              发布到用户端
            </label>
            <label class="flex items-center gap-2 text-sm text-slate-700">
              <input
                v-model="form.requires_approval"
                type="checkbox"
                :disabled="!form.is_published"
                class="h-4 w-4 rounded border-slate-300 disabled:opacity-50"
              />
              领用前需要审批
            </label>
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-3 border-t border-slate-100 pt-4">
          <button
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            @click="router.push('/skills')"
          >
            取消
          </button>
          <button
            class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
            :disabled="saving"
            @click="handleSave"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </template>

    <ConfirmDialog
      :visible="showDelete"
      title="删除 Skill"
      :message="`确认删除 ${skill?.name}？此操作不可恢复，包含的 zip 文件也会被删除。`"
      @confirm="handleDelete"
      @cancel="showDelete = false"
    />
  </div>
</template>
