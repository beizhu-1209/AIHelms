<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@aihelms/shared'

const router = useRouter()
const { t } = useI18n()
const { login } = useAuth()

const email = ref('')
const password = ref('')
const errorMessage = ref('')
const isLoading = ref(false)

async function handleLogin(): Promise<void> {
  if (!email.value || !password.value) {
    errorMessage.value = t('login.validation.required')
    return
  }
  isLoading.value = true
  try {
    await login(email.value, password.value)
    errorMessage.value = ''
    router.push('/')
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : t('login.error.invalidCredentials')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-50">
    <div class="absolute -left-40 -top-40 h-[500px] w-[500px] animate-blob rounded-full bg-purple-300/40 blur-[120px]" />
    <div class="absolute -bottom-40 -right-40 h-[500px] w-[500px] animate-blob-reverse rounded-full bg-blue-300/40 blur-[120px]" />
    <div class="absolute left-1/2 top-1/2 h-[400px] w-[400px] -translate-x-1/2 -translate-y-1/2 animate-blob-slow rounded-full bg-indigo-200/30 blur-[100px]" />

    <div class="relative z-10 w-full max-w-[420px] rounded-2xl border border-slate-200/60 bg-white/70 p-8 shadow-xl backdrop-blur-xl">
      <div class="mb-8 space-y-3 text-center">
        <div class="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-blue-600 text-sm font-bold text-white shadow-lg shadow-purple-500/30">
          AI
        </div>
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">{{ t('login.title') }}</h1>
        <p class="text-sm text-slate-500">{{ t('login.subtitle') }}</p>
      </div>

      <form class="space-y-5" @submit.prevent="handleLogin">
        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-700">{{ t('login.field.account') }}</label>
          <input v-model="email" type="text"
            class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            :placeholder="t('login.field.accountPlaceholder')" autocomplete="username" />
        </div>

        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-700">{{ t('login.field.password') }}</label>
          <input v-model="password" type="password"
            class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            :placeholder="t('login.field.passwordPlaceholder')" autocomplete="current-password" />
        </div>

        <p v-if="errorMessage" class="text-sm text-red-500">{{ errorMessage }}</p>

        <button type="submit" :disabled="isLoading"
          class="flex h-11 w-full items-center justify-center rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50">
          {{ isLoading ? t('login.status.submitting') : t('login.action.submit') }}
        </button>
      </form>

      <p class="mt-6 text-center text-xs text-slate-400">
        {{ t('login.adminPrompt') }}
        <a href="/admin/login" class="text-purple-600 hover:underline">{{ t('login.adminLink') }}</a>
      </p>
    </div>

    <p class="absolute bottom-6 left-1/2 -translate-x-1/2 text-xs text-slate-400">
      &copy; {{ new Date().getFullYear() }} AIHelms. {{ t('login.copyright') }}
    </p>
  </div>
</template>
