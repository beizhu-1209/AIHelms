<script setup lang="ts">
import { useAuth } from '@aihelms/shared'

const { currentUser, logout } = useAuth()

function handleLogout(): void {
  logout()
}
</script>

<template>
  <header class="flex h-14 items-center justify-between border-b border-slate-200/60 bg-white/70 px-6 backdrop-blur-lg">
    <div class="text-sm font-medium text-slate-700">管理后台</div>
    <div class="flex items-center gap-4">
      <span class="text-sm text-slate-600">{{ currentUser?.username }}</span>
      <button
        class="rounded-lg px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100/80"
        @click="handleLogout"
      >
        退出
      </button>
    </div>
  </header>
</template>
