<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  page: number
  pageSize: number
  total: number
  pageSizeOptions?: number[]
}

const props = withDefaults(defineProps<Props>(), {
  pageSizeOptions: () => [10, 20, 50, 100],
})

const emit = defineEmits<{
  change: [page: number]
  'update:pageSize': [pageSize: number]
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const pageItems = computed<(number | 'ellipsis')[]>(() => {
  const last = totalPages.value
  const current = props.page
  if (last <= 9) {
    return Array.from({ length: last }, (_, i) => i + 1)
  }
  const items: (number | 'ellipsis')[] = [1]
  const start = Math.max(2, current - 2)
  const end = Math.min(last - 1, current + 2)
  if (start > 2) items.push('ellipsis')
  for (let i = start; i <= end; i++) items.push(i)
  if (end < last - 1) items.push('ellipsis')
  items.push(last)
  return items
})

function goTo(target: number): void {
  if (target < 1 || target > totalPages.value || target === props.page) return
  emit('change', target)
}

function handlePageSizeChange(event: Event): void {
  const value = Number((event.target as HTMLSelectElement).value)
  if (value === props.pageSize) return
  emit('update:pageSize', value)
  emit('change', 1)
}

const btnClass =
  'min-w-8 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40'
const activeClass =
  'min-w-8 rounded-lg border border-indigo-500 bg-indigo-500 px-2.5 py-1.5 text-sm font-medium text-white'
</script>

<template>
  <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
    <span class="text-sm text-slate-500">共 {{ total }} 条</span>
    <div class="flex items-center gap-1">
      <button :disabled="page <= 1" :class="btnClass" @click="goTo(1)">首页</button>
      <button :disabled="page <= 1" :class="btnClass" @click="goTo(page - 1)">上一页</button>
      <template v-for="(item, index) in pageItems" :key="index">
        <span v-if="item === 'ellipsis'" class="px-1 text-sm text-slate-400">…</span>
        <button v-else :class="item === page ? activeClass : btnClass" @click="goTo(item)">{{ item }}</button>
      </template>
      <button :disabled="page >= totalPages" :class="btnClass" @click="goTo(page + 1)">下一页</button>
      <button :disabled="page >= totalPages" :class="btnClass" @click="goTo(totalPages)">末页</button>
      <select
        :value="pageSize"
        class="ml-2 rounded-lg border border-slate-200 bg-white py-1.5 pl-2 pr-6 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-400"
        @change="handlePageSizeChange"
      >
        <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }} 条/页</option>
      </select>
    </div>
  </div>
</template>
