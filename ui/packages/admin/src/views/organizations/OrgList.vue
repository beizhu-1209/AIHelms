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
    <div class="mb-6 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-slate-900">部门管理</h2>
      <div class="flex gap-2">
        <button
          v-if="hasPermission('organization:create')"
          class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]"
          @click="handleCreate(null)"
        >
          新建部门
        </button>
        <button
          v-if="hasPermission('organization:create')"
          class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
          @click="formType = 'group'; handleCreate(null)"
        >
          新建项目组
        </button>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <!-- 左侧：部门树 -->
      <div class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
        <h3 class="mb-3 text-sm font-medium text-slate-700">部门树</h3>
        <OrgTree
          v-if="tree.length"
          :nodes="tree"
          @select="handleTreeSelect"
        />
        <p v-else class="text-sm text-slate-400">暂无部门</p>

        <h3 class="mb-3 mt-6 text-sm font-medium text-slate-700">项目组</h3>
        <ul>
          <li
            v-for="org in organizations.filter(o => o.type === 'group')"
            :key="org.id"
            class="cursor-pointer rounded-lg px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100/80"
            @click="selectedOrg = org"
          >
            {{ org.name }}
            <span v-if="!org.is_active" class="ml-1 text-xs text-red-400">(已禁用)</span>
          </li>
        </ul>
      </div>

      <!-- 右侧：组织详情 -->
      <div class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
        <h3 class="mb-3 text-sm font-medium text-slate-700">组织详情</h3>
        <div v-if="selectedOrg">
          <dl class="space-y-3 text-sm">
            <div class="flex">
              <dt class="w-20 text-slate-400">名称</dt>
              <dd class="text-slate-900">{{ selectedOrg.name }}</dd>
            </div>
            <div class="flex">
              <dt class="w-20 text-slate-400">类型</dt>
              <dd class="text-slate-900">{{ selectedOrg.type === 'department' ? '部门' : '项目组' }}</dd>
            </div>
            <div class="flex">
              <dt class="w-20 text-slate-400">负责人</dt>
              <dd class="text-slate-900">
                <template v-if="selectedOrg.managers.length">
                  <span
                    v-for="mgr in selectedOrg.managers"
                    :key="mgr.id"
                    class="mr-1 inline-block rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700"
                  >
                    {{ mgr.username }}
                  </span>
                </template>
                <span v-else class="text-slate-400">未设置</span>
              </dd>
            </div>
            <div class="flex">
              <dt class="w-20 text-slate-400">描述</dt>
              <dd class="text-slate-900">{{ selectedOrg.description || '-' }}</dd>
            </div>
            <div class="flex">
              <dt class="w-20 text-slate-400">状态</dt>
              <dd :class="selectedOrg.is_active ? 'text-green-600' : 'text-red-500'">
                {{ selectedOrg.is_active ? '正常' : '已禁用' }}
              </dd>
            </div>
          </dl>
          <div class="mt-5 flex flex-wrap gap-2">
            <button
              v-if="hasPermission('organization:create') && selectedOrg.type === 'department'"
              class="rounded-lg bg-slate-100 px-3 py-1.5 text-sm text-slate-700 transition-colors hover:bg-slate-200"
              @click="handleCreate(selectedOrg.id)"
            >
              添加子部门
            </button>
            <button
              v-if="hasPermission('organization:update')"
              class="rounded-lg bg-blue-50 px-3 py-1.5 text-sm text-blue-600 transition-colors hover:bg-blue-100"
              @click="handleEdit(selectedOrg)"
            >
              编辑
            </button>
            <button
              v-if="hasPermission('organization:update')"
              class="rounded-lg bg-green-50 px-3 py-1.5 text-sm text-green-600 transition-colors hover:bg-green-100"
              @click="handleEditManagers(selectedOrg)"
            >
              设置负责人
            </button>
            <button
              v-if="hasPermission('organization:delete')"
              class="rounded-lg bg-red-50 px-3 py-1.5 text-sm text-red-600 transition-colors hover:bg-red-100"
              @click="deleteTarget = selectedOrg"
            >
              删除
            </button>
          </div>
        </div>
        <p v-else class="text-sm text-slate-400">点击左侧树节点查看详情</p>
      </div>
    </div>

    <!-- 新建/编辑组织弹窗 -->
    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ isEditing ? '编辑组织' : '新建组织' }}</h3>
        <form @submit.prevent="handleSubmit">
          <div class="mb-4">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">名称</label>
            <input
              v-model="formName"
              class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <div v-if="!isEditing" class="mb-4">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">类型</label>
            <select
              v-model="formType"
              class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            >
              <option value="department">部门</option>
              <option value="group">项目组</option>
            </select>
          </div>
          <div class="mb-4">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">描述</label>
            <textarea
              v-model="formDescription"
              rows="2"
              class="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <div class="mb-4">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">排序</label>
            <input
              v-model.number="formSortOrder"
              type="number"
              class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <p v-if="errorMessage" class="mb-4 text-sm text-red-500">{{ errorMessage }}</p>
          <div class="flex justify-end gap-3">
            <button
              type="button"
              class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
              @click="showForm = false"
            >
              取消
            </button>
            <button
              type="submit"
              class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]"
            >
              保存
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 设置负责人弹窗 -->
    <div v-if="showManagerForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-2 text-lg font-semibold text-slate-900">设置负责人 - {{ selectedOrg?.name }}</h3>
        <p class="mb-4 text-xs text-slate-400">可选择多个负责人</p>
        <div class="mb-4 max-h-64 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2">
          <div
            v-for="user in allUsers"
            :key="user.id"
            class="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-slate-50"
          >
            <input
              type="checkbox"
              :checked="selectedManagerIds.includes(user.id)"
              class="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
              @change="toggleManager(user.id)"
            />
            <span class="text-sm text-slate-700">{{ user.username }}</span>
            <span class="text-xs text-slate-400">{{ user.email }}</span>
          </div>
        </div>
        <p v-if="errorMessage" class="mb-4 text-sm text-red-500">{{ errorMessage }}</p>
        <div class="flex justify-end gap-3">
          <button
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
            @click="showManagerForm = false"
          >
            取消
          </button>
          <button
            class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]"
            @click="handleSaveManagers"
          >
            保存
          </button>
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
