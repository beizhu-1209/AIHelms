<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getKeyScenarios,
  createKeyScenario,
  updateKeyScenario,
  deleteKeyScenario,
  type KeyScenario,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()

const scenarios = ref<KeyScenario[]>([])
const total = ref(0)
const isLoading = ref(false)
const keyword = ref('')

const showForm = ref(false)
const editingId = ref<number | null>(null)
const formName = ref('')
const formDescription = ref('')
const formError = ref('')
const deleteTarget = ref<KeyScenario | null>(null)

async function fetchData(): Promise<void> {
  isLoading.value = true
  const result = await getKeyScenarios(1, 100, keyword.value || undefined)
  scenarios.value = result.items
  total.value = result.total
  isLoading.value = false
}

function handleCreate(): void {
  editingId.value = null
  formName.value = ''
  formDescription.value = ''
  formError.value = ''
  showForm.value = true
}

function handleEdit(scenario: KeyScenario): void {
  editingId.value = scenario.id
  formName.value = scenario.name
  formDescription.value = scenario.description
  formError.value = ''
  showForm.value = true
}

async function handleSubmit(): Promise<void> {
  formError.value = ''
  if (!formName.value.trim()) {
    formError.value = '请输入场景名称'
    return
  }
  try {
    if (editingId.value) {
      await updateKeyScenario(editingId.value, {
        name: formName.value.trim(),
        description: formDescription.value.trim(),
      })
    } else {
      await createKeyScenario({
        name: formName.value.trim(),
        description: formDescription.value.trim(),
      })
    }
    showForm.value = false
    await fetchData()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  try {
    await deleteKeyScenario(deleteTarget.value.id)
    deleteTarget.value = null
    await fetchData()
  } catch (e) {
    deleteTarget.value = null
  }
}

onMounted(fetchData)
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <input
          v-model="keyword"
          placeholder="搜索场景名称..."
          class="h-8 w-52 rounded-lg border border-slate-200 bg-white px-3 text-sm placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
          @keyup.enter="fetchData"
        />
        <button class="h-8 rounded-lg bg-slate-100 px-3 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200" @click="fetchData">搜索</button>
      </div>
      <button
        v-if="hasPermission('user:update')"
        class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-3.5 py-1.5 text-xs font-medium text-white shadow-sm shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500"
        @click="handleCreate"
      >新建场景</button>
    </div>

    <table class="w-full text-left text-sm">
      <thead class="border-b border-slate-200/60">
        <tr>
          <th class="px-3 py-2 font-medium text-slate-600">名称</th>
          <th class="px-3 py-2 font-medium text-slate-600">描述</th>
          <th class="px-3 py-2 font-medium text-slate-600">创建时间</th>
          <th class="px-3 py-2 font-medium text-slate-600">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in scenarios" :key="s.id" class="border-b border-slate-100 hover:bg-slate-50/50">
          <td class="px-3 py-2 font-medium text-slate-900">{{ s.name }}</td>
          <td class="px-3 py-2 text-slate-600">{{ s.description || '-' }}</td>
          <td class="px-3 py-2 text-xs text-slate-500">{{ s.created_at?.slice(0, 10) || '-' }}</td>
          <td class="px-3 py-2">
            <div class="flex gap-2">
              <button v-if="hasPermission('user:update')" class="text-xs text-purple-500 hover:text-purple-600" @click="handleEdit(s)">编辑</button>
              <button v-if="hasPermission('user:delete')" class="text-xs text-red-500 hover:text-red-600" @click="deleteTarget = s">删除</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="isLoading" class="py-12 text-center text-sm text-slate-400">加载中...</div>
    <div v-if="!isLoading && scenarios.length === 0" class="py-12 text-center text-sm text-slate-400">暂无使用场景</div>

    <!-- Create/Edit Dialog -->
    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-sm rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ editingId ? '编辑场景' : '新建场景' }}</h3>
        <form @submit.prevent="handleSubmit">
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">场景名称</label>
            <input v-model="formName" placeholder="如：代码助手、文档翻译" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">描述</label>
            <input v-model="formDescription" placeholder="可选" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <p v-if="formError" class="mb-3 text-sm text-red-500">{{ formError }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showForm = false">取消</button>
            <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 hover:from-purple-500 hover:to-blue-500">{{ editingId ? '保存' : '创建' }}</button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteTarget"
      title="删除场景"
      :message="`确定删除场景「${deleteTarget?.name}」？`"
      @confirm="handleConfirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>
