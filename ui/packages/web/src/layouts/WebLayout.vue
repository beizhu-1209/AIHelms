<script setup lang="ts">
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth, changePassword } from '@aihelms/shared'
import { LogOut, Settings, KeyRound, ChevronDown } from 'lucide-vue-next'

const router = useRouter()
const { currentUser, fetchCurrentUser, logout } = useAuth()

onMounted(async () => {
  if (!currentUser.value) {
    await fetchCurrentUser()
  }
  document.addEventListener('click', handleGlobalClick, true)
})

onUnmounted(() => {
  document.removeEventListener('click', handleGlobalClick, true)
})

function handleGlobalClick(e: MouseEvent): void {
  const trigger = triggerRef.value
  const dropdown = dropdownRef.value
  const target = e.target as Node
  if (showDropdown.value && trigger && !trigger.contains(target) && (!dropdown || !dropdown.contains(target))) {
    showDropdown.value = false
  }
}

function handleLogout(): void {
  logout()
}

const currentPath = ref(router.currentRoute.value.path)
router.afterEach((to) => {
  currentPath.value = to.path
})

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

// 下拉菜单
const showDropdown = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)
const triggerRef = ref<HTMLElement | null>(null)
const dropdownStyle = ref({ top: '0px', right: '0px' })

function toggleDropdown(): void {
  showDropdown.value = !showDropdown.value
  if (showDropdown.value) {
    nextTick(() => {
      updateDropdownPosition()
    })
  }
}

function updateDropdownPosition(): void {
  if (!triggerRef.value) return
  const rect = triggerRef.value.getBoundingClientRect()
  dropdownStyle.value = {
    top: `${rect.bottom + 4}px`,
    right: `${window.innerWidth - rect.right}px`,
  }
}

function closeDropdown(): void {
  showDropdown.value = false
}

// 修改密码弹窗
const showPasswordModal = ref(false)
const passwordForm = ref({ oldPassword: '', newPassword: '', confirmPassword: '' })
const passwordError = ref('')
const passwordLoading = ref(false)

function handleOpenPasswordModal(): void {
  showDropdown.value = false
  showPasswordModal.value = true
}

async function handleChangePassword(): Promise<void> {
  passwordError.value = ''
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }
  passwordLoading.value = true
  try {
    await changePassword({
      old_password: passwordForm.value.oldPassword,
      new_password: passwordForm.value.newPassword,
    })
    showPasswordModal.value = false
    passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
    logout()
  } catch (e: unknown) {
    const err = e as { message?: string }
    passwordError.value = err.message || '修改失败，请重试'
  } finally {
    passwordLoading.value = false
  }
}
</script>

<template>
  <div class="relative flex min-h-screen flex-col overflow-hidden bg-slate-50">
    <!-- 背景渐变色块 -->
    <div class="pointer-events-none absolute -left-60 -top-60 h-[600px] w-[600px] animate-blob rounded-full bg-purple-200/30 blur-[140px]" />
    <div class="pointer-events-none absolute -bottom-60 -right-60 h-[600px] w-[600px] animate-blob-reverse rounded-full bg-blue-200/30 blur-[140px]" />
    <div class="pointer-events-none absolute left-1/2 top-1/3 h-[400px] w-[400px] -translate-x-1/2 animate-blob-slow rounded-full bg-indigo-100/20 blur-[120px]" />

    <!-- 顶部导航 -->
    <header class="relative z-30 grid h-[60px] grid-cols-3 items-center border-b border-slate-200/60 bg-white/70 px-6 backdrop-blur-xl">
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

        <!-- 用户下拉菜单 -->
        <div class="relative">
          <button ref="triggerRef" @click="toggleDropdown"
            class="flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100">
            <span>{{ currentUser?.display_name || currentUser?.email || currentUser?.username || '...' }}</span>
            <ChevronDown class="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </header>

    <!-- 内容区 -->
    <main class="relative z-10 flex-1 overflow-y-auto">
      <RouterView />
    </main>

    <!-- 下拉菜单（Teleport 到 body 避免 z-index 层叠问题） -->
    <Teleport to="body">
      <div v-if="showDropdown" ref="dropdownRef"
        class="fixed z-[9999] w-48 rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
        :style="dropdownStyle">
        <button @click="handleOpenPasswordModal"
          class="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50">
          <KeyRound class="h-4 w-4" />
          修改密码
        </button>
        <div class="my-1 border-t border-slate-100" />
        <button @click="handleLogout"
          class="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm text-red-500 hover:bg-slate-50">
          <LogOut class="h-4 w-4" />
          退出登录
        </button>
      </div>
    </Teleport>

    <!-- 修改密码弹窗 -->
    <Teleport to="body">
      <Transition enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0" enter-to-class="opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100" leave-to-class="opacity-0">
        <div v-if="showPasswordModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          @click.self="showPasswordModal = false">
          <div class="w-[400px] rounded-xl bg-white p-6 shadow-xl">
            <h3 class="mb-4 text-lg font-semibold text-slate-900">修改密码</h3>
            <form @submit.prevent="handleChangePassword" class="space-y-4">
              <div>
                <label class="mb-1 block text-sm text-slate-600">当前密码</label>
                <input v-model="passwordForm.oldPassword" type="password" required
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400" />
              </div>
              <div>
                <label class="mb-1 block text-sm text-slate-600">新密码</label>
                <input v-model="passwordForm.newPassword" type="password" required minlength="8"
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400" />
              </div>
              <div>
                <label class="mb-1 block text-sm text-slate-600">确认新密码</label>
                <input v-model="passwordForm.confirmPassword" type="password" required minlength="8"
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400" />
              </div>
              <p v-if="passwordError" class="text-sm text-red-500">{{ passwordError }}</p>
              <div class="flex justify-end gap-2 pt-2">
                <button type="button" @click="showPasswordModal = false"
                  class="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">
                  取消
                </button>
                <button type="submit" :disabled="passwordLoading"
                  class="rounded-lg bg-purple-600 px-4 py-2 text-sm text-white hover:bg-purple-700 disabled:opacity-50">
                  {{ passwordLoading ? '提交中...' : '确认修改' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
