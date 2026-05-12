<script setup lang="ts">
import { useAuth } from '@aihelms/shared'

const { currentUser } = useAuth()
</script>

<template>
  <div>
    <h2 class="mb-6 text-xl font-semibold text-slate-900">仪表盘</h2>
    <div class="rounded-2xl border border-slate-200/60 bg-white/70 p-6 shadow-sm backdrop-blur-xl">
      <p class="text-slate-600">
        欢迎回来，<span class="font-medium text-slate-900">{{ currentUser?.username }}</span>
      </p>
    </div>
  </div>
</template>
