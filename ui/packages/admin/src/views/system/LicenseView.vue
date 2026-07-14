<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Blocks,
  Building2,
  CalendarDays,
  FileKey2,
  KeyRound,
  LoaderCircle,
  ShieldAlert,
  ShieldCheck,
  ShieldOff,
  Upload,
} from 'lucide-vue-next'
import { importLicense, useBranding, useLicense } from '@aihelms/shared'

const { status, loading, refresh } = useLicense()
const { refresh: refreshBranding, applyToDocument } = useBranding()
const importing = ref(false)
const selectedFile = ref('')

const editionLabel = computed(() => {
  if (status.value?.status === 'active') return '企业版'
  if (status.value?.status === 'expired') return '企业版（已过期）'
  return '社区版'
})

const statusLabel = computed(() => {
  if (status.value?.status === 'active') return '授权有效'
  if (status.value?.status === 'expired') return '授权已过期'
  return '未导入授权'
})

const featureLabels: Record<string, string> = {
  whitelabel: '品牌白标',
}

function featureLabel(feature: string): string {
  return featureLabels[feature] ?? feature
}

async function handleFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  selectedFile.value = file.name
  importing.value = true
  try {
    await importLicense(file)
    await Promise.all([refresh(), refreshBranding()])
    applyToDocument()
  } finally {
    importing.value = false
    input.value = ''
  }
}

onMounted(async () => {
  if (!status.value) await refresh()
})
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-slate-950">License 授权</h1>
        <p class="mt-1 text-sm text-slate-500">企业授权状态与功能许可</p>
      </div>
      <div
        class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium"
        :class="status?.status === 'active'
          ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
          : status?.status === 'expired'
            ? 'border-amber-200 bg-amber-50 text-amber-700'
            : 'border-slate-200 bg-white text-slate-600'"
      >
        <ShieldCheck v-if="status?.status === 'active'" class="h-4 w-4" />
        <ShieldAlert v-else-if="status?.status === 'expired'" class="h-4 w-4" />
        <ShieldOff v-else class="h-4 w-4" />
        {{ statusLabel }}
      </div>
    </header>

    <section class="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div class="flex items-center gap-4 border-b border-slate-100 px-5 py-5">
        <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-slate-900 text-white">
          <KeyRound class="h-5 w-5" />
        </div>
        <div>
          <p class="text-xs font-medium uppercase text-slate-500">当前版本</p>
          <p class="mt-0.5 text-lg font-semibold text-slate-950">
            {{ loading ? '读取中' : editionLabel }}
          </p>
        </div>
      </div>

      <dl class="grid divide-y divide-slate-100 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <div class="px-5 py-4">
          <dt class="flex items-center gap-2 text-xs font-medium text-slate-500">
            <Building2 class="h-4 w-4" />
            授权客户
          </dt>
          <dd class="mt-2 truncate text-sm font-medium text-slate-900">
            {{ status?.licensed_to || '未授权' }}
          </dd>
        </div>
        <div class="px-5 py-4">
          <dt class="flex items-center gap-2 text-xs font-medium text-slate-500">
            <CalendarDays class="h-4 w-4" />
            到期日期
          </dt>
          <dd class="mt-2 text-sm font-medium text-slate-900">
            {{ status?.expires_at || '无' }}
          </dd>
        </div>
        <div class="px-5 py-4">
          <dt class="flex items-center gap-2 text-xs font-medium text-slate-500">
            <Blocks class="h-4 w-4" />
            已许可功能
          </dt>
          <dd class="mt-2 flex min-h-5 flex-wrap gap-1.5">
            <span
              v-for="feature in status?.features || []"
              :key="feature"
              class="rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700"
            >
              {{ featureLabel(feature) }}
            </span>
            <span v-if="!status?.features.length" class="text-sm font-medium text-slate-900">无</span>
          </dd>
        </div>
      </dl>
    </section>

    <section class="flex flex-wrap items-center justify-between gap-5 rounded-lg border border-slate-200 bg-white px-5 py-5">
      <div class="flex min-w-0 items-center gap-3">
        <FileKey2 class="h-5 w-5 shrink-0 text-slate-500" />
        <div class="min-w-0">
          <p class="text-sm font-medium text-slate-900">License 文件</p>
          <p class="mt-0.5 truncate text-xs text-slate-500">
            {{ selectedFile || '支持 .key 或 .txt 文件' }}
          </p>
        </div>
      </div>
      <label
        class="inline-flex h-9 cursor-pointer items-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-700"
        :class="importing ? 'pointer-events-none opacity-60' : ''"
      >
        <LoaderCircle v-if="importing" class="h-4 w-4 animate-spin" />
        <Upload v-else class="h-4 w-4" />
        {{ importing ? '导入中' : '导入 License' }}
        <input
          type="file"
          accept=".key,.txt,text/plain"
          class="hidden"
          :disabled="importing"
          @change="handleFile"
        />
      </label>
    </section>
  </div>
</template>
