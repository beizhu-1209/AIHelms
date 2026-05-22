<script setup lang="ts">
interface Props {
  title?: string
  subtitle?: string
  padding?: string
}

withDefaults(defineProps<Props>(), {
  title: '',
  subtitle: '',
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
        <div v-if="title" class="text-sm font-semibold text-slate-900">{{ title }}</div>
        <div v-if="subtitle" class="mt-0.5 text-xs text-slate-400">{{ subtitle }}</div>
      </div>
      <div v-if="$slots.action" class="shrink-0">
        <slot name="action" />
      </div>
    </div>
    <slot />
  </div>
</template>
