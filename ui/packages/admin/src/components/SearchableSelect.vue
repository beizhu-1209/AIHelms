<script setup lang="ts" generic="T extends string | number">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Check, ChevronDown, Loader2, Search, X } from 'lucide-vue-next'

interface SearchableSelectOption {
  value: T
  label: string
  searchText?: string
  disabled?: boolean
}

const props = withDefaults(defineProps<{
  modelValue: T | ''
  options: SearchableSelectOption[]
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  selectedLabel?: string
  disabled?: boolean
  loading?: boolean
  remote?: boolean
  clearable?: boolean
  menuClass?: string
}>(), {
  placeholder: '请选择',
  searchPlaceholder: '搜索',
  emptyText: '无匹配结果',
  selectedLabel: '',
  disabled: false,
  loading: false,
  remote: false,
  clearable: true,
  menuClass: 'z-[70]',
})

const emit = defineEmits<{
  'update:modelValue': [value: T | '']
  change: [value: T | '']
  search: [keyword: string]
}>()

const root = ref<HTMLElement | null>(null)
const searchInput = ref<HTMLInputElement | null>(null)
const open = ref(false)
const keyword = ref('')
const activeIndex = ref(-1)
const listboxId = `searchable-select-${Math.random().toString(36).slice(2)}`

const selectedOption = computed(() => (
  props.options.find((option) => option.value === props.modelValue)
))

const selectedText = computed(() => (
  selectedOption.value?.label || props.selectedLabel || props.placeholder
))

const visibleOptions = computed(() => {
  if (props.remote || !keyword.value.trim()) return props.options
  const normalizedKeyword = keyword.value.trim().toLocaleLowerCase()
  return props.options.filter((option) => (
    `${option.label} ${option.searchText || ''}`.toLocaleLowerCase().includes(normalizedKeyword)
  ))
})

function firstEnabledIndex(): number {
  return visibleOptions.value.findIndex((option) => !option.disabled)
}

function openMenu(): void {
  if (props.disabled) return
  open.value = true
  keyword.value = ''
  activeIndex.value = firstEnabledIndex()
  emit('search', '')
  nextTick(() => searchInput.value?.focus())
}

function closeMenu(): void {
  open.value = false
  keyword.value = ''
  activeIndex.value = -1
}

function toggleMenu(): void {
  if (open.value) closeMenu()
  else openMenu()
}

function selectOption(option: SearchableSelectOption): void {
  if (option.disabled) return
  emit('update:modelValue', option.value)
  emit('change', option.value)
  closeMenu()
}

function clearSelection(): void {
  if (props.disabled) return
  emit('update:modelValue', '')
  emit('change', '')
  closeMenu()
}

function handleSearchInput(): void {
  activeIndex.value = firstEnabledIndex()
  emit('search', keyword.value)
}

function moveActive(step: number): void {
  const options = visibleOptions.value
  if (!options.length) return
  let nextIndex = activeIndex.value
  for (let count = 0; count < options.length; count += 1) {
    nextIndex = (nextIndex + step + options.length) % options.length
    if (!options[nextIndex]?.disabled) {
      activeIndex.value = nextIndex
      return
    }
  }
}

function handleTriggerKeydown(event: KeyboardEvent): void {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openMenu()
    if (event.key === 'ArrowUp') moveActive(-1)
  }
}

function handleSearchKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.preventDefault()
    closeMenu()
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveActive(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveActive(-1)
  } else if (event.key === 'Enter') {
    event.preventDefault()
    const option = visibleOptions.value[activeIndex.value]
    if (option) selectOption(option)
  } else if (event.key === 'Tab') {
    closeMenu()
  }
}

function handleDocumentMouseDown(event: MouseEvent): void {
  if (root.value && !root.value.contains(event.target as Node)) closeMenu()
}

watch(visibleOptions, () => {
  if (open.value && !visibleOptions.value[activeIndex.value]) {
    activeIndex.value = firstEnabledIndex()
  }
})

watch(() => props.disabled, (disabled) => {
  if (disabled) closeMenu()
})

onMounted(() => document.addEventListener('mousedown', handleDocumentMouseDown))
onBeforeUnmount(() => document.removeEventListener('mousedown', handleDocumentMouseDown))
</script>

<template>
  <div ref="root" class="relative min-w-[10rem]">
    <div
      class="flex h-9 items-center rounded-lg border border-slate-200 bg-white text-sm transition-colors focus-within:border-purple-500"
      :class="disabled ? 'cursor-not-allowed bg-slate-50 text-slate-400' : 'text-slate-700'"
    >
      <button
        type="button"
        class="min-w-0 flex-1 truncate px-3 text-left outline-none"
        :class="modelValue === '' ? 'text-slate-500' : 'text-slate-700'"
        :disabled="disabled"
        role="combobox"
        aria-haspopup="listbox"
        :aria-expanded="open"
        :aria-controls="listboxId"
        :data-selected-value="modelValue"
        @click="toggleMenu"
        @keydown="handleTriggerKeydown"
      >
        {{ selectedText }}
      </button>
      <button
        v-if="clearable && modelValue !== '' && !disabled"
        type="button"
        class="mr-1 rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
        :aria-label="`清空${placeholder}`"
        @click.stop="clearSelection"
      >
        <X class="h-3.5 w-3.5" />
      </button>
      <ChevronDown
        class="mr-2 h-4 w-4 shrink-0 text-slate-400 transition-transform"
        :class="open ? 'rotate-180' : ''"
      />
    </div>

    <div
      v-if="open"
      class="absolute left-0 top-full mt-1 w-max min-w-full max-w-[30rem] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg"
      :class="menuClass"
    >
      <div class="border-b border-slate-100 p-2">
        <div class="flex items-center gap-2 rounded-md border border-slate-200 px-2 focus-within:border-purple-500">
          <Search class="h-4 w-4 shrink-0 text-slate-400" />
          <input
            ref="searchInput"
            v-model="keyword"
            type="text"
            class="min-w-0 flex-1 bg-transparent py-1.5 text-sm text-slate-700 outline-none placeholder:text-slate-400"
            :placeholder="searchPlaceholder"
            autocomplete="off"
            @input="handleSearchInput"
            @keydown="handleSearchKeydown"
          />
        </div>
      </div>

      <div :id="listboxId" role="listbox" class="max-h-64 overflow-y-auto p-1">
        <div v-if="loading" class="flex items-center justify-center gap-2 px-3 py-6 text-sm text-slate-500">
          <Loader2 class="h-4 w-4 animate-spin" /> 加载中...
        </div>
        <div v-else-if="visibleOptions.length === 0" class="px-3 py-6 text-center text-sm text-slate-500">
          {{ emptyText }}
        </div>
        <template v-else>
          <button
            v-for="(option, index) in visibleOptions"
            :key="option.value"
            type="button"
            role="option"
            class="flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-sm"
            :class="[
              option.disabled ? 'cursor-not-allowed text-slate-300' : 'text-slate-700',
              activeIndex === index ? 'bg-purple-50' : 'hover:bg-slate-50',
            ]"
            :aria-selected="option.value === modelValue"
            :data-value="option.value"
            :disabled="option.disabled"
            :title="option.label"
            @mouseenter="activeIndex = index"
            @click="selectOption(option)"
          >
            <span class="truncate">{{ option.label }}</span>
            <Check v-if="option.value === modelValue" class="h-4 w-4 shrink-0 text-purple-600" />
          </button>
        </template>
      </div>
    </div>
  </div>
</template>
