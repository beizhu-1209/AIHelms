<script setup lang="ts">
interface Props {
  visible: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
}

defineProps<Props>()
const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl">
      <h3 class="mb-2 text-lg font-semibold text-gray-900">{{ title }}</h3>
      <p class="mb-6 text-sm text-gray-600">{{ message }}</p>
      <div class="flex justify-end gap-3">
        <button
          class="rounded-md border px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          @click="emit('cancel')"
        >
          {{ cancelText || '取消' }}
        </button>
        <button
          class="rounded-md bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
          @click="emit('confirm')"
        >
          {{ confirmText || '确认' }}
        </button>
      </div>
    </div>
  </div>
</template>
