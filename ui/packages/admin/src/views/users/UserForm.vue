<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getUserById,
  createUser,
  updateUser,
  resetUserPassword,
  updateUserRoles,
  getRoles,
  type Role,
} from '@aihelms/shared'

const route = useRoute()
const router = useRouter()

const userId = computed(() => route.params.id ? Number(route.params.id) : null)
const isEdit = computed(() => !!userId.value)

const username = ref('')
const email = ref('')
const password = ref('')
const isActive = ref(true)
const selectedRoleIds = ref<number[]>([])
const allRoles = ref<Role[]>([])
const newPassword = ref('')
const errorMessage = ref('')
const isLoading = ref(false)

async function fetchData(): Promise<void> {
  allRoles.value = await getRoles()
  if (isEdit.value && userId.value) {
    const user = await getUserById(userId.value)
    username.value = user.username
    email.value = user.email
    isActive.value = user.is_active
    selectedRoleIds.value = user.roles.map((r) => r.id)
  }
}

async function handleSubmit(): Promise<void> {
  errorMessage.value = ''
  isLoading.value = true
  try {
    if (isEdit.value && userId.value) {
      await updateUser(userId.value, { email: email.value, is_active: isActive.value })
      await updateUserRoles(userId.value, selectedRoleIds.value)
      if (newPassword.value) {
        await resetUserPassword(userId.value, newPassword.value)
      }
    } else {
      if (!username.value || !email.value || !password.value) {
        errorMessage.value = '请填写所有必填项'
        return
      }
      await createUser({
        username: username.value,
        email: email.value,
        password: password.value,
        is_active: isActive.value,
      })
    }
    router.push({ name: 'UserList' })
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    isLoading.value = false
  }
}

function handleCancel(): void {
  router.push({ name: 'UserList' })
}

function toggleRole(roleId: number): void {
  const idx = selectedRoleIds.value.indexOf(roleId)
  if (idx >= 0) {
    selectedRoleIds.value.splice(idx, 1)
  } else {
    selectedRoleIds.value.push(roleId)
  }
}

onMounted(fetchData)
</script>

<template>
  <div>
    <h2 class="mb-6 text-xl font-semibold text-slate-900">
      {{ isEdit ? '编辑用户' : '新建用户' }}
    </h2>

    <div class="max-w-lg rounded-2xl border border-slate-200/60 bg-white/70 p-6 shadow-sm backdrop-blur-xl">
      <form @submit.prevent="handleSubmit">
        <div class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">用户名</label>
          <input
            v-model="username"
            type="text"
            :disabled="isEdit"
            class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20 disabled:bg-slate-50 disabled:text-slate-400"
          />
        </div>

        <div class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">邮箱</label>
          <input
            v-model="email"
            type="email"
            class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
          />
        </div>

        <div v-if="!isEdit" class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">密码</label>
          <input
            v-model="password"
            type="password"
            class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
          />
        </div>

        <div v-if="isEdit" class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">重置密码（留空不修改）</label>
          <input
            v-model="newPassword"
            type="password"
            placeholder="输入新密码"
            class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
          />
        </div>

        <div class="mb-4">
          <label class="flex items-center gap-2 text-sm font-medium text-slate-700">
            <input
              v-model="isActive"
              type="checkbox"
              class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
            />
            启用
          </label>
        </div>

        <div class="mb-5">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">角色</label>
          <div class="flex flex-wrap gap-2">
            <label
              v-for="role in allRoles"
              :key="role.id"
              class="flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 transition-colors hover:bg-slate-50"
              :class="selectedRoleIds.includes(role.id) ? 'border-purple-300 bg-purple-50 text-purple-700' : ''"
            >
              <input
                type="checkbox"
                :checked="selectedRoleIds.includes(role.id)"
                class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
                @change="toggleRole(role.id)"
              />
              {{ role.display_name }}
            </label>
          </div>
        </div>

        <p v-if="errorMessage" class="mb-4 text-sm text-red-500">{{ errorMessage }}</p>

        <div class="flex gap-3">
          <button
            type="submit"
            :disabled="isLoading"
            class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {{ isLoading ? '保存中...' : '保存' }}
          </button>
          <button
            type="button"
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
            @click="handleCancel"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
