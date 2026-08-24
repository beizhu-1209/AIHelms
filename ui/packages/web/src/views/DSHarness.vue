<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createDshSession, getPublicConfig } from '@aihelms/shared'

const router = useRouter()
const isLoading = ref(true)
const hasError = ref(false)
const isReady = ref(false)

async function checkFeature(): Promise<void> {
  try {
    const config = await getPublicConfig()
    if (!config.dsh_enabled) {
      await router.replace('/')
      return
    }
    await createDshSession()
    isReady.value = true
  } catch {
    hasError.value = true
  } finally {
    isLoading.value = false
  }
}

function handleFrameLoad(): void {
  isLoading.value = false
}

onMounted(() => {
  void checkFeature()
})
</script>

<template>
  <section class="relative h-[calc(100vh-60px)] min-h-[560px] bg-slate-100">
    <div v-if="isLoading && !hasError" class="absolute inset-0 z-10 flex items-center justify-center bg-white">
      <span class="text-sm text-slate-500">{{ $t('dsh.loading') }}</span>
    </div>
    <div v-if="hasError" class="flex h-full items-center justify-center bg-white">
      <span class="text-sm text-red-500">{{ $t('dsh.unavailable') }}</span>
    </div>
    <iframe
      v-else-if="isReady"
      :title="$t('dsh.title')"
      src="/dsh/"
      class="h-full w-full border-0"
      allow="clipboard-read; clipboard-write"
      @load="handleFrameLoad"
    />
  </section>
</template>
