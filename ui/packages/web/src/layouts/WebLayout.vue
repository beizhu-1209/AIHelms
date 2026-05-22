<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@aihelms/shared'
import { LogOut, Settings } from 'lucide-vue-next'

const router = useRouter()
const { currentUser, fetchCurrentUser, logout } = useAuth()

onMounted(async () => {
  if (!currentUser.value) {
    await fetchCurrentUser()
  }
})

function handleLogout(): void {
  logout()
}

const currentPath = computed(() => router.currentRoute.value.path)

function isActive(path: string): boolean {
  if (path === '/') return currentPath.value === '/'
  return currentPath.value.startsWith(path)
}

const navItems = [
  { path: '/', label: '我的 AI 身份' },
  { path: '/market', label: 'AI 市场' },
  { path: '/models', label: '模型广场' },
  { path: '/agents', label: '智能体中心' },
]
</script>

<template>
  <div class="relative flex min-h-screen flex-col overflow-hidden bg-slate-50">
    <!-- 背景渐变色块 -->
    <div class="pointer-events-none absolute -left-60 -top-60 h-[600px] w-[600px] animate-blob rounded-full bg-purple-200/30 blur-[140px]" />
    <div class="pointer-events-none absolute -bottom-60 -right-60 h-[600px] w-[600px] animate-blob-reverse rounded-full bg-blue-200/30 blur-[140px]" />
    <div class="pointer-events-none absolute left-1/2 top-1/3 h-[400px] w-[400px] -translate-x-1/2 animate-blob-slow rounded-full bg-indigo-100/20 blur-[120px]" />

    <!-- 顶部导航 -->
    <header class="relative z-10 grid h-[60px] grid-cols-3 items-center border-b border-slate-200/60 bg-white/70 px-6 backdrop-blur-xl">
      <!-- 左：Logo -->
      <div class="flex items-center">
        <RouterLink to="/" class="flex items-center gap-2.5">
          <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 text-xs font-bold text-white shadow-md shadow-purple-500/20">
            AI
          </div>
          <span class="text-lg font-bold text-slate-900">AIHelms</span>
        </RouterLink>
      </div>

      <!-- 中：导航居中 -->
      <nav class="flex items-center justify-center gap-1">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path"
          class="whitespace-nowrap rounded-lg px-3.5 py-2 text-sm transition-colors"
          :class="isActive(item.path) ? 'bg-purple-50 font-medium text-purple-700' : 'text-slate-600 hover:bg-slate-100'">
          {{ item.label }}
        </RouterLink>
      </nav>

      <!-- 右：用户操作 -->
      <div class="flex items-center justify-end gap-3">
        <a v-if="currentUser?.is_admin" href="/admin/"
          class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100">
          <Settings class="h-4 w-4" />
          管理后台
        </a>
        <span class="text-sm text-slate-600">{{ currentUser?.username || '...' }}</span>
        <button @click="handleLogout"
          class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100">
          <LogOut class="h-4 w-4" />
        </button>
      </div>
    </header>

    <!-- 内容区 -->
    <main class="relative z-10 flex-1 overflow-y-auto">
      <RouterView />
    </main>
  </div>
</template>