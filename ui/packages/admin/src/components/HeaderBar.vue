<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Menu, ShieldAlert, ShieldCheck, ShieldOff } from 'lucide-vue-next'
import { useAuth, useBranding, useLicense } from '@aihelms/shared'

const { currentUser, logout } = useAuth()
const { status } = useLicense()
const { branding } = useBranding()
const router = useRouter()
const emit = defineEmits<{ toggleSidebar: [] }>()

const licenseLabel = computed(() => {
  if (status.value?.status === 'active') return '企业版'
  if (status.value?.status === 'expired') return '已过期'
  return '社区版'
})

const licenseTone = computed(() => {
  if (status.value?.status === 'active') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
  }
  if (status.value?.status === 'expired') {
    return 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100'
  }
  return 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'
})

const licenseTitle = computed(() => {
  if (!status.value?.licensed_to) return '查看 License 授权'
  const expiration = status.value.expires_at ? `，到期 ${status.value.expires_at}` : ''
  return `${status.value.licensed_to}${expiration}`
})

function handleLogout(): void {
  logout()
}

function goLicense(): void {
  void router.push('/system/license')
}
</script>

<template>
  <header class="flex h-14 items-center justify-between gap-2 border-b border-slate-200/60 bg-white/70 px-3 backdrop-blur-lg sm:px-6">
    <div class="flex min-w-0 items-center gap-2">
      <button
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-600 transition-colors hover:bg-slate-100 md:hidden"
        type="button"
        title="打开导航"
        aria-label="打开导航"
        @click="emit('toggleSidebar')"
      >
        <Menu class="h-5 w-5" />
      </button>
      <div class="hidden min-w-0 truncate text-sm font-medium text-slate-700 sm:block">
        {{ branding?.platform_name || 'AIHelms' }} 管理后台
      </div>
    </div>
    <div class="flex items-center gap-2 sm:gap-4">
      <button
        class="flex min-w-[5.25rem] items-center justify-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors"
        :class="licenseTone"
        :title="licenseTitle"
        @click="goLicense"
      >
        <ShieldCheck v-if="status?.status === 'active'" class="h-3.5 w-3.5" />
        <ShieldAlert v-else-if="status?.status === 'expired'" class="h-3.5 w-3.5" />
        <ShieldOff v-else class="h-3.5 w-3.5" />
        {{ licenseLabel }}
      </button>
      <span class="hidden text-sm text-slate-600 sm:inline">{{ currentUser?.username }}</span>
      <button
        class="rounded-lg px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100/80"
        @click="handleLogout"
      >
        退出
      </button>
    </div>
  </header>
</template>
