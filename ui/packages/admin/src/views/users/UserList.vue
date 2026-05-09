<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getUsers, deleteUser, type User } from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import Pagination from '../../components/Pagination.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const router = useRouter()
const { hasPermission } = usePermission()

const users = ref<User[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const isLoading = ref(false)
const deleteTarget = ref<User | null>(null)

async function fetchUsers(): Promise<void> {
  isLoading.value = true
  try {
    const result = await getUsers(page.value, pageSize.value, keyword.value)
    users.value = result.items
    total.value = result.total
  } finally {
    isLoading.value = false
  }
}

function handleSearch(): void {
  page.value = 1
  fetchUsers()
}

function handlePageChange(newPage: number): void {
  page.value = newPage
  fetchUsers()
}

function handleCreate(): void {
  router.push({ name: 'UserCreate' })
}

function handleEdit(user: User): void {
  router.push({ name: 'UserEdit', params: { id: user.id } })
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  await deleteUser(deleteTarget.value.id)
  deleteTarget.value = null
  fetchUsers()
}

onMounted(fetchUsers)
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900">用户管理</h2>
      <button
        v-if="hasPermission('user:create')"
        class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
        @click="handleCreate"
      >
        新建用户
      </button>
    </div>

    <div class="mb-4 flex gap-2">
      <input
        v-model="keyword"
        type="text"
        placeholder="搜索用户名或邮箱"
        class="rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        @keyup.enter="handleSearch"
      />
      <button
        class="rounded-md bg-gray-200 px-4 py-2 text-sm hover:bg-gray-300"
        @click="handleSearch"
      >
        搜索
      </button>
    </div>

    <div class="overflow-hidden rounded-lg bg-white shadow-sm">
      <table class="w-full text-left text-sm">
        <thead class="border-b bg-gray-50">
          <tr>
            <th class="px-4 py-3 font-medium text-gray-700">ID</th>
            <th class="px-4 py-3 font-medium text-gray-700">用户名</th>
            <th class="px-4 py-3 font-medium text-gray-700">邮箱</th>
            <th class="px-4 py-3 font-medium text-gray-700">角色</th>
            <th class="px-4 py-3 font-medium text-gray-700">状态</th>
            <th class="px-4 py-3 font-medium text-gray-700">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="6" class="px-4 py-8 text-center text-gray-500">加载中...</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="6" class="px-4 py-8 text-center text-gray-500">暂无数据</td>
          </tr>
          <tr v-for="user in users" :key="user.id" class="border-b last:border-0">
            <td class="px-4 py-3">{{ user.id }}</td>
            <td class="px-4 py-3 font-medium">{{ user.username }}</td>
            <td class="px-4 py-3">{{ user.email }}</td>
            <td class="px-4 py-3">
              <span
                v-for="role in user.roles"
                :key="role.id"
                class="mr-1 inline-block rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700"
              >
                {{ role.display_name }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span
                :class="user.is_active ? 'text-green-600' : 'text-red-600'"
                class="text-xs font-medium"
              >
                {{ user.is_active ? '正常' : '已禁用' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex gap-2">
                <button
                  v-if="hasPermission('user:update')"
                  class="text-blue-600 hover:text-blue-800"
                  @click="handleEdit(user)"
                >
                  编辑
                </button>
                <button
                  v-if="hasPermission('user:delete') && !user.is_admin"
                  class="text-red-600 hover:text-red-800"
                  @click="deleteTarget = user"
                >
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination
      :page="page"
      :page-size="pageSize"
      :total="total"
      @change="handlePageChange"
    />

    <ConfirmDialog
      :visible="!!deleteTarget"
      title="确认删除"
      :message="`确定要禁用用户「${deleteTarget?.username}」吗？`"
      @confirm="handleConfirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>
