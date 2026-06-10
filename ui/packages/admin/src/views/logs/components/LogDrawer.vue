<script setup lang="ts">
import { ref, computed } from 'vue'
import { X, Copy, Check, ChevronDown, ChevronRight } from 'lucide-vue-next'
import { toast } from '@aihelms/shared'

interface InfoItem {
  label: string
  value: string | number | null | undefined
  mono?: boolean
}

interface JsonBlock {
  label: string
  value: unknown
  collapsed?: boolean
}

interface Props {
  open: boolean
  title: string
  subtitle?: string
  headerTag?: { text: string; color: string }
  info: InfoItem[]
  jsonBlocks?: JsonBlock[]
}

const props = withDefaults(defineProps<Props>(), {
  jsonBlocks: () => [],
})

const emit = defineEmits<{
  close: []
}>()

const copiedIdx = ref<number | null>(null)
const expanded = ref<Record<number, boolean>>({})

function close(): void {
  emit('close')
}

function deepParseJson(obj: unknown): unknown {
  if (typeof obj === 'string') {
    try {
      const parsed = JSON.parse(obj)
      return deepParseJson(parsed)
    } catch {
      return obj
    }
  }
  if (Array.isArray(obj)) {
    return obj.map(deepParseJson)
  }
  if (obj !== null && typeof obj === 'object') {
    const result: Record<string, unknown> = {}
    for (const [key, val] of Object.entries(obj as Record<string, unknown>)) {
      result[key] = deepParseJson(val)
    }
    return result
  }
  return obj
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  const parsed = deepParseJson(value)
  if (typeof parsed === 'string') return parsed
  try {
    return JSON.stringify(parsed, null, 2)
  } catch {
    return String(value)
  }
}

const formattedBlocks = computed(() =>
  props.jsonBlocks.map((block, idx) => ({
    label: block.label,
    text: formatValue(block.value),
    isEmpty: block.value === null || block.value === undefined || block.value === '',
    isExpanded: expanded.value[idx] ?? !block.collapsed,
  }))
)

function toggleBlock(idx: number, defaultExpanded: boolean): void {
  const current = expanded.value[idx] ?? defaultExpanded
  expanded.value[idx] = !current
}

async function handleCopy(idx: number, text: string): Promise<void> {
  if (!text || text === '—') return
  try {
    await navigator.clipboard.writeText(text)
    copiedIdx.value = idx
    setTimeout(() => {
      if (copiedIdx.value === idx) copiedIdx.value = null
    }, 2000)
  } catch {
    toast.error('复制失败')
  }
}
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50"
  >
    <div class="absolute inset-0 bg-black/30" @click="close" />
    <aside
      class="absolute right-0 top-0 flex h-full w-full max-w-3xl flex-col bg-white shadow-2xl"
    >
      <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-6 py-4">
        <div class="flex items-center gap-3">
          <span
            v-if="headerTag"
            class="rounded px-2 py-0.5 text-xs font-semibold"
            :class="headerTag.color"
          >
            {{ headerTag.text }}
          </span>
          <div>
            <div class="text-base font-semibold text-slate-900">{{ title }}</div>
            <div v-if="subtitle" class="mt-0.5 text-xs text-slate-500">{{ subtitle }}</div>
          </div>
        </div>
        <button
          class="flex h-8 w-8 items-center justify-center rounded text-slate-500 hover:bg-slate-100"
          aria-label="关闭"
          @click="close"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-5">
        <div class="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">基本信息</p>
          <div v-for="item in info" :key="item.label" class="flex items-start gap-2 py-1">
            <span class="w-28 shrink-0 text-xs text-slate-500">{{ item.label }}</span>
            <span
              class="text-xs text-slate-900"
              :class="item.mono ? 'break-all font-mono' : 'break-all'"
            >{{ item.value ?? '—' }}</span>
          </div>
        </div>

        <div
          v-for="(block, idx) in formattedBlocks"
          :key="block.label"
          class="mb-4 overflow-hidden rounded-lg border border-slate-200 bg-white"
        >
          <div
            class="flex cursor-pointer items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2"
            @click="toggleBlock(idx, !jsonBlocks[idx].collapsed)"
          >
            <span class="flex items-center gap-1 text-xs font-semibold text-slate-600">
              <ChevronDown v-if="block.isExpanded" class="h-3.5 w-3.5" />
              <ChevronRight v-else class="h-3.5 w-3.5" />
              {{ block.label }}
            </span>
            <button
              v-if="!block.isEmpty"
              class="flex items-center gap-1 rounded p-1 text-xs text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-700"
              :title="copiedIdx === idx ? '已复制' : '复制'"
              @click.stop="handleCopy(idx, block.text)"
            >
              <Check v-if="copiedIdx === idx" class="h-3.5 w-3.5 text-green-600" />
              <Copy v-else class="h-3.5 w-3.5" />
            </button>
          </div>
          <pre
            v-if="block.isExpanded"
            class="m-0 max-h-[50vh] overflow-auto whitespace-pre-wrap break-all rounded-b-lg bg-slate-900 p-4 font-mono text-xs leading-relaxed text-green-300"
          >{{ block.isEmpty ? '空' : block.text }}</pre>
        </div>
      </div>
    </aside>
  </div>
</template>
