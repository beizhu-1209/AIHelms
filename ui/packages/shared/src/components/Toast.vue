<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface ToastItem {
  id: number
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  actionLabel?: string
  actionPath?: string
}

const toasts = ref<ToastItem[]>([])
let nextId = 0

function addToast(
  message: string,
  type: ToastItem['type'] = 'info',
  duration = 4000,
  actionLabel?: string,
  actionPath?: string
) {
  const id = nextId++
  toasts.value.push({ id, message, type, actionLabel, actionPath })
  setTimeout(() => {
    removeToast(id)
  }, duration)
}

function removeToast(id: number) {
  toasts.value = toasts.value.filter(t => t.id !== id)
}

function handleToastEvent(e: Event) {
  const detail = (e as CustomEvent).detail
  addToast(detail.message, detail.type, detail.duration, detail.actionLabel, detail.actionPath)
}

function handleAction(toast: ToastItem) {
  if (toast.actionPath) {
    window.location.href = toast.actionPath
  }
  removeToast(toast.id)
}

onMounted(() => {
  window.addEventListener('aihelms-toast', handleToastEvent)
})

onUnmounted(() => {
  window.removeEventListener('aihelms-toast', handleToastEvent)
})

const typeClasses: Record<ToastItem['type'], string> = {
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
}

const iconPaths: Record<ToastItem['type'], string> = {
  success: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  error: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
  warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z',
  info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
      <TransitionGroup
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="translate-x-full opacity-0"
        enter-to-class="translate-x-0 opacity-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="translate-x-0 opacity-100"
        leave-to-class="translate-x-full opacity-0"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="[
            'pointer-events-auto flex items-center gap-2 rounded-lg border px-4 py-3 shadow-lg backdrop-blur-sm max-w-sm',
            typeClasses[toast.type],
          ]"
        >
          <svg class="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="iconPaths[toast.type]" />
          </svg>
          <span class="text-sm font-medium leading-5">{{ toast.message }}</span>
          <button
            v-if="toast.actionLabel"
            class="ml-2 shrink-0 rounded-md border border-current/30 px-2 py-1 text-xs font-semibold hover:bg-white/40"
            @click="handleAction(toast)"
          >
            {{ toast.actionLabel }}
          </button>
          <button
            class="ml-1 shrink-0 opacity-60 hover:opacity-100"
            @click="removeToast(toast.id)"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
