<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getOrganizations,
  getOrganizationTree,
  createOrganization,
  updateOrganization,
  updateOrgManagers,
  deleteOrganization,
  getUsers,
  type Organization,
  type OrgTreeNode,
  type User,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import OrgTree from '../../components/OrgTree.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()

const organizations = ref<Organization[]>([])
const tree = ref<OrgTreeNode[]>([])
const allUsers = ref<User[]>([])
const selectedOrg = ref<Organization | null>(null)
const showForm = ref(false)
const showManagerForm = ref(false)
const isEditing = ref(false)
const deleteTarget = ref<Organization | null>(null)

const formName = ref('')
const formType = ref<'department' | 'group'>('department')
const formParentId = ref<number | null>(null)
const formDescription = ref('')
const formSortOrder = ref(0)
const selectedManagerIds = ref<number[]>([])
const errorMessage = ref('')

async function fetchData(): Promise<void> {
  organizations.value = await getOrganizations()
  tree.value = await getOrganizationTree()
  const usersResult = await getUsers(1, 200)
  allUsers.value = usersResult.items
}

function handleTreeSelect(node: OrgTreeNode): void {
  const org = organizations.value.find((o) => o.id === node.id)
  if (org) {
    selectedOrg.value = org
  }
}

function handleCreate(parentId: number | null = null): void {
  isEditing.value = false
  formName.value = ''
  formType.value = 'department'
  formParentId.value = parentId
  formDescription.value = ''
  formSortOrder.value = 0
  errorMessage.value = ''
  showForm.value = true
}

function handleEdit(org: Organization): void {
  isEditing.value = true
  selectedOrg.value = org
  formName.value = org.name
  formType.value = org.type
  formDescription.value = org.description
  formSortOrder.value = org.sort_order
  errorMessage.value = ''
  showForm.value = true
}

function handleEditManagers(org: Organization): void {
  selectedOrg.value = org
  selectedManagerIds.value = org.managers.map((m) => m.id)
  errorMessage.value = ''
  showManagerForm.value = true
}

