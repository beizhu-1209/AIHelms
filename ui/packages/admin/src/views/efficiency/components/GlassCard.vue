<script setup lang="ts">
import { HelpCircle } from 'lucide-vue-next'

interface Props {
  title?: string
  subtitle?: string
  tooltip?: string
  padding?: string
}

withDefaults(defineProps<Props>(), {
  title: '',
  subtitle: '',
  tooltip: '',
  padding: 'p-5',
})
</script>

<template>
  <div
    class="rounded-xl border border-white/80 bg-white/70 shadow-sm backdrop-blur-xl"
    :class="padding"
  >
    <div v-if="title || $slots.action" class="mb-1 flex items-start justify-between gap-3">
      <div class="flex-1">
        <div v-if="title" class="flex items-center gap-1.5">
          <span class="text-sm font-semibold text-slate-900">{{ title }}</span>
          <span v-if="tooltip" class="group relative cursor-help">
            <HelpCircle class="h-3.5 w-3.5 text-slate-300 transition hover:text-slate-500" />
            <span class="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 w-56 -translate-x-1/2 rounded-lg bg-slate-800 px-3 py-2 text-xs leading-relaxed text-white opacity-0 shadow-lg transition group-hover:opacity-100">
              {{ tooltip }}
            </span>
          </span>
        </div>
        <div v-if="subtitle" class="mt-0.5 text-xs text-slate-400">{{ subtitle }}</div>
      </div>
      <div v-if="$slots.action" class="shrink-0">
        <slot name="action" />
      </div>
    </div>
    <slot />
  </div>
</template>
