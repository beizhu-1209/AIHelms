<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getUserById,
  createUser,
  updateUser,
  resetUserPassword,
  updateUserRoles,
  updateUserDepartments,
  updateUserProjects,
  getRoles,
  getDepartmentTree,
  getProjects,
  type Role,
  type DeptTreeNode,
} from '@aihelms/shared'

const route = useRoute()
const router = useRouter()

const userId = computed(() => route.params.id ? Number(route.params.id) : null)
const isEdit = computed(() => !!userId.value)

const username = ref('')
const email = ref('')
const password = ref('')
const phone = ref('')
const displayName = ref('')
const position = ref('')
const avatar = ref('')
const isActive = ref(true)
const selectedRoleIds = ref<number[]>([])
const selectedDeptIds = ref<number[]>([])
const selectedProjectIds = ref<number[]>([])
const allRoles = ref<Role[]>([])
const deptTree = ref<DeptTreeNode[]>([])
const allProjects = ref<{ id: number; name: string }[]>([])
const newPassword = ref('')
const errorMessage = ref('')
const isLoading = ref(false)

const showDeptPicker = ref(false)
const deptSearchKeyword = ref('')

interface FlatDept {
  id: number
  name: string
  depth: number
}

function flattenDeptTree(nodes: DeptTreeNode[], depth: number = 0): FlatDept[] {
  const result: FlatDept[] = []
  for (const node of nodes) {
    result.push({ id: node.id, name: node.name, depth })
    if (node.children.length > 0) {
      result.push(...flattenDeptTree(node.children, depth + 1))
    }
  }
  return result
}

const flatDepts = computed(() => flattenDeptTree(deptTree.value))

const assignableRoles = computed(() =>
  allRoles.value.filter((r: Role) => r.name !== 'super_admin' && r.name !== 'department_manager')
)

const filteredDepts = computed(() => {
  if (!deptSearchKeyword.value) return flatDepts.value
  const kw = deptSearchKeyword.value.toLowerCase()
  return flatDepts.value.filter(d => d.name.toLowerCase().includes(kw))
})

const selectedDeptNames = computed(() => {
  const idSet = new Set(selectedDeptIds.value)
  return flatDepts.value.filter(d => idSet.has(d.id)).map(d => d.name)
})

function toggleDept(deptId: number): void {
  const idx = selectedDeptIds.value.indexOf(deptId)
  if (idx >= 0) {
    selectedDeptIds.value.splice(idx, 1)
  } else {
    selectedDeptIds.value.push(deptId)
  }
}

function removeDept(deptId: number): void {
  const idx = selectedDeptIds.value.indexOf(deptId)
  if (idx >= 0) selectedDeptIds.value.splice(idx, 1)
}

function toggleProject(projectId: number): void {
  const idx = selectedProjectIds.value.indexOf(projectId)
  if (idx >= 0) {
    selectedProjectIds.value.splice(idx, 1)
  } else {
    selectedProjectIds.value.push(projectId)
  }
}

function toggleRole(roleId: number): void {
  const idx = selectedRoleIds.value.indexOf(roleId)
  if (idx >= 0) {
    selectedRoleIds.value.splice(idx, 1)
  } else {
    selectedRoleIds.value.push(roleId)
  }
}

async function fetchData(): Promise<void> {
  const [roles, tree, projects] = await Promise.all([
    getRoles(),
    getDepartmentTree(),
    getProjects(1, 100),
  ])
  allRoles.value = roles
  deptTree.value = tree
  allProjects.value = projects.items.map((p: { id: number; name: string }) => ({ id: p.id, name: p.name }))

  if (isEdit.value && userId.value) {
    const user = await getUserById(userId.value)
    username.value = user.username
    email.value = user.email
    phone.value = user.phone || ''
    displayName.value = user.display_name || ''
    position.value = user.position || ''
    avatar.value = user.avatar || ''
    isActive.value = user.is_active
    selectedRoleIds.value = user.roles.map((r: { id: number }) => r.id)
    selectedDeptIds.value = user.departments.map((d: { id: number }) => d.id)
    selectedProjectIds.value = user.projects.map((p: { id: number }) => p.id)
  }
}

