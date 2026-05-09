<script setup lang="ts">
import { useAuth } from '@aihelms/shared'

const { currentUser } = useAuth()
</script>

<template>
  <div>
    <h2 class="mb-4 text-xl font-semibold text-gray-900">仪表盘</h2>
    <div class="rounded-lg bg-white p-6 shadow-sm">
      <p class="text-gray-600">
        欢迎回来，<span class="font-medium text-gray-900">{{ currentUser?.username }}</span>
      </p>
    </div>
  </div>
</template>
