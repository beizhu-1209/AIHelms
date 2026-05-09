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
    <h2 class="mb-4 text-xl font-semibold text-gray-900">
      {{ isEdit ? '编辑用户' : '新建用户' }}
    </h2>

    <div class="max-w-lg rounded-lg bg-white p-6 shadow-sm">
      <form @submit.prevent="handleSubmit">
        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700">用户名</label>
          <input
            v-model="username"
            type="text"
            :disabled="isEdit"
            class="w-full rounded-md border px-3 py-2 text-sm disabled:bg-gray-100"
          />
        </div>

        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700">邮箱</label>
          <input
            v-model="email"
            type="email"
            class="w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        <div v-if="!isEdit" class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700">密码</label>
          <input
            v-model="password"
            type="password"
            class="w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        <div v-if="isEdit" class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700">重置密码（留空不修改）</label>
          <input
            v-model="newPassword"
            type="password"
            placeholder="输入新密码"
            class="w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        <div class="mb-4">
          <label class="mb-1 flex items-center gap-2 text-sm font-medium text-gray-700">
            <input v-model="isActive" type="checkbox" class="rounded" />
            启用
          </label>
        </div>

        <div class="mb-4">
          <label class="mb-1 block text-sm font-medium text-gray-700">角色</label>
          <div class="flex flex-wrap gap-2">
            <label
              v-for="role in allRoles"
              :key="role.id"
              class="flex items-center gap-1 rounded-md border px-2 py-1 text-sm"
            >
              <input
                type="checkbox"
                :checked="selectedRoleIds.includes(role.id)"
                @change="toggleRole(role.id)"
              />
              {{ role.display_name }}
            </label>
          </div>
        </div>

        <p v-if="errorMessage" class="mb-4 text-sm text-red-600">{{ errorMessage }}</p>

        <div class="flex gap-3">
          <button
            type="submit"
            :disabled="isLoading"
            class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {{ isLoading ? '保存中...' : '保存' }}
          </button>
          <button
            type="button"
            class="rounded-md border px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            @click="handleCancel"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
