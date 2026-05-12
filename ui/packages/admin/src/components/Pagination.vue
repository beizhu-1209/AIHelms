<script setup lang="ts">
interface Props {
  page: number
  pageSize: number
  total: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  change: [page: number]
}>()

function totalPages(): number {
  return Math.ceil(props.total / props.pageSize)
}

function handlePrev(): void {
  if (props.page > 1) {
    emit('change', props.page - 1)
  }
}

function handleNext(): void {
  if (props.page < totalPages()) {
    emit('change', props.page + 1)
  }
}
</script>

<template>
  <div class="mt-4 flex items-center justify-between">
    <span class="text-sm text-slate-500">共 {{ total }} 条</span>
    <div class="flex items-center gap-2">
      <button
        :disabled="page <= 1"
        class="rounded-lg bg-slate-100 px-3 py-1.5 text-sm text-slate-700 transition-colors hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
        @click="handlePrev"
      >
        上一页
      </button>
      <span class="text-sm text-slate-600">{{ page }} / {{ totalPages() }}</span>
      <button
        :disabled="page >= totalPages()"
        class="rounded-lg bg-slate-100 px-3 py-1.5 text-sm text-slate-700 transition-colors hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
        @click="handleNext"
      >
        下一页
      </button>
    </div>
  </div>
</template>
