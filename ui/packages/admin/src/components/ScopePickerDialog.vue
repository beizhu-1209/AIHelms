<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ChevronRight, Search, X } from 'lucide-vue-next'
import { buildDepartmentPathMap, flattenDepartmentTree } from './scopePickerTypes'

import type { DeptTreeNode, ScopeDimension, ScopeOption } from './scopePickerTypes'

interface Props {
  open: boolean
  dimension: ScopeDimension
  departmentTree: DeptTreeNode[]
  projectOptions: ScopeOption[]
  modelValue: number[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [ids: number[]]
  'update:open': [open: boolean]
  confirm: [ids: number[]]
}>()

const currentPath = ref<DeptTreeNode[]>([])
const keyword = ref('')
const selectedIds = ref<number[]>([])

const currentLevel = computed(() => {
  const current = currentPath.value[currentPath.value.length - 1]
  return current?.children || props.departmentTree
})
const departmentMatches = computed(() => {
  const normalized = keyword.value.trim().toLocaleLowerCase()
  if (!normalized) return []
  return flattenDepartmentTree(props.departmentTree).filter((item) =>
    item.node.name.toLocaleLowerCase().includes(normalized),
  )
})
const visibleProjects = computed(() => {
  const normalized = keyword.value.trim().toLocaleLowerCase()
  if (!normalized) return props.projectOptions
  return props.projectOptions.filter((item) => item.name.toLocaleLowerCase().includes(normalized))
})
const departmentPathMap = computed(() => buildDepartmentPathMap(props.departmentTree))
const projectNameMap = computed(() => new Map(props.projectOptions.map((item) => [item.id, item.name])))
const selectedItems = computed(() => selectedIds.value.map((id) => ({
  id,
  name: props.dimension === 'department'
    ? departmentPathMap.value.get(id) || `部门 ${id}`
    : projectNameMap.value.get(id) || `项目 ${id}`,
})))

watch(() => props.open, (open) => {
  if (!open) return
  selectedIds.value = [...props.modelValue]
  currentPath.value = []
  keyword.value = ''
})
watch(() => props.dimension, () => {
  currentPath.value = []
  keyword.value = ''
})

function isSelected(id: number): boolean {
  return selectedIds.value.includes(id)
}

function toggleSelection(id: number) {
  selectedIds.value = isSelected(id)
    ? selectedIds.value.filter((item) => item !== id)
    : [...selectedIds.value, id]
}

function handleDepartmentName(node: DeptTreeNode) {
  if (node.children?.length) currentPath.value.push(node)
  else toggleSelection(node.id)
}

function handleBreadcrumb(index: number) {
  currentPath.value.splice(index)
}

function handleClose() {
  emit('update:open', false)
}

function handleConfirm() {
  const ids = [...selectedIds.value]
  emit('update:modelValue', ids)
  emit('confirm', ids)
  emit('update:open', false)
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/35 p-4" @click.self="handleClose">
    <div class="flex max-h-[72vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
      <div class="flex items-center justify-between border-b border-slate-200 px-5 py-4">
        <div>
          <h3 class="text-base font-semibold text-slate-900">选择{{ dimension === 'department' ? '部门' : '项目' }}</h3>
          <p class="mt-0.5 text-xs text-slate-500">{{ dimension === 'department' ? '可多选，勾选父部门不会自动包含子部门' : '可多选，支持按项目名称搜索' }}</p>
        </div>
        <button type="button" class="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" @click="handleClose"><X class="h-4 w-4" /></button>
      </div>
      <div class="grid min-h-0 flex-1 grid-cols-[minmax(0,1.35fr)_minmax(260px,0.65fr)]">
        <div class="flex min-h-0 flex-col border-r border-slate-200 p-4">
          <div class="relative mb-3">
            <Search class="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input v-model="keyword" type="search" :placeholder="`搜索${dimension === 'department' ? '部门' : '项目'}`" class="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
          </div>
          <div v-if="dimension === 'department' && !keyword.trim()" class="mb-2 flex flex-wrap items-center gap-1 text-xs text-slate-500">
            <template v-for="(node, index) in [{ id: 0, name: '全部' }, ...currentPath]" :key="node.id">
              <ChevronRight v-if="index" class="h-3 w-3 text-slate-300" />
              <button type="button" class="rounded px-1 py-0.5 hover:bg-slate-100 hover:text-blue-600" @click="handleBreadcrumb(index)">{{ node.name }}</button>
            </template>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto rounded-lg border border-slate-100">
            <template v-if="dimension === 'department'">
              <div v-for="item in keyword.trim() ? departmentMatches : currentLevel.map((node) => ({ node, path: node.name }))" :key="item.node.id" class="flex items-center gap-2 border-b border-slate-100 px-3 py-2.5 last:border-0 hover:bg-slate-50">
                <input type="checkbox" class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" :checked="isSelected(item.node.id)" @change="toggleSelection(item.node.id)" />
                <button type="button" class="flex min-w-0 flex-1 items-center gap-2 text-left text-sm text-slate-700" @click="keyword.trim() ? toggleSelection(item.node.id) : handleDepartmentName(item.node)">
                  <span class="min-w-0 flex-1 truncate">{{ keyword.trim() ? item.path : item.node.name }}</span>
                  <ChevronRight v-if="!keyword.trim() && item.node.children?.length" class="h-4 w-4 shrink-0 text-slate-400" />
                </button>
              </div>
              <div v-if="(keyword.trim() ? departmentMatches : currentLevel).length === 0" class="py-10 text-center text-sm text-slate-400">暂无匹配部门</div>
            </template>
            <template v-else>
              <label v-for="project in visibleProjects" :key="project.id" class="flex cursor-pointer items-center gap-2 border-b border-slate-100 px-3 py-2.5 last:border-0 hover:bg-slate-50">
                <input type="checkbox" class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" :checked="isSelected(project.id)" @change="toggleSelection(project.id)" />
                <span class="truncate text-sm text-slate-700">{{ project.name }}</span>
              </label>
              <div v-if="visibleProjects.length === 0" class="py-10 text-center text-sm text-slate-400">暂无匹配项目</div>
            </template>
          </div>
        </div>
        <div class="flex min-h-0 flex-col p-4">
          <div class="mb-3 flex items-center justify-between">
            <span class="text-sm font-medium text-slate-800">已选 {{ selectedIds.length }} 个</span>
            <button type="button" class="text-xs text-blue-600 hover:text-blue-700 disabled:text-slate-300" :disabled="selectedIds.length === 0" @click="selectedIds = []">清空</button>
          </div>
          <div class="min-h-0 flex-1 space-y-2 overflow-y-auto">
            <div v-for="item in selectedItems" :key="item.id" class="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
              <span class="min-w-0 flex-1 break-words">{{ item.name }}</span>
              <button type="button" class="shrink-0 text-slate-400 hover:text-red-500" @click="toggleSelection(item.id)"><X class="h-3.5 w-3.5" /></button>
            </div>
            <div v-if="selectedItems.length === 0" class="py-10 text-center text-sm text-slate-400">暂未选择</div>
          </div>
        </div>
      </div>
      <div class="flex justify-end gap-2 border-t border-slate-200 px-5 py-3">
        <button type="button" class="rounded-md border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50" @click="handleClose">取消</button>
        <button type="button" class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700" @click="handleConfirm">确定</button>
      </div>
    </div>
  </div>
</template>
