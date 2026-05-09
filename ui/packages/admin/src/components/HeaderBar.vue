<script setup lang="ts">
import { useAuth } from '@aihelms/shared'

const { currentUser, logout } = useAuth()

function handleLogout(): void {
  logout()
}
</script>

<template>
  <header class="flex h-14 items-center justify-between border-b bg-white px-6">
    <div class="text-sm text-gray-600">管理后台</div>
    <div class="flex items-center gap-4">
      <span class="text-sm text-gray-700">{{ currentUser?.username }}</span>
      <button
        class="rounded-md px-3 py-1 text-sm text-gray-600 hover:bg-gray-100"
        @click="handleLogout"
      >
        退出
      </button>
    </div>
  </header>
</template>
