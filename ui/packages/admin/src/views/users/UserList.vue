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
    <div class="mb-6 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-slate-900">用户管理</h2>
      <button
        v-if="hasPermission('user:create')"
        class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]"
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
        class="flex h-11 rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
        @keyup.enter="handleSearch"
      />
      <button
        class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
        @click="handleSearch"
      >
        搜索
      </button>
    </div>

    <div class="overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-slate-200/60 bg-slate-50/50">
          <tr>
            <th class="px-4 py-3 font-medium text-slate-600">ID</th>
            <th class="px-4 py-3 font-medium text-slate-600">用户名</th>
            <th class="px-4 py-3 font-medium text-slate-600">邮箱</th>
            <th class="px-4 py-3 font-medium text-slate-600">角色</th>
            <th class="px-4 py-3 font-medium text-slate-600">状态</th>
            <th class="px-4 py-3 font-medium text-slate-600">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="6" class="px-4 py-8 text-center text-slate-400">加载中...</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="6" class="px-4 py-8 text-center text-slate-400">暂无数据</td>
          </tr>
          <tr v-for="user in users" :key="user.id" class="border-b border-slate-100 last:border-0">
            <td class="px-4 py-3 text-slate-600">{{ user.id }}</td>
            <td class="px-4 py-3 font-medium text-slate-900">{{ user.username }}</td>
            <td class="px-4 py-3 text-slate-600">{{ user.email }}</td>
            <td class="px-4 py-3">
              <span
                v-for="role in user.roles"
                :key="role.id"
                class="mr-1 inline-block rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700"
              >
                {{ role.display_name }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span
                :class="user.is_active ? 'text-green-600' : 'text-red-500'"
                class="text-xs font-medium"
              >
                {{ user.is_active ? '正常' : '已禁用' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex gap-3">
                <button
                  v-if="hasPermission('user:update')"
                  class="text-sm text-blue-600 transition-colors hover:text-blue-700"
                  @click="handleEdit(user)"
                >
                  编辑
                </button>
                <button
                  v-if="hasPermission('user:delete') && !user.is_admin"
                  class="text-sm text-red-500 transition-colors hover:text-red-600"
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
