<script setup lang="ts">
import { computed } from 'vue'
import TooltipIcon from '../../../components/TooltipIcon.vue'

interface Props {
  title?: string
  subtitle?: string
  tooltip?: string
  padding?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  subtitle: '',
  tooltip: '',
  padding: 'p-5',
})

const headerClass = computed(() =>
  props.padding === 'p-0'
    ? 'px-5 pt-4 pb-3'
    : 'mb-4'
)
</script>

<template>
  <div
    class="rounded-xl border border-white/80 bg-white/70 shadow-sm backdrop-blur-xl"
    :class="padding"
  >
    <div
      v-if="title || $slots.action"
      class="flex min-h-9 items-center justify-between gap-4"
      :class="headerClass"
    >
      <div class="min-w-0 flex-1">
        <div v-if="title" class="flex min-w-0 items-center gap-1.5">
          <span class="truncate text-sm font-semibold text-slate-900">{{ title }}</span>
          <TooltipIcon v-if="tooltip" :text="tooltip" width-class="w-56" />
        </div>
        <div v-if="subtitle" class="mt-0.5 truncate text-xs text-slate-400">{{ subtitle }}</div>
      </div>
      <div v-if="$slots.action" class="flex shrink-0 items-center justify-end pr-0.5">
        <slot name="action" />
      </div>
    </div>
    <slot />
  </div>
</template>
