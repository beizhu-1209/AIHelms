<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getUsers, updateUser, type User } from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import Pagination from '../../components/Pagination.vue'

const router = useRouter()
const { hasPermission } = usePermission()

const users = ref<User[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const filterRole = ref('')
const filterStatus = ref('')
const isLoading = ref(false)

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

async function handleToggleActive(user: User): Promise<void> {
  await updateUser(user.id, { is_active: !user.is_active })
  fetchUsers()
}

function getRoleLabel(user: User): string {
  const roleNames = user.roles.map(r => r.display_name)
  if (roleNames.length === 0) return '普通用户'
  return roleNames.join(', ')
}

function isAdmin(user: User): boolean {
  return user.roles.some(r => r.name === 'admin')
}

const filteredUsers = computed(() => {
  let result = users.value
  if (filterRole.value) {
    result = result.filter(u => {
      if (filterRole.value === 'admin') return u.roles.some(r => r.name === 'admin')
      if (filterRole.value === 'user') return !u.roles.some(r => r.name === 'admin')
      return true
    })
  }
  if (filterStatus.value) {
    result = result.filter(u => {
      if (filterStatus.value === 'active') return u.is_active
      if (filterStatus.value === 'disabled') return !u.is_active
      return true
    })
  }
  return result
})

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

    <div class="mb-4 flex flex-wrap items-center gap-3">
      <input
        v-model="keyword"
        type="text"
        placeholder="搜索用户名、姓名或邮箱"
        class="flex h-10 w-64 rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
        @keyup.enter="handleSearch"
      />
      <select
        v-model="filterRole"
        class="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
      >
        <option value="">全部角色</option>
        <option value="admin">管理员</option>
        <option value="user">普通用户</option>
      </select>
      <select
        v-model="filterStatus"
        class="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
      >
        <option value="">全部状态</option>
        <option value="active">正常</option>
        <option value="disabled">已禁用</option>
      </select>
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
            <th class="px-4 py-3 font-medium text-slate-600">用户名</th>
            <th class="px-4 py-3 font-medium text-slate-600">姓名</th>
            <th class="px-4 py-3 font-medium text-slate-600">邮箱</th>
            <th class="px-4 py-3 font-medium text-slate-600">
              <span class="group relative cursor-help">
                角色
                <span class="pointer-events-none absolute -top-16 left-0 z-10 w-56 rounded-lg bg-slate-800 px-3 py-2 text-xs font-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                  管理员：可管理平台日常运营<br/>普通用户：基础使用权限
                </span>
              </span>
            </th>
            <th class="px-4 py-3 font-medium text-slate-600">部门</th>
            <th class="px-4 py-3 font-medium text-slate-600">状态</th>
            <th class="px-4 py-3 font-medium text-slate-600">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="7" class="px-4 py-8 text-center text-slate-400">加载中...</td>
          </tr>
          <tr v-else-if="filteredUsers.length === 0">
            <td colspan="7" class="px-4 py-8 text-center text-slate-400">暂无数据</td>
          </tr>
          <tr v-for="user in filteredUsers" :key="user.id" class="border-b border-slate-100 last:border-0">
            <td class="px-4 py-3 font-medium text-slate-900">{{ user.username }}</td>
            <td class="px-4 py-3 text-slate-600">{{ user.display_name || '-' }}</td>
            <td class="px-4 py-3 text-slate-600">{{ user.email }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-block rounded-full px-2.5 py-0.5 text-xs font-medium"
                :class="isAdmin(user) ? 'bg-purple-50 text-purple-700' : 'bg-slate-100 text-slate-600'"
              >
                {{ getRoleLabel(user) }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span
                v-for="dept in user.departments"
                :key="dept.id"
                class="mr-1 inline-block rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700"
              >
                {{ dept.name }}
              </span>
              <span v-if="!user.departments || user.departments.length === 0" class="text-xs text-slate-400">-</span>
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
                  v-if="hasPermission('user:update')"
                  class="text-sm transition-colors"
                  :class="user.is_active ? 'text-orange-500 hover:text-orange-600' : 'text-green-600 hover:text-green-700'"
                  @click="handleToggleActive(user)"
                >
                  {{ user.is_active ? '禁用' : '启用' }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination
      :page="page"
      v-model:page-size="pageSize"
      :total="total"
      @change="handlePageChange"
    />
  </div>
</template>
