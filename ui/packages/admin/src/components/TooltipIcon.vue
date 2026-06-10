<script setup lang="ts">
import { computed } from 'vue'
import { HelpCircle } from 'lucide-vue-next'

interface Props {
  text: string
  focusable?: boolean
  widthClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  focusable: true,
  widthClass: 'w-64',
})

const tabIndex = computed(() => (props.focusable ? 0 : undefined))
</script>

<template>
  <span
    class="group relative inline-flex cursor-help align-middle"
    :title="text"
    :aria-label="text"
    :tabindex="tabIndex"
    data-tooltip-trigger
  >
    <HelpCircle class="h-3.5 w-3.5 text-slate-400 transition group-hover:text-slate-600" />
    <span
      class="pointer-events-none invisible absolute bottom-full left-1/2 z-[70] mb-1.5 -translate-x-1/2 rounded-lg bg-slate-800 px-3 py-2 text-left text-xs font-normal leading-relaxed text-white opacity-0 shadow-lg transition group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100"
      :class="widthClass"
      role="tooltip"
      data-tooltip-content
    >
      {{ text }}
    </span>
  </span>
</template>
