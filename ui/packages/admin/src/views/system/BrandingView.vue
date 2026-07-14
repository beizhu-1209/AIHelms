<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Check,
  Image,
  ImageUp,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  Palette,
  Save,
  Upload,
} from 'lucide-vue-next'
import {
  updatePlatformName,
  uploadFavicon,
  uploadLogo,
  uploadSquareLogo,
  useBranding,
  useLicense,
} from '@aihelms/shared'

const router = useRouter()
const { isEnterprise } = useLicense()
const { branding, logoUrl, squareLogoUrl, faviconUrl, refresh, applyToDocument } = useBranding()
const name = ref('')
const savingName = ref(false)
const uploadingLogo = ref(false)
const uploadingSquareLogo = ref(false)
const uploadingFavicon = ref(false)

const canSaveName = computed(() => {
  const normalized = name.value.trim()
  return Boolean(
    isEnterprise.value
      && normalized
      && normalized !== branding.value?.platform_name
      && !savingName.value,
  )
})

watch(
  () => branding.value?.platform_name,
  (value) => {
    name.value = value ?? ''
  },
  { immediate: true },
)

async function saveName(): Promise<void> {
  if (!canSaveName.value) return
  savingName.value = true
  try {
    await updatePlatformName(name.value.trim())
    await refresh()
    applyToDocument()
  } finally {
    savingName.value = false
  }
}

async function handleLogo(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadingLogo.value = true
  try {
    await uploadLogo(file)
    await refresh()
  } finally {
    uploadingLogo.value = false
    input.value = ''
  }
}

async function handleFavicon(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadingFavicon.value = true
  try {
    await uploadFavicon(file)
    await refresh()
    applyToDocument()
  } finally {
    uploadingFavicon.value = false
    input.value = ''
  }
}

async function handleSquareLogo(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadingSquareLogo.value = true
  try {
    await uploadSquareLogo(file)
    await refresh()
  } finally {
    uploadingSquareLogo.value = false
    input.value = ''
  }
}

function goLicense(): void {
  void router.push('/system/license')
}

