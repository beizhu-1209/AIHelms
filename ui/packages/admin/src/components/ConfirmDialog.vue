<script setup lang="ts">
interface Props {
  visible: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  error?: string
  loading?: boolean
}

defineProps<Props>()
const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
    <div
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      :aria-busy="loading || undefined"
      class="w-full max-w-sm rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl"
    >
      <h3 class="mb-2 text-lg font-semibold text-slate-900">{{ title }}</h3>
      <p class="mb-6 text-sm text-slate-600">{{ message }}</p>
      <p v-if="error" role="alert" class="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ error }}
      </p>
      <div class="flex justify-end gap-3">
        <button
          type="button"
          :disabled="loading"
          class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
          @click="emit('cancel')"
        >
          {{ cancelText || '取消' }}
        </button>
        <button
          type="button"
          :disabled="loading"
          class="rounded-lg bg-red-50 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-100"
          @click="emit('confirm')"
        >
          {{ loading ? '处理中...' : (confirmText || '确认') }}
        </button>
      </div>
    </div>
  </div>
</template>
