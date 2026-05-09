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
  <div class="flex items-center justify-between border-t pt-4">
    <span class="text-sm text-gray-600">共 {{ total }} 条</span>
    <div class="flex items-center gap-2">
      <button
        :disabled="page <= 1"
        class="rounded-md border px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
        @click="handlePrev"
      >
        上一页
      </button>
      <span class="text-sm text-gray-700">{{ page }} / {{ totalPages() }}</span>
      <button
        :disabled="page >= totalPages()"
        class="rounded-md border px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
        @click="handleNext"
      >
        下一页
      </button>
    </div>
  </div>
</template>
