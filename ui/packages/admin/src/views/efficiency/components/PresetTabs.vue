<script setup lang="ts">
interface Preset {
  key: string
  label: string
}

interface Props {
  modelValue: string
  presets?: Preset[]
}

withDefaults(defineProps<Props>(), {
  presets: () => [
    { key: 'today', label: '今日' },
    { key: '7d', label: '本周' },
    { key: 'month', label: '本月' },
    { key: 'last_month', label: '上月' },
    { key: '30d', label: '近30天' },
    { key: '90d', label: '本季' },
  ],
})

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <div class="inline-flex rounded-lg bg-slate-100/80 p-1">
    <button
      v-for="p in presets"
      :key="p.key"
      class="rounded-md px-3 py-1 text-xs transition-colors"
      :class="modelValue === p.key
        ? 'bg-white font-medium text-slate-900 shadow-sm'
        : 'text-slate-500 hover:text-slate-700'"
      @click="$emit('update:modelValue', p.key)"
    >
      {{ p.label }}
    </button>
  </div>
</template>
