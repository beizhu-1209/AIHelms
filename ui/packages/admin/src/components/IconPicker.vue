<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search, X } from 'lucide-vue-next'
import HostedIcon from '@aihelms/shared/src/components/HostedIcon.vue'

interface Props {
  modelValue: string
  label?: string
}

const props = withDefaults(defineProps<Props>(), {
  label: '图标',
})
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const showPicker = ref(false)
const search = ref('')

// Curated icon names for AI/dev/business scenarios
const ICON_NAMES: string[] = [
  'Search', 'Code', 'FileText', 'Database', 'Globe',
  'Bot', 'Brain', 'Sparkles', 'Zap', 'Shield',
  'Lock', 'Key', 'Eye', 'MessageSquare', 'Send',
  'Upload', 'Download', 'FolderOpen', 'File', 'FileCode',
  'Terminal', 'Server', 'Cloud', 'Wifi', 'Link',
  'GitBranch', 'GitPullRequest', 'Package', 'Box', 'Layers',
  'BarChart3', 'LineChart', 'PieChart', 'TrendingUp', 'Activity',
  'Users', 'UserCheck', 'Building2', 'Briefcase', 'Wallet',
  'CreditCard', 'DollarSign', 'Calculator', 'ClipboardList', 'CheckSquare',
  'AlertTriangle', 'Info', 'HelpCircle', 'Settings', 'Wrench',
  'Hammer', 'Puzzle', 'Lightbulb', 'Rocket', 'Target',
  'Flag', 'Bookmark', 'Star', 'Heart', 'ThumbsUp',
  'Languages', 'BookOpen', 'GraduationCap', 'Microscope', 'FlaskConical',
  'Cpu', 'HardDrive', 'Monitor', 'Smartphone', 'Tablet',
  'Camera', 'Image', 'Video', 'Music', 'Headphones',
  'Mail', 'Bell', 'Calendar', 'Clock', 'Timer',
  'MapPin', 'Navigation', 'Compass', 'Map', 'Route',
  'Scissors', 'Pen', 'Paintbrush', 'Palette', 'Wand2',
  'Presentation', 'Network', 'SpellCheck', 'Code2', 'PenLine', 'ShoppingCart',
]

const filtered = computed(() => {
  if (!search.value) return ICON_NAMES
  const q = search.value.toLowerCase()
  return ICON_NAMES.filter(name => name.toLowerCase().includes(q))
})

function toIconUrl(name: string): string {
  const filename = name
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/([A-Za-z])([0-9])/g, '$1-$2')
    .toLowerCase()
  return `/icons/v1/lucide/${filename}.svg`
}

const selectedName = computed(() => {
  if (props.modelValue === '📦') return 'Package'
  if (props.modelValue === '🤖') return 'Bot'
  const pathMatch = props.modelValue.match(/\/icons\/v1\/lucide\/([a-z0-9-]+)\.svg(?:$|[?#])/)
  if (pathMatch) {
    return ICON_NAMES.find(name => toIconUrl(name).includes(`/${pathMatch[1]}.svg`)) || ''
  }
  return ICON_NAMES.includes(props.modelValue) ? props.modelValue : ''
})

const selectedIconUrl = computed(() => {
  return selectedName.value ? toIconUrl(selectedName.value) : props.modelValue
})

const selectedLabel = computed(() => {
  if (selectedName.value) return selectedName.value
  if (props.modelValue.includes('/icons/v1/default.svg')) return '平台默认图标'
  return props.modelValue
})

function handleSelect(name: string) {
  emit('update:modelValue', toIconUrl(name))
  showPicker.value = false
  search.value = ''
}

function handleClear() {
  emit('update:modelValue', '/icons/v1/default.svg')
}
</script>

<template>
  <div>
    <label v-if="label" class="mb-1 block text-sm font-medium text-slate-700">{{ label }}</label>
    <div class="flex items-center gap-2">
      <button
        type="button"
        class="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white hover:bg-slate-50"
        @click="showPicker = true"
      >
        <HostedIcon v-if="modelValue" :src="selectedIconUrl" :size="20" :alt="selectedName" />
        <span v-else class="text-xs text-slate-400">+</span>
      </button>
      <span v-if="modelValue" class="text-xs text-slate-500">{{ selectedLabel }}</span>
      <button
        v-if="modelValue"
        type="button"
        class="text-xs text-slate-400 hover:text-red-500"
        @click="handleClear"
      >
        清除
      </button>
    </div>

    <!-- Picker Popover -->
    <Teleport to="body">
      <div
        v-if="showPicker"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/20 backdrop-blur-sm"
        @click.self="showPicker = false"
      >
        <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white p-5 shadow-xl">
          <div class="mb-3 flex items-center justify-between">
            <h4 class="text-sm font-semibold text-slate-800">选择图标</h4>
            <button class="rounded p-1 text-slate-400 hover:text-slate-600" @click="showPicker = false">
              <X class="h-4 w-4" />
            </button>
          </div>
          <div class="relative mb-3">
            <Search class="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              v-model="search"
              type="text"
              placeholder="搜索图标名..."
              class="w-full rounded-lg border border-slate-200 bg-white py-2 pl-8 pr-3 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div class="grid max-h-64 grid-cols-8 gap-1 overflow-y-auto">
            <button
              v-for="name in filtered"
              :key="name"
              type="button"
              class="flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
              :class="selectedName === name ? 'bg-purple-100 ring-2 ring-purple-500' : 'hover:bg-slate-100'"
              :title="name"
              @click="handleSelect(name)"
            >
              <HostedIcon :src="toIconUrl(name)" :size="16" :alt="name" />
            </button>
          </div>
          <p v-if="!filtered.length" class="py-4 text-center text-xs text-slate-400">无匹配图标</p>
        </div>
      </div>
    </Teleport>
  </div>
</template>