onMounted(async () => {
  if (!branding.value) await refresh()
})
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6">
    <header>
      <h1 class="text-xl font-semibold text-slate-950">品牌定制</h1>
      <p class="mt-1 text-sm text-slate-500">平台名称与品牌资产</p>
    </header>

    <section
      v-if="!isEnterprise"
      class="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-amber-200 bg-amber-50 px-5 py-4"
    >
      <div class="flex items-center gap-3">
        <LockKeyhole class="h-5 w-5 text-amber-700" />
        <div>
          <p class="text-sm font-semibold text-amber-900">需要企业版授权</p>
          <p class="mt-0.5 text-sm text-amber-700">当前品牌配置保持默认状态</p>
        </div>
      </div>
      <button
        class="inline-flex h-9 items-center gap-2 rounded-md border border-amber-300 bg-white px-3 text-sm font-medium text-amber-800 transition-colors hover:bg-amber-100"
        @click="goLicense"
      >
        <KeyRound class="h-4 w-4" />
        License 授权
      </button>
    </section>

    <template v-else>
      <section class="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div class="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
          <Palette class="h-5 w-5 text-slate-600" />
          <h2 class="text-sm font-semibold text-slate-900">平台名称</h2>
        </div>
        <div class="flex flex-wrap items-end gap-3 px-5 py-5">
          <label class="min-w-[15rem] flex-1">
            <span class="mb-1.5 block text-xs font-medium text-slate-600">显示名称</span>
            <input
              v-model="name"
              maxlength="100"
              class="h-10 w-full rounded-md border border-slate-300 px-3 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
              @keyup.enter="saveName"
            />
          </label>
          <button
            class="inline-flex h-10 items-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!canSaveName"
            @click="saveName"
          >
            <LoaderCircle v-if="savingName" class="h-4 w-4 animate-spin" />
            <Save v-else class="h-4 w-4" />
            保存
          </button>
        </div>
      </section>

      <section class="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div class="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
          <ImageUp class="h-5 w-5 text-slate-600" />
          <h2 class="text-sm font-semibold text-slate-900">品牌资产</h2>
        </div>

        <div class="divide-y divide-slate-100">
          <div class="grid gap-5 px-5 py-5 md:grid-cols-[9rem_1fr_auto] md:items-center">
            <div class="flex h-20 items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 px-3">
              <img
                v-if="logoUrl"
                :src="logoUrl"
                :alt="branding?.platform_name || 'Logo'"
                class="max-h-12 max-w-full object-contain"
              />
              <Image v-else class="h-6 w-6 text-slate-300" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <p class="text-sm font-medium text-slate-900">Logo</p>
                <Check v-if="logoUrl" class="h-4 w-4 text-emerald-600" />
              </div>
              <p class="mt-1 text-xs text-slate-500">PNG 或 SVG，最大 10MB</p>
            </div>
            <label
              class="inline-flex h-9 cursor-pointer items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
              :class="uploadingLogo ? 'pointer-events-none opacity-60' : ''"
            >
              <LoaderCircle v-if="uploadingLogo" class="h-4 w-4 animate-spin" />
              <Upload v-else class="h-4 w-4" />
              {{ logoUrl ? '替换' : '上传' }}
              <input
                type="file"
                accept=".png,.svg,image/png,image/svg+xml"
                class="hidden"
                :disabled="uploadingLogo"
                @change="handleLogo"
              />
            </label>
          </div>

          <div class="grid gap-5 px-5 py-5 md:grid-cols-[9rem_1fr_auto] md:items-center">
            <div class="flex h-20 items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50">
              <img
                v-if="squareLogoUrl"
                :src="squareLogoUrl"
                :alt="`${branding?.platform_name || 'AIHelms'} 方形 Logo`"
                class="h-12 w-12 object-contain"
              />
              <Image v-else class="h-6 w-6 text-slate-300" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <p class="text-sm font-medium text-slate-900">方形 Logo</p>
                <Check v-if="branding?.has_square_logo" class="h-4 w-4 text-emerald-600" />
              </div>
              <p class="mt-1 text-xs text-slate-500">PNG 或 SVG，正方形，建议 256×256，最大 2MB</p>
            </div>
            <label
              class="inline-flex h-9 cursor-pointer items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
              :class="uploadingSquareLogo ? 'pointer-events-none opacity-60' : ''"
            >
              <LoaderCircle v-if="uploadingSquareLogo" class="h-4 w-4 animate-spin" />
              <Upload v-else class="h-4 w-4" />
              {{ branding?.has_square_logo ? '替换' : '上传' }}
              <input
                type="file"
                accept=".png,.svg,image/png,image/svg+xml"
                class="hidden"
                :disabled="uploadingSquareLogo"
                @change="handleSquareLogo"
              />
            </label>
          </div>

          <div class="grid gap-5 px-5 py-5 md:grid-cols-[9rem_1fr_auto] md:items-center">
            <div class="flex h-20 items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50">
              <img
                v-if="faviconUrl"
                :src="faviconUrl"
                alt="Favicon"
                class="h-8 w-8 object-contain"
              />
              <Image v-else class="h-6 w-6 text-slate-300" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <p class="text-sm font-medium text-slate-900">Favicon</p>
                <Check v-if="faviconUrl" class="h-4 w-4 text-emerald-600" />
              </div>
              <p class="mt-1 text-xs text-slate-500">ICO 或 PNG，最大 200KB</p>
            </div>
            <label
              class="inline-flex h-9 cursor-pointer items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
              :class="uploadingFavicon ? 'pointer-events-none opacity-60' : ''"
            >
              <LoaderCircle v-if="uploadingFavicon" class="h-4 w-4 animate-spin" />
              <Upload v-else class="h-4 w-4" />
              {{ faviconUrl ? '替换' : '上传' }}
              <input
                type="file"
                accept=".ico,.png,image/x-icon,image/png"
                class="hidden"
                :disabled="uploadingFavicon"
                @change="handleFavicon"
              />
            </label>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