async function handleSubmit(): Promise<void> {
  if (!formName.value) {
    errorMessage.value = '请输入名称'
    return
  }
  errorMessage.value = ''
  try {
    if (isEditing.value && selectedOrg.value) {
      await updateOrganization(selectedOrg.value.id, {
        name: formName.value,
        description: formDescription.value,
        sort_order: formSortOrder.value,
      })
    } else {
      await createOrganization({
        name: formName.value,
        type: formType.value,
        parent_id: formParentId.value,
        description: formDescription.value,
        sort_order: formSortOrder.value,
      })
    }
    showForm.value = false
    await fetchData()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleSaveManagers(): Promise<void> {
  if (!selectedOrg.value) return
  try {
    await updateOrgManagers(selectedOrg.value.id, selectedManagerIds.value)
    showManagerForm.value = false
    await fetchData()
    const updated = organizations.value.find((o) => o.id === selectedOrg.value?.id)
    if (updated) selectedOrg.value = updated
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '保存失败'
  }
}

function toggleManager(userId: number): void {
  const idx = selectedManagerIds.value.indexOf(userId)
  if (idx >= 0) {
    selectedManagerIds.value.splice(idx, 1)
  } else {
    selectedManagerIds.value.push(userId)
  }
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  try {
    await deleteOrganization(deleteTarget.value.id)
    deleteTarget.value = null
    selectedOrg.value = null
    await fetchData()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '删除失败'
    deleteTarget.value = null
  }
}

onMounted(fetchData)
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900">部门管理</h2>
      <div class="flex gap-2">
        <button
          v-if="hasPermission('organization:create')"
          class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          @click="handleCreate(null)"
        >
          新建部门
        </button>
        <button
          v-if="hasPermission('organization:create')"
          class="rounded-md border px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          @click="formType = 'group'; handleCreate(null)"
        >
          新建项目组
        </button>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <h3 class="mb-3 text-sm font-medium text-gray-700">部门树</h3>
        <OrgTree
          v-if="tree.length"
          :nodes="tree"
          @select="handleTreeSelect"
        />
        <p v-else class="text-sm text-gray-500">暂无部门</p>

        <h3 class="mb-3 mt-6 text-sm font-medium text-gray-700">项目组</h3>
        <ul>
          <li
            v-for="org in organizations.filter(o => o.type === 'group')"
            :key="org.id"
            class="cursor-pointer rounded-md px-2 py-1 text-sm hover:bg-gray-100"
            @click="selectedOrg = org"
          >
            {{ org.name }}
            <span v-if="!org.is_active" class="ml-1 text-xs text-red-400">(已禁用)</span>
          </li>
        </ul>
      </div>

      <div class="rounded-lg bg-white p-4 shadow-sm">
        <h3 class="mb-3 text-sm font-medium text-gray-700">组织详情</h3>
        <div v-if="selectedOrg">
          <dl class="space-y-2 text-sm">
            <div class="flex">
              <dt class="w-20 text-gray-500">名称</dt>
              <dd class="text-gray-900">{{ selectedOrg.name }}</dd>
            </div>
            <div class="flex">
              <dt class="w-20 text-gray-500">类型</dt>
              <dd class="text-gray-900">{{ selectedOrg.type === 'department' ? '部门' : '项目组' }}</dd>
            </div>
            <div class="flex">
              <dt class="w-20 text-gray-500">负责人</dt>
              <dd class="text-gray-900">
                <template v-if="selectedOrg.managers.length">
                  <span
                    v-for="mgr in selectedOrg.managers"
                    :key="mgr.id"
                    class="mr-1 inline-block rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700"
                  >
                    {{ mgr.username }}
                  </span>
                </template>
                <span v-else class="text-gray-400">未设置</span>
              </dd>
            </div>
            <div class="flex">
              <dt class="w-20 text-gray-500">描述</dt>
              <dd class="text-gray-900">{{ selectedOrg.description || '-' }}</dd>
            </div>
            <div class="flex">
              <dt class="w-20 text-gray-500">状态</dt>
              <dd :class="selectedOrg.is_active ? 'text-green-600' : 'text-red-600'">
                {{ selectedOrg.is_active ? '正常' : '已禁用' }}
              </dd>
            </div>
          </dl>
          <div class="mt-4 flex flex-wrap gap-2">
            <button
              v-if="hasPermission('organization:create') && selectedOrg.type === 'department'"
              class="rounded-md border px-3 py-1 text-sm hover:bg-gray-50"
              @click="handleCreate(selectedOrg.id)"
            >
              添加子部门
            </button>
            <button
              v-if="hasPermission('organization:update')"
              class="rounded-md border px-3 py-1 text-sm text-blue-600 hover:bg-blue-50"
              @click="handleEdit(selectedOrg)"
            >
              编辑
            </button>
            <button
              v-if="hasPermission('organization:update')"
              class="rounded-md border px-3 py-1 text-sm text-green-600 hover:bg-green-50"
              @click="handleEditManagers(selectedOrg)"
            >
              设置负责人
            </button>
            <button
              v-if="hasPermission('organization:delete')"
              class="rounded-md border px-3 py-1 text-sm text-red-600 hover:bg-red-50"
              @click="deleteTarget = selectedOrg"
            >
              删除
            </button>
          </div>
        </div>
        <p v-else class="text-sm text-gray-500">点击左侧树节点查看详情</p>
      </div>
    </div>

    <!-- 新建/编辑组织弹窗 -->
    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 class="mb-4 text-lg font-semibold">{{ isEditing ? '编辑组织' : '新建组织' }}</h3>
        <form @submit.prevent="handleSubmit">
          <div class="mb-3">
            <label class="mb-1 block text-sm font-medium text-gray-700">名称</label>
            <input v-model="formName" class="w-full rounded-md border px-3 py-2 text-sm" />
          </div>
          <div v-if="!isEditing" class="mb-3">
            <label class="mb-1 block text-sm font-medium text-gray-700">类型</label>
            <select v-model="formType" class="w-full rounded-md border px-3 py-2 text-sm">
              <option value="department">部门</option>
              <option value="group">项目组</option>
            </select>
          </div>
          <div class="mb-3">
            <label class="mb-1 block text-sm font-medium text-gray-700">描述</label>
            <textarea v-model="formDescription" rows="2" class="w-full rounded-md border px-3 py-2 text-sm" />
          </div>
          <div class="mb-3">
            <label class="mb-1 block text-sm font-medium text-gray-700">排序</label>
            <input v-model.number="formSortOrder" type="number" class="w-full rounded-md border px-3 py-2 text-sm" />
          </div>
          <p v-if="errorMessage" class="mb-3 text-sm text-red-600">{{ errorMessage }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-md border px-4 py-2 text-sm" @click="showForm = false">取消</button>
            <button type="submit" class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">保存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 设置负责人弹窗 -->
    <div v-if="showManagerForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 class="mb-4 text-lg font-semibold">设置负责人 - {{ selectedOrg?.name }}</h3>
        <p class="mb-3 text-xs text-gray-500">可选择多个负责人</p>
        <div class="mb-4 max-h-64 overflow-y-auto">
          <div
            v-for="user in allUsers"
            :key="user.id"
            class="flex items-center gap-2 border-b py-2 last:border-0"
          >
            <input
              type="checkbox"
              :checked="selectedManagerIds.includes(user.id)"
              @change="toggleManager(user.id)"
            />
            <span class="text-sm text-gray-800">{{ user.username }}</span>
            <span class="text-xs text-gray-500">{{ user.email }}</span>
          </div>
        </div>
        <p v-if="errorMessage" class="mb-3 text-sm text-red-600">{{ errorMessage }}</p>
        <div class="flex justify-end gap-3">
          <button class="rounded-md border px-4 py-2 text-sm" @click="showManagerForm = false">取消</button>
          <button class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700" @click="handleSaveManagers">保存</button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteTarget"
      title="确认删除"
      :message="`确定要删除组织「${deleteTarget?.name}」吗？`"
      @confirm="handleConfirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>
