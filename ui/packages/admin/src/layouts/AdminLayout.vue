<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth, useBranding, useLicense } from '@aihelms/shared'
import Sidebar from '../components/Sidebar.vue'
import HeaderBar from '../components/HeaderBar.vue'

const { fetchCurrentUser } = useAuth()
const { refresh: refreshLicense } = useLicense()
const { refresh: refreshBranding, applyToDocument } = useBranding()
const sidebarOpen = ref(false)

onMounted(async () => {
  await fetchCurrentUser()
  await Promise.all([refreshLicense(), refreshBranding()])
  applyToDocument()
})
</script>

<template>
  <div class="relative flex h-screen overflow-hidden bg-slate-50">
    <!-- 背景渐变色块 -->
    <div
      class="pointer-events-none absolute -left-60 -top-60 h-[600px] w-[600px] animate-blob rounded-full bg-purple-200/30 blur-[140px]"
    />
    <div
      class="pointer-events-none absolute -bottom-60 -right-60 h-[600px] w-[600px] animate-blob-reverse rounded-full bg-blue-200/30 blur-[140px]"
    />
    <div
      class="pointer-events-none absolute left-1/2 top-1/3 h-[400px] w-[400px] -translate-x-1/2 animate-blob-slow rounded-full bg-indigo-100/20 blur-[120px]"
    />

    <!-- 侧边栏 -->
    <Sidebar :open="sidebarOpen" @close="sidebarOpen = false" />
    <button
      v-if="sidebarOpen"
      class="fixed inset-0 z-30 bg-slate-950/35 md:hidden"
      type="button"
      aria-label="关闭导航遮罩"
      @click="sidebarOpen = false"
    />

    <!-- 右侧内容区 -->
    <div class="relative z-10 flex flex-1 flex-col overflow-hidden">
      <HeaderBar @toggle-sidebar="sidebarOpen = !sidebarOpen" />
      <main class="flex-1 overflow-y-auto p-4 sm:p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>
