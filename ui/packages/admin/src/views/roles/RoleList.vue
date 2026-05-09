<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getRoles,
  createRole,
  updateRole,
  deleteRole,
  updateRolePermissions,
  getPermissions,
  type Role,
  type Permission,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()

const roles = ref<Role[]>([])
const allPermissions = ref<Permission[]>([])
const selectedRole = ref<Role | null>(null)
const showForm = ref(false)
const isEditing = ref(false)
const showPermissionEditor = ref(false)
const deleteTarget = ref<Role | null>(null)

const formName = ref('')
const formDisplayName = ref('')
const formDescription = ref('')
const selectedPermissionIds = ref<number[]>([])
const errorMessage = ref('')

async function fetchData(): Promise<void> {
  roles.value = await getRoles()
  allPermissions.value = await getPermissions()
}

function handleCreate(): void {
  isEditing.value = false
  formName.value = ''
  formDisplayName.value = ''
  formDescription.value = ''
  errorMessage.value = ''
  showForm.value = true
}

function handleEdit(role: Role): void {
  isEditing.value = true
  selectedRole.value = role
  formDisplayName.value = role.display_name
  formDescription.value = role.description
  errorMessage.value = ''
  showForm.value = true
}

function handleEditPermissions(role: Role): void {
  selectedRole.value = role
  selectedPermissionIds.value = role.permissions.map((p) => p.id)
  showPermissionEditor.value = true
}

async function handleSubmit(): Promise<void> {
  errorMessage.value = ''
  try {
    if (isEditing.value && selectedRole.value) {
      await updateRole(selectedRole.value.id, {
        display_name: formDisplayName.value,
        description: formDescription.value,
      })
    } else {
      if (!formName.value || !formDisplayName.value) {
        errorMessage.value = '请填写必填项'
        return
      }
      await createRole({
        name: formName.value,
        display_name: formDisplayName.value,
        description: formDescription.value,
      })
    }
    showForm.value = false
    await fetchData()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleSavePermissions(): Promise<void> {
  if (!selectedRole.value) return
  try {
    await updateRolePermissions(selectedRole.value.id, selectedPermissionIds.value)
    showPermissionEditor.value = false
    await fetchData()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '保存失败'
  }
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  try {
    await deleteRole(deleteTarget.value.id)
    deleteTarget.value = null
    await fetchData()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '删除失败'
    deleteTarget.value = null
  }
}

function togglePermission(permId: number): void {
  const idx = selectedPermissionIds.value.indexOf(permId)
  if (idx >= 0) {
    selectedPermissionIds.value.splice(idx, 1)
  } else {
    selectedPermissionIds.value.push(permId)
  }
}

onMounted(fetchData)
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900">角色权限</h2>
      <button
        v-if="hasPermission('role:create')"
        class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
        @click="handleCreate"
      >
        新建角色
      </button>
    </div>

    <div class="overflow-hidden rounded-lg bg-white shadow-sm">
      <table class="w-full text-left text-sm">
        <thead class="border-b bg-gray-50">
          <tr>
            <th class="px-4 py-3 font-medium text-gray-700">角色名</th>
            <th class="px-4 py-3 font-medium text-gray-700">显示名</th>
            <th class="px-4 py-3 font-medium text-gray-700">描述</th>
            <th class="px-4 py-3 font-medium text-gray-700">权限数</th>
            <th class="px-4 py-3 font-medium text-gray-700">类型</th>
            <th class="px-4 py-3 font-medium text-gray-700">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="role in roles" :key="role.id" class="border-b last:border-0">
            <td class="px-4 py-3 font-medium">{{ role.name }}</td>
            <td class="px-4 py-3">{{ role.display_name }}</td>
            <td class="px-4 py-3 text-gray-600">{{ role.description || '-' }}</td>
            <td class="px-4 py-3">{{ role.permissions.length }}</td>
            <td class="px-4 py-3">
              <span
                :class="role.is_system ? 'bg-gray-100 text-gray-700' : 'bg-blue-100 text-blue-700'"
                class="rounded-full px-2 py-0.5 text-xs"
              >
                {{ role.is_system ? '系统' : '自定义' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex gap-2">
                <button
                  v-if="hasPermission('role:update') && !role.is_system"
                  class="text-blue-600 hover:text-blue-800"
                  @click="handleEdit(role)"
                >
                  编辑
                </button>
                <button
                  v-if="hasPermission('role:update') && !role.is_system"
                  class="text-blue-600 hover:text-blue-800"
                  @click="handleEditPermissions(role)"
                >
                  权限
                </button>
                <button
                  v-if="hasPermission('role:delete') && !role.is_system"
                  class="text-red-600 hover:text-red-800"
                  @click="deleteTarget = role"
                >
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 class="mb-4 text-lg font-semibold">{{ isEditing ? '编辑角色' : '新建角色' }}</h3>
        <form @submit.prevent="handleSubmit">
          <div v-if="!isEditing" class="mb-3">
            <label class="mb-1 block text-sm font-medium text-gray-700">角色标识</label>
            <input v-model="formName" class="w-full rounded-md border px-3 py-2 text-sm" placeholder="如 editor" />
          </div>
          <div class="mb-3">
            <label class="mb-1 block text-sm font-medium text-gray-700">显示名称</label>
            <input v-model="formDisplayName" class="w-full rounded-md border px-3 py-2 text-sm" />
          </div>
          <div class="mb-3">
            <label class="mb-1 block text-sm font-medium text-gray-700">描述</label>
            <textarea v-model="formDescription" rows="2" class="w-full rounded-md border px-3 py-2 text-sm" />
          </div>
          <p v-if="errorMessage" class="mb-3 text-sm text-red-600">{{ errorMessage }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-md border px-4 py-2 text-sm" @click="showForm = false">取消</button>
            <button type="submit" class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">保存</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showPermissionEditor" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h3 class="mb-4 text-lg font-semibold">
          编辑权限 - {{ selectedRole?.display_name }}
        </h3>
        <div class="mb-4 max-h-64 overflow-y-auto">
          <div
            v-for="perm in allPermissions"
            :key="perm.id"
            class="flex items-center gap-2 border-b py-2 last:border-0"
          >
            <input
              type="checkbox"
              :checked="selectedPermissionIds.includes(perm.id)"
              @change="togglePermission(perm.id)"
            />
            <span class="text-sm font-medium text-gray-800">{{ perm.name }}</span>
            <span class="text-xs text-gray-500">({{ perm.code }})</span>
          </div>
        </div>
        <div class="flex justify-end gap-3">
          <button class="rounded-md border px-4 py-2 text-sm" @click="showPermissionEditor = false">取消</button>
          <button class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700" @click="handleSavePermissions">保存</button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteTarget"
      title="确认删除"
      :message="`确定要删除角色「${deleteTarget?.display_name}」吗？`"
      @confirm="handleConfirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>
