<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, Languages } from 'lucide-vue-next'
import { getCurrentLocale, isSupportedLocale, setLocale, SUPPORTED_LOCALES, type AppLocale } from '../i18n'

const selectedLocale = ref<AppLocale>(getCurrentLocale())
const isOpen = ref(false)
const switcherRef = ref<HTMLElement | null>(null)

const localeLabels: Record<AppLocale, string> = {
  'zh-CN': '中文',
  'en-US': 'EN',
}

const localeNames: Record<AppLocale, string> = {
  'zh-CN': '中文',
  'en-US': 'English',
}

function selectLocale(locale: AppLocale): void {
  if (!isSupportedLocale(locale)) return
  selectedLocale.value = locale
  setLocale(locale)
  isOpen.value = false
}

function handleDocumentClick(event: MouseEvent): void {
  if (!switcherRef.value?.contains(event.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', handleDocumentClick))
</script>

<template>
  <div ref="switcherRef" class="relative">
    <button
      type="button"
      class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100"
      aria-label="Language"
      :aria-expanded="isOpen"
      @click.stop="isOpen = !isOpen"
    >
      <Languages class="h-4 w-4" />
      <span>{{ localeLabels[selectedLocale] }}</span>
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 z-50 mt-1 w-36 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
    >
      <button
        v-for="locale in SUPPORTED_LOCALES"
        :key="locale"
        type="button"
        class="flex w-full items-center justify-between px-4 py-2 text-sm text-slate-600 transition-colors hover:bg-slate-50"
        @click="selectLocale(locale)"
      >
        <span>{{ localeNames[locale] }}</span>
        <Check v-if="selectedLocale === locale" class="h-4 w-4 text-purple-600" />
      </button>
    </div>
  </div>
</template>