async function handleSubmit(): Promise<void> {
  errorMessage.value = ''
  isLoading.value = true
  try {
    if (isEdit.value && userId.value) {
      await updateUser(userId.value, {
        email: email.value,
        phone: phone.value,
        display_name: displayName.value,
        position: position.value,
        avatar: avatar.value,
        is_active: isActive.value,
      })
      await Promise.all([
        updateUserRoles(userId.value, selectedRoleIds.value),
        updateUserDepartments(userId.value, selectedDeptIds.value),
        updateUserProjects(userId.value, selectedProjectIds.value),
      ])
      if (newPassword.value) {
        await resetUserPassword(userId.value, newPassword.value)
      }
    } else {
      if (!username.value || !email.value || !password.value) {
        errorMessage.value = '请填写所有必填项'
        return
      }
      const user = await createUser({
        username: username.value,
        email: email.value,
        password: password.value,
        phone: phone.value,
        display_name: displayName.value,
        position: position.value,
        avatar: avatar.value,
        is_active: isActive.value,
      })
      await Promise.all([
        updateUserRoles(user.id, selectedRoleIds.value),
        updateUserDepartments(user.id, selectedDeptIds.value),
        updateUserProjects(user.id, selectedProjectIds.value),
      ])
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

onMounted(fetchData)
</script>

<template>
  <div class="flex h-full items-start justify-center py-6">
    <div class="w-full max-w-2xl rounded-2xl border border-slate-200/60 bg-white/70 p-8 shadow-sm backdrop-blur-xl">
      <h2 class="mb-6 text-xl font-semibold text-slate-900">
        {{ isEdit ? '编辑用户' : '新建用户' }}
      </h2>

      <form @submit.prevent="handleSubmit">
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label class="mb-1.5 block text-sm font-medium text-slate-700">用户名 *</label>
            <input
              v-model="username"
              type="text"
              :disabled="isEdit"
              class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20 disabled:bg-slate-50 disabled:text-slate-400"
            />
          </div>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-slate-700">邮箱 *</label>
            <input
              v-model="email"
              type="email"
              class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label class="mb-1.5 block text-sm font-medium text-slate-700">姓名</label>
            <input
              v-model="displayName"
              type="text"
              class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-slate-700">手机号</label>
            <input
              v-model="phone"
              type="text"
              class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
        </div>

        <div class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">职位</label>
          <input
            v-model="position"
            type="text"
            class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
          />
        </div>

        <div class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">头像</label>
          <div class="flex items-center gap-3">
            <div class="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
              <img v-if="avatar" :src="avatar" alt="" class="h-full w-full object-cover" />
              <span v-else class="text-xs text-slate-400">无</span>
            </div>
            <input
              v-model="avatar"
              type="text"
              placeholder="头像 URL（可选）"
              class="flex h-11 flex-1 rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
        </div>

        <div v-if="!isEdit" class="mb-4">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">密码 *</label>
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

        <!-- 角色选择 -->
        <div class="mb-5">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">角色</label>
          <div class="flex flex-wrap gap-2">
            <label
              v-for="role in assignableRoles"
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

        <!-- 部门选择 - 穿梭框 -->
        <div class="mb-5">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">部门</label>
          <div class="flex flex-wrap gap-1.5 mb-2" v-if="selectedDeptIds.length > 0">
            <span
              v-for="(name, idx) in selectedDeptNames"
              :key="idx"
              class="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700"
            >
              {{ name }}
              <button
                type="button"
                class="text-blue-400 hover:text-blue-600"
                @click="removeDept(selectedDeptIds[idx])"
              >
                &times;
              </button>
            </span>
          </div>
          <button
            type="button"
            class="rounded-lg border border-dashed border-slate-300 px-4 py-2 text-sm text-slate-500 transition-colors hover:border-purple-400 hover:text-purple-600"
            @click="showDeptPicker = true"
          >
            选择部门
          </button>
        </div>

        <!-- 项目选择 - 多选 -->
        <div class="mb-5">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">项目</label>
          <div class="flex flex-wrap gap-2">
            <label
              v-for="proj in allProjects"
              :key="proj.id"
              class="flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 transition-colors hover:bg-slate-50"
              :class="selectedProjectIds.includes(proj.id) ? 'border-green-300 bg-green-50 text-green-700' : ''"
            >
              <input
                type="checkbox"
                :checked="selectedProjectIds.includes(proj.id)"
                class="h-4 w-4 rounded border-slate-300 text-green-600 focus:ring-green-500/20"
                @change="toggleProject(proj.id)"
              />
              {{ proj.name }}
            </label>
          </div>
          <p v-if="allProjects.length === 0" class="text-sm text-slate-400">暂无项目</p>
        </div>

        <p v-if="errorMessage" class="mb-4 text-sm text-red-500">{{ errorMessage }}</p>

        <div class="flex gap-3">
          <button
            type="submit"
            :disabled="isLoading"
            class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {{ isLoading ? '保存中...' : '保存' }}
          </button>
          <button
            type="button"
            class="rounded-lg bg-slate-100 px-5 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
            @click="handleCancel"
          >
            取消
          </button>
        </div>
      </form>
    </div>

    <!-- 部门穿梭框弹窗 -->
    <div v-if="showDeptPicker" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-xl rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">选择部门</h3>
        <div class="flex gap-4">
          <!-- 左侧：部门树 -->
          <div class="flex-1">
            <div class="mb-2">
              <input
                v-model="deptSearchKeyword"
                placeholder="搜索部门名称"
                class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
              />
            </div>
            <div class="h-64 overflow-y-auto rounded-lg border border-slate-200 bg-white">
              <div
                v-for="dept in filteredDepts"
                :key="dept.id"
                class="flex cursor-pointer items-center gap-2 px-3 py-2 transition-colors hover:bg-slate-50"
                :class="selectedDeptIds.includes(dept.id) ? 'bg-blue-50' : ''"
                :style="{ paddingLeft: (dept.depth * 20 + 12) + 'px' }"
                @click="toggleDept(dept.id)"
              >
                <input
                  type="checkbox"
                  :checked="selectedDeptIds.includes(dept.id)"
                  class="h-3.5 w-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500/20"
                  @click.stop
                  @change="toggleDept(dept.id)"
                />
                <span class="text-sm text-slate-700">{{ dept.name }}</span>
              </div>
              <div v-if="filteredDepts.length === 0" class="py-8 text-center text-sm text-slate-400">无匹配部门</div>
            </div>
          </div>

          <!-- 右侧：已选 -->
          <div class="w-44 shrink-0">
            <div class="mb-2 flex h-10 items-center">
              <span class="text-sm font-medium text-slate-700">已选 {{ selectedDeptIds.length }} 个</span>
            </div>
            <div class="h-64 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50/50">
              <div
                v-for="dept in flatDepts.filter(d => selectedDeptIds.includes(d.id))"
                :key="dept.id"
                class="flex items-center justify-between px-3 py-2"
              >
                <span class="truncate text-sm text-slate-700">{{ dept.name }}</span>
                <button
                  type="button"
                  class="shrink-0 text-xs text-red-400 transition-colors hover:text-red-600"
                  @click="removeDept(dept.id)"
                >
                  移除
                </button>
              </div>
              <div v-if="selectedDeptIds.length === 0" class="py-8 text-center text-sm text-slate-400">请从左侧选择</div>
            </div>
          </div>
        </div>

        <div class="mt-4 flex justify-end">
          <button
            type="button"
            class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-purple-500"
            @click="showDeptPicker = false; deptSearchKeyword = ''"
          >
            确定
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
