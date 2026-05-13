<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getIdentityList,
  createAiKey,
  updateAiKey,
  toggleAiKey,
  deleteAiKey,
  getActiveModels,
  getModelLimits,
  setModelLimits,
  type AiKey,
  type ActiveModel,
  type IdentityUserItem,
  type IdentityDepartmentItem,
  type IdentityProjectItem,
  type AiKeyModelLimit,
  type SetModelLimitItem,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()

type TabType = 'user' | 'department' | 'project'

const activeTab = ref<TabType>('user')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const isLoading = ref(false)

// Tab-specific filters
const filterStatus = ref<'all' | 'active' | 'inactive'>('all')
const filterDepartment = ref('')

const userItems = ref<IdentityUserItem[]>([])
const deptItems = ref<IdentityDepartmentItem[]>([])
const projectItems = ref<IdentityProjectItem[]>([])
const expandedRows = ref<Set<string>>(new Set())

const activeModels = ref<ActiveModel[]>([])
const showCreateForm = ref(false)
const showEditForm = ref(false)
const editingKey = ref<AiKey | null>(null)
const editingOwnerType = ref<TabType>('user')
const editingOwnerId = ref<number>(0)
const deleteTarget = ref<AiKey | null>(null)
const createdKeyValue = ref<string | null>(null)

// Create form
const formName = ref('')
const formDescription = ref('')
const formKeyType = ref('personal_scene')
const formSelectedModels = ref<string[]>([])
const formBudgetLimit = ref('')
const formBudgetType = ref<'money' | 'count'>('money')
const formBudgetHardLimit = ref(true)
const formTags = ref('')
const formOwnerId = ref<number>(0)
const errorMessage = ref('')

// Model limits
const showLimitsForm = ref(false)
const limitsKeyId = ref<number>(0)
const limitsKeyName = ref('')
const modelLimits = ref<AiKeyModelLimit[]>([])
const limitsFormData = ref<SetModelLimitItem[]>([])
const limitsError = ref('')

async function fetchData(): Promise<void> {
  isLoading.value = true
  if (activeTab.value === 'user') {
    const result = await getIdentityList('user', page.value, pageSize.value, keyword.value || undefined)
    userItems.value = result.items
    total.value = result.total
  } else if (activeTab.value === 'department') {
    const result = await getIdentityList('department', page.value, pageSize.value, keyword.value || undefined)
    deptItems.value = result.items
    total.value = result.total
  } else {
    const result = await getIdentityList('project', page.value, pageSize.value, keyword.value || undefined)
    projectItems.value = result.items
    total.value = result.total
  }
  isLoading.value = false
}

async function fetchModels(): Promise<void> {
  activeModels.value = await getActiveModels()
}

function handleTabChange(tab: TabType): void {
  activeTab.value = tab
  page.value = 1
  keyword.value = ''
  filterStatus.value = 'all'
  filterDepartment.value = ''
  expandedRows.value.clear()
  fetchData()
}

function handleSearch(): void {
  page.value = 1
  fetchData()
}

function handleCreateNew(): void {
  editingOwnerType.value = activeTab.value
  editingOwnerId.value = 0
  formOwnerId.value = 0
  formName.value = ''
  formDescription.value = ''
  formKeyType.value = activeTab.value === 'user' ? 'personal_scene' : activeTab.value === 'department' ? 'dept_shared' : 'project_shared'
  formSelectedModels.value = []
  formBudgetLimit.value = ''
  formBudgetType.value = 'money'
  formBudgetHardLimit.value = true
  formTags.value = ''
  errorMessage.value = ''
  createdKeyValue.value = null
  showCreateForm.value = true
}

function toggleExpand(rowKey: string): void {
  if (expandedRows.value.has(rowKey)) {
    expandedRows.value.delete(rowKey)
  } else {
    expandedRows.value.add(rowKey)
  }
}

function toggleModel(modelId: string): void {
  const idx = formSelectedModels.value.indexOf(modelId)
  if (idx >= 0) {
    formSelectedModels.value.splice(idx, 1)
  } else {
    formSelectedModels.value.push(modelId)
  }
}

function handleCreateForUser(userId: number): void {
  editingOwnerType.value = 'user'
  editingOwnerId.value = userId
  formName.value = ''
  formDescription.value = ''
  formKeyType.value = 'personal_scene'
  formSelectedModels.value = []
  formBudgetLimit.value = ''
  formBudgetType.value = 'money'
  formBudgetHardLimit.value = true
  formTags.value = ''
  errorMessage.value = ''
  createdKeyValue.value = null
  showCreateForm.value = true
}

function handleCreateForOwner(ownerType: TabType, ownerId: number): void {
  editingOwnerType.value = ownerType
  editingOwnerId.value = ownerId
  formName.value = ''
  formDescription.value = ''
  formKeyType.value = ownerType === 'department' ? 'dept_shared' : 'project_shared'
  formSelectedModels.value = []
  formBudgetLimit.value = ''
  formBudgetType.value = 'money'
  formBudgetHardLimit.value = true
  formTags.value = ''
  errorMessage.value = ''
  createdKeyValue.value = null
  showCreateForm.value = true
}

function handleEdit(key: AiKey): void {
  editingKey.value = key
  formName.value = key.name
  formDescription.value = key.description
  formSelectedModels.value = [...key.models]
  formBudgetLimit.value = key.budget_limit || ''
  formBudgetType.value = key.budget_type === 'count' ? 'count' : 'money'
  formBudgetHardLimit.value = key.budget_hard_limit
  formTags.value = key.tags.join(', ')
  errorMessage.value = ''
  showEditForm.value = true
}

async function handleSubmitCreate(): Promise<void> {
  errorMessage.value = ''
  const ownerId = editingOwnerId.value || formOwnerId.value
  if (!ownerId) {
    errorMessage.value = '请选择归属对象'
    return
  }
  if (!formName.value) {
    errorMessage.value = '请输入 Key 名称'
    return
  }
  try {
    const tags = formTags.value ? formTags.value.split(',').map(s => s.trim()).filter(Boolean) : []
    const budgetLimit = formBudgetLimit.value ? Number(formBudgetLimit.value) : undefined
    const result = await createAiKey({
      name: formName.value,
      key_type: formKeyType.value,
      owner_type: editingOwnerType.value,
      owner_id: ownerId,
      description: formDescription.value,
      models: formSelectedModels.value,
      tags,
      budget_limit: budgetLimit,
      budget_type: formBudgetType.value,
      budget_hard_limit: formBudgetHardLimit.value,
    })
    createdKeyValue.value = result.key_value || null
    if (!createdKeyValue.value) {
      showCreateForm.value = false
    }
    await fetchData()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '创建失败'
  }
}

async function handleSubmitEdit(): Promise<void> {
  if (!editingKey.value) return
  errorMessage.value = ''
  try {
    const tags = formTags.value ? formTags.value.split(',').map(s => s.trim()).filter(Boolean) : []
    const budgetLimit = formBudgetLimit.value ? Number(formBudgetLimit.value) : undefined
    await updateAiKey(editingKey.value.id, {
      name: formName.value,
      description: formDescription.value,
      models: formSelectedModels.value,
      tags,
      budget_limit: budgetLimit,
      budget_type: formBudgetType.value,
      budget_hard_limit: formBudgetHardLimit.value,
    })
    showEditForm.value = false
    editingKey.value = null
    await fetchData()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '更新失败'
  }
}

async function handleToggle(key: AiKey): Promise<void> {
  await toggleAiKey(key.id)
  await fetchData()
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  try {
    await deleteAiKey(deleteTarget.value.id)
    deleteTarget.value = null
    await fetchData()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '删除失败'
    deleteTarget.value = null
  }
}

function handleCopyKey(): void {
  if (createdKeyValue.value) {
    navigator.clipboard.writeText(createdKeyValue.value)
  }
}

async function handleOpenLimits(key: AiKey): Promise<void> {
  limitsKeyId.value = key.id
  limitsKeyName.value = key.name
  limitsError.value = ''
  modelLimits.value = await getModelLimits(key.id)
  // Init form data from key's associated models
  limitsFormData.value = key.models.map(modelId => {
    const existing = modelLimits.value.find(l => l.model_model_id === modelId)
    const modelInfo = activeModels.value.find(m => m.model_id === modelId)
    return {
      model_id: modelInfo?.id || existing?.model_id || 0,
      tpm: existing?.tpm || null,
      rpm: existing?.rpm || null,
      max_tokens: existing?.max_tokens || null,
      max_calls: existing?.max_calls || null,
    }
  }).filter(item => item.model_id > 0)
  showLimitsForm.value = true
}

async function handleSaveLimits(): Promise<void> {
  limitsError.value = ''
  try {
    await setModelLimits(limitsKeyId.value, limitsFormData.value)
    showLimitsForm.value = false
    await fetchData()
  } catch (e) {
    limitsError.value = e instanceof Error ? e.message : '保存失败'
  }
}

function getModelName(modelId: string): string {
  const m = activeModels.value.find(am => am.model_id === modelId)
  return m?.name || modelId
}

onMounted(() => {
  fetchData()
  fetchModels()
})
</script>

<template>
  <div class="h-full overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
    <!-- Header -->
    <div class="border-b border-slate-200/60">
      <!-- Title + Create -->
      <div class="flex h-12 items-center justify-between px-5">
        <h2 class="text-base font-semibold text-slate-900">AI 身份管理</h2>
        <button
          v-if="hasPermission('user:update')"
          class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-3.5 py-1.5 text-xs font-medium text-white shadow-sm shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500"
          @click="handleCreateNew"
        >新建 Key</button>
      </div>
      <!-- Tabs -->
      <div class="flex gap-1 px-5">
        <button
          class="rounded-t-lg border-b-2 px-3 py-2 text-sm font-medium transition-colors"
          :class="activeTab === 'user' ? 'border-purple-600 text-purple-700' : 'border-transparent text-slate-500 hover:text-slate-700'"
          @click="handleTabChange('user')"
        >人员</button>
        <button
          class="rounded-t-lg border-b-2 px-3 py-2 text-sm font-medium transition-colors"
          :class="activeTab === 'department' ? 'border-purple-600 text-purple-700' : 'border-transparent text-slate-500 hover:text-slate-700'"
          @click="handleTabChange('department')"
        >部门</button>
        <button
          class="rounded-t-lg border-b-2 px-3 py-2 text-sm font-medium transition-colors"
          :class="activeTab === 'project' ? 'border-purple-600 text-purple-700' : 'border-transparent text-slate-500 hover:text-slate-700'"
          @click="handleTabChange('project')"
        >项目</button>
      </div>
    </div>

    <!-- Filter bar (tab-specific) -->
    <div class="flex items-center gap-3 border-b border-slate-100 px-5 py-2.5">
      <input
        v-model="keyword"
        :placeholder="activeTab === 'user' ? '搜索用户名/姓名...' : activeTab === 'department' ? '搜索部门名称...' : '搜索项目名称...'"
        class="h-8 w-52 rounded-lg border border-slate-200 bg-white px-3 text-sm placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
        @keyup.enter="handleSearch"
      />
      <!-- User tab filters -->
      <template v-if="activeTab === 'user'">
        <select
          v-model="filterStatus"
          class="h-8 rounded-lg border border-slate-200 bg-white px-2.5 text-sm text-slate-700 focus:border-purple-500/50 focus:outline-none"
          @change="handleSearch"
        >
          <option value="all">全部状态</option>
          <option value="active">已启用</option>
          <option value="inactive">已禁用</option>
        </select>
      </template>
      <!-- Department/Project tab: no extra filters needed -->
      <button
        class="h-8 rounded-lg bg-slate-100 px-3 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200"
        @click="handleSearch"
      >搜索</button>
    </div>

    <!-- Content -->
    <div class="overflow-y-auto p-4" style="max-height: calc(100vh - 12rem)">
      <!-- User tab -->
      <table v-if="activeTab === 'user'" class="w-full text-left text-sm">
        <thead class="border-b border-slate-200/60">
          <tr>
            <th class="w-8 px-3 py-2"></th>
            <th class="px-3 py-2 font-medium text-slate-600">用户</th>
            <th class="px-3 py-2 font-medium text-slate-600">部门</th>
            <th class="px-3 py-2 font-medium text-slate-600">可用模型</th>
            <th class="px-3 py-2 font-medium text-slate-600">状态</th>
            <th class="px-3 py-2 font-medium text-slate-600">操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="item in userItems" :key="item.user.id">
            <tr class="border-b border-slate-100 hover:bg-slate-50/50">
              <td class="px-3 py-2">
                <button
                  v-if="item.scene_keys.length > 0"
                  class="text-slate-400 transition-transform"
                  :class="expandedRows.has(`user-${item.user.id}`) ? 'rotate-90' : ''"
                  @click="toggleExpand(`user-${item.user.id}`)"
                >▶</button>
              </td>
              <td class="px-3 py-2">
                <div class="font-medium text-slate-900">{{ item.user.display_name || item.user.username }}</div>
                <div class="text-xs text-slate-400">{{ item.user.username }}</div>
              </td>
              <td class="px-3 py-2 text-slate-600">{{ item.user.department_name || '-' }}</td>
              <td class="px-3 py-2">
                <div v-if="item.main_key && item.main_key.models.length > 0" class="flex flex-wrap gap-1">
                  <span v-for="m in item.main_key.models.slice(0, 3)" :key="m" class="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">{{ getModelName(m) }}</span>
                  <span v-if="item.main_key.models.length > 3" class="text-xs text-slate-400">+{{ item.main_key.models.length - 3 }}</span>
                </div>
                <span v-else class="text-xs text-slate-400">全部</span>
              </td>
              <td class="px-3 py-2">
                <button
                  v-if="item.main_key"
                  class="rounded-full px-2 py-0.5 text-xs font-medium transition-colors"
                  :class="item.main_key.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                  @click="handleToggle(item.main_key!)"
                >{{ item.main_key.is_active ? '已启用' : '已禁用' }}</button>
                <span v-else class="text-xs text-slate-400">无主Key</span>
              </td>
              <td class="px-3 py-2">
                <div class="flex gap-2">
                  <button v-if="item.main_key && hasPermission('user:update')" class="text-xs text-purple-500 hover:text-purple-600" @click="handleEdit(item.main_key!)">编辑</button>
                  <button v-if="item.main_key && item.main_key.models.length > 0 && hasPermission('user:update')" class="text-xs text-blue-500 hover:text-blue-600" @click="handleOpenLimits(item.main_key!)">限制</button>
                  <button v-if="hasPermission('user:update')" class="text-xs text-green-500 hover:text-green-600" @click="handleCreateForUser(item.user.id)">+场景Key</button>
                </div>
              </td>
            </tr>
            <!-- Expanded scene keys -->
            <template v-if="expandedRows.has(`user-${item.user.id}`)">
              <tr v-for="sk in item.scene_keys" :key="sk.id" class="border-b border-slate-50 bg-slate-50/30">
                <td class="px-3 py-1.5"></td>
                <td class="px-3 py-1.5">
                  <span class="text-xs text-slate-500">┗ {{ sk.name }}</span>
                  <span v-if="sk.tags.length > 0" class="ml-1 rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-400">{{ sk.tags[0] }}</span>
                </td>
                <td class="px-3 py-1.5"></td>
                <td class="px-3 py-1.5">
                  <div v-if="sk.models.length > 0" class="flex flex-wrap gap-1">
                    <span v-for="m in sk.models.slice(0, 2)" :key="m" class="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">{{ getModelName(m) }}</span>
                    <span v-if="sk.models.length > 2" class="text-xs text-slate-400">+{{ sk.models.length - 2 }}</span>
                  </div>
                  <span v-else class="text-xs text-slate-400">全部</span>
                </td>
                <td class="px-3 py-1.5">
                  <button
                    class="rounded-full px-2 py-0.5 text-xs font-medium transition-colors"
                    :class="sk.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                    @click="handleToggle(sk)"
                  >{{ sk.is_active ? '启用' : '禁用' }}</button>
                </td>
                <td class="px-3 py-1.5">
                  <div class="flex gap-2">
                    <button v-if="hasPermission('user:update')" class="text-xs text-purple-500 hover:text-purple-600" @click="handleEdit(sk)">编辑</button>
                    <button v-if="sk.models.length > 0 && hasPermission('user:update')" class="text-xs text-blue-500 hover:text-blue-600" @click="handleOpenLimits(sk)">限制</button>
                    <button v-if="hasPermission('user:delete')" class="text-xs text-red-500 hover:text-red-600" @click="deleteTarget = sk">删除</button>
                  </div>
                </td>
              </tr>
            </template>
          </template>
        </tbody>
      </table>

      <!-- Department tab -->
      <table v-if="activeTab === 'department'" class="w-full text-left text-sm">
        <thead class="border-b border-slate-200/60">
          <tr>
            <th class="px-3 py-2 font-medium text-slate-600">部门</th>
            <th class="px-3 py-2 font-medium text-slate-600">Key 名称</th>
            <th class="px-3 py-2 font-medium text-slate-600">可用模型</th>
            <th class="px-3 py-2 font-medium text-slate-600">状态</th>
            <th class="px-3 py-2 font-medium text-slate-600">操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="item in deptItems" :key="item.department.id">
            <tr v-if="item.keys.length === 0" class="border-b border-slate-100">
              <td class="px-3 py-2 font-medium text-slate-900">{{ item.department.name }}</td>
              <td class="px-3 py-2 text-xs text-slate-400" colspan="3">暂无共享 Key</td>
              <td class="px-3 py-2">
                <button v-if="hasPermission('user:update')" class="text-xs text-green-500 hover:text-green-600" @click="handleCreateForOwner('department', item.department.id)">创建</button>
              </td>
            </tr>
            <tr v-for="(key, idx) in item.keys" :key="key.id" class="border-b border-slate-100">
              <td class="px-3 py-2 font-medium text-slate-900">{{ idx === 0 ? item.department.name : '' }}</td>
              <td class="px-3 py-2 text-slate-700">{{ key.name }}</td>
              <td class="px-3 py-2">
                <div v-if="key.models.length > 0" class="flex flex-wrap gap-1">
                  <span v-for="m in key.models.slice(0, 3)" :key="m" class="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">{{ getModelName(m) }}</span>
                  <span v-if="key.models.length > 3" class="text-xs text-slate-400">+{{ key.models.length - 3 }}</span>
                </div>
                <span v-else class="text-xs text-slate-400">全部</span>
              </td>
              <td class="px-3 py-2">
                <button
                  class="rounded-full px-2 py-0.5 text-xs font-medium transition-colors"
                  :class="key.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                  @click="handleToggle(key)"
                >{{ key.is_active ? '已启用' : '已禁用' }}</button>
              </td>
              <td class="px-3 py-2">
                <div class="flex gap-2">
                  <button v-if="hasPermission('user:update')" class="text-xs text-purple-500 hover:text-purple-600" @click="handleEdit(key)">编辑</button>
                  <button v-if="key.models.length > 0 && hasPermission('user:update')" class="text-xs text-blue-500 hover:text-blue-600" @click="handleOpenLimits(key)">限制</button>
                  <button v-if="hasPermission('user:delete')" class="text-xs text-red-500 hover:text-red-600" @click="deleteTarget = key">删除</button>
                  <button v-if="idx === 0 && hasPermission('user:update')" class="text-xs text-green-500 hover:text-green-600" @click="handleCreateForOwner('department', item.department.id)">+Key</button>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <!-- Project tab -->
      <table v-if="activeTab === 'project'" class="w-full text-left text-sm">
        <thead class="border-b border-slate-200/60">
          <tr>
            <th class="px-3 py-2 font-medium text-slate-600">项目</th>
            <th class="px-3 py-2 font-medium text-slate-600">Key 名称</th>
            <th class="px-3 py-2 font-medium text-slate-600">可用模型</th>
            <th class="px-3 py-2 font-medium text-slate-600">状态</th>
            <th class="px-3 py-2 font-medium text-slate-600">操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="item in projectItems" :key="item.project.id">
            <tr v-if="item.keys.length === 0" class="border-b border-slate-100">
              <td class="px-3 py-2 font-medium text-slate-900">{{ item.project.name }}</td>
              <td class="px-3 py-2 text-xs text-slate-400" colspan="3">暂无共享 Key</td>
              <td class="px-3 py-2">
                <button v-if="hasPermission('user:update')" class="text-xs text-green-500 hover:text-green-600" @click="handleCreateForOwner('project', item.project.id)">创建</button>
              </td>
            </tr>
            <tr v-for="(key, idx) in item.keys" :key="key.id" class="border-b border-slate-100">
              <td class="px-3 py-2 font-medium text-slate-900">{{ idx === 0 ? item.project.name : '' }}</td>
              <td class="px-3 py-2 text-slate-700">{{ key.name }}</td>
              <td class="px-3 py-2">
                <div v-if="key.models.length > 0" class="flex flex-wrap gap-1">
                  <span v-for="m in key.models.slice(0, 3)" :key="m" class="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">{{ getModelName(m) }}</span>
                  <span v-if="key.models.length > 3" class="text-xs text-slate-400">+{{ key.models.length - 3 }}</span>
                </div>
                <span v-else class="text-xs text-slate-400">全部</span>
              </td>
              <td class="px-3 py-2">
                <button
                  class="rounded-full px-2 py-0.5 text-xs font-medium transition-colors"
                  :class="key.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                  @click="handleToggle(key)"
                >{{ key.is_active ? '已启用' : '已禁用' }}</button>
              </td>
              <td class="px-3 py-2">
                <div class="flex gap-2">
                  <button v-if="hasPermission('user:update')" class="text-xs text-purple-500 hover:text-purple-600" @click="handleEdit(key)">编辑</button>
                  <button v-if="key.models.length > 0 && hasPermission('user:update')" class="text-xs text-blue-500 hover:text-blue-600" @click="handleOpenLimits(key)">限制</button>
                  <button v-if="hasPermission('user:delete')" class="text-xs text-red-500 hover:text-red-600" @click="deleteTarget = key">删除</button>
                  <button v-if="idx === 0 && hasPermission('user:update')" class="text-xs text-green-500 hover:text-green-600" @click="handleCreateForOwner('project', item.project.id)">+Key</button>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <div v-if="isLoading" class="py-12 text-center text-sm text-slate-400">加载中...</div>
      <div v-if="!isLoading && total === 0" class="py-12 text-center text-sm text-slate-400">暂无数据</div>
    </div>
  </div>

  <!-- Create Key Modal -->
  <div v-if="showCreateForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
    <div class="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
      <template v-if="createdKeyValue">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">Key 创建成功</h3>
        <p class="mb-2 text-sm text-slate-600">请立即复制保存，此 Key 仅显示一次：</p>
        <div class="mb-4 flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <code class="flex-1 break-all text-sm text-slate-900">{{ createdKeyValue }}</code>
          <button class="shrink-0 rounded-md bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-500" @click="handleCopyKey">复制</button>
        </div>
        <div class="flex justify-end">
          <button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showCreateForm = false; createdKeyValue = null">关闭</button>
        </div>
      </template>
      <template v-else>
        <h3 class="mb-4 text-lg font-semibold text-slate-900">创建 Key</h3>
        <form @submit.prevent="handleSubmitCreate">
          <!-- Owner selection (when from top-level button) -->
          <div v-if="editingOwnerId === 0" class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">归属类型</label>
            <select v-model="editingOwnerType" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" @change="formKeyType = editingOwnerType === 'user' ? 'personal_scene' : editingOwnerType === 'department' ? 'dept_shared' : 'project_shared'">
              <option value="user">人员</option>
              <option value="department">部门</option>
              <option value="project">项目</option>
            </select>
          </div>
          <div v-if="editingOwnerId === 0 && editingOwnerType === 'user'" class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">选择用户</label>
            <select v-model="formOwnerId" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
              <option :value="0" disabled>请选择用户</option>
              <option v-for="item in userItems" :key="item.user.id" :value="item.user.id">{{ item.user.display_name || item.user.username }}</option>
            </select>
          </div>
          <div v-if="editingOwnerId === 0 && editingOwnerType === 'department'" class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">选择部门</label>
            <select v-model="formOwnerId" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
              <option :value="0" disabled>请选择部门</option>
              <option v-for="item in deptItems" :key="item.department.id" :value="item.department.id">{{ item.department.name }}</option>
            </select>
          </div>
          <div v-if="editingOwnerId === 0 && editingOwnerType === 'project'" class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">选择项目</label>
            <select v-model="formOwnerId" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20">
              <option :value="0" disabled>请选择项目</option>
              <option v-for="item in projectItems" :key="item.project.id" :value="item.project.id">{{ item.project.name }}</option>
            </select>
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">Key 名称</label>
            <input v-model="formName" placeholder="如：开发环境、CI/CD" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">描述</label>
            <input v-model="formDescription" placeholder="可选" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">可用模型</label>
            <div class="max-h-40 overflow-y-auto rounded-lg border border-slate-200 p-2">
              <label v-for="m in activeModels" :key="m.model_id" class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-slate-50">
                <input type="checkbox" :checked="formSelectedModels.includes(m.model_id)" class="h-4 w-4 rounded border-slate-300 text-purple-600" @change="toggleModel(m.model_id)" />
                <span class="text-slate-700">{{ m.name }}</span>
                <span class="text-xs text-slate-400">{{ m.model_id }}</span>
              </label>
              <p v-if="activeModels.length === 0" class="py-2 text-center text-xs text-slate-400">暂无模型</p>
            </div>
            <p class="mt-1 text-xs text-slate-400">不选 = 可用全部模型</p>
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">标签</label>
            <input v-model="formTags" placeholder="逗号分隔" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">预算</label>
            <div class="flex gap-3">
              <input v-model="formBudgetLimit" type="number" step="0.01" :placeholder="formBudgetType === 'money' ? '金额（留空=无限制）' : '次数（留空=无限制）'" class="flex h-10 flex-1 rounded-lg border border-slate-200 bg-white px-4 text-sm placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
              <select v-model="formBudgetType" class="flex h-10 w-24 rounded-lg border border-slate-200 bg-white px-2 text-sm focus:border-purple-500/50 focus:outline-none">
                <option value="money">金额</option>
                <option value="count">次数</option>
              </select>
              <label class="flex items-center gap-1.5 text-sm text-slate-700">
                <input v-model="formBudgetHardLimit" type="checkbox" class="h-4 w-4 rounded border-slate-300 text-purple-600" />硬限
              </label>
            </div>
          </div>
          <p v-if="errorMessage" class="mb-3 text-sm text-red-500">{{ errorMessage }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showCreateForm = false">取消</button>
            <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 hover:from-purple-500 hover:to-blue-500">创建</button>
          </div>
        </form>
      </template>
    </div>
  </div>

  <!-- Edit Key Modal -->
  <div v-if="showEditForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
    <div class="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
      <h3 class="mb-4 text-lg font-semibold text-slate-900">编辑 Key</h3>
      <form @submit.prevent="handleSubmitEdit">
        <div class="mb-3">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">Key 名称</label>
          <input v-model="formName" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
        </div>
        <div class="mb-3">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">描述</label>
          <input v-model="formDescription" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
        </div>
        <div class="mb-3">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">可用模型</label>
          <div class="max-h-40 overflow-y-auto rounded-lg border border-slate-200 p-2">
            <label v-for="m in activeModels" :key="m.model_id" class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-slate-50">
              <input type="checkbox" :checked="formSelectedModels.includes(m.model_id)" class="h-4 w-4 rounded border-slate-300 text-purple-600" @change="toggleModel(m.model_id)" />
              <span class="text-slate-700">{{ m.name }}</span>
              <span class="text-xs text-slate-400">{{ m.model_id }}</span>
            </label>
          </div>
          <p class="mt-1 text-xs text-slate-400">不选 = 可用全部模型</p>
        </div>
        <div class="mb-3">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">标签</label>
          <input v-model="formTags" placeholder="逗号分隔" class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
        </div>
        <div class="mb-3">
          <label class="mb-1.5 block text-sm font-medium text-slate-700">预算</label>
          <div class="flex gap-3">
            <input v-model="formBudgetLimit" type="number" step="0.01" :placeholder="formBudgetType === 'money' ? '金额' : '次数'" class="flex h-10 flex-1 rounded-lg border border-slate-200 bg-white px-4 text-sm placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20" />
            <select v-model="formBudgetType" class="flex h-10 w-24 rounded-lg border border-slate-200 bg-white px-2 text-sm focus:border-purple-500/50 focus:outline-none">
              <option value="money">金额</option>
              <option value="count">次数</option>
            </select>
            <label class="flex items-center gap-1.5 text-sm text-slate-700">
              <input v-model="formBudgetHardLimit" type="checkbox" class="h-4 w-4 rounded border-slate-300 text-purple-600" />硬限
            </label>
          </div>
        </div>
        <p v-if="errorMessage" class="mb-3 text-sm text-red-500">{{ errorMessage }}</p>
        <div class="flex justify-end gap-3">
          <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showEditForm = false">取消</button>
          <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 hover:from-purple-500 hover:to-blue-500">保存</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Model Limits Modal -->
  <div v-if="showLimitsForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
    <div class="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
      <h3 class="mb-4 text-lg font-semibold text-slate-900">模型限制 - {{ limitsKeyName }}</h3>
      <p class="mb-3 text-xs text-slate-400">留空表示不限制</p>
      <table v-if="limitsFormData.length > 0" class="mb-4 w-full text-sm">
        <thead class="border-b border-slate-200">
          <tr>
            <th class="px-2 py-1.5 text-left text-xs font-medium text-slate-600">模型</th>
            <th class="px-2 py-1.5 text-xs font-medium text-slate-600">TPM</th>
            <th class="px-2 py-1.5 text-xs font-medium text-slate-600">RPM</th>
            <th class="px-2 py-1.5 text-xs font-medium text-slate-600">Max Tokens</th>
            <th class="px-2 py-1.5 text-xs font-medium text-slate-600">调用次数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in limitsFormData" :key="item.model_id" class="border-b border-slate-100">
            <td class="px-2 py-1.5 text-xs text-slate-700">{{ activeModels.find(m => m.id === item.model_id)?.name || item.model_id }}</td>
            <td class="px-2 py-1.5"><input v-model.number="limitsFormData[idx].tpm" type="number" min="1" placeholder="-" class="h-7 w-20 rounded border border-slate-200 px-2 text-xs focus:border-purple-500/50 focus:outline-none" /></td>
            <td class="px-2 py-1.5"><input v-model.number="limitsFormData[idx].rpm" type="number" min="1" placeholder="-" class="h-7 w-20 rounded border border-slate-200 px-2 text-xs focus:border-purple-500/50 focus:outline-none" /></td>
            <td class="px-2 py-1.5"><input v-model.number="limitsFormData[idx].max_tokens" type="number" min="1" placeholder="-" class="h-7 w-20 rounded border border-slate-200 px-2 text-xs focus:border-purple-500/50 focus:outline-none" /></td>
            <td class="px-2 py-1.5"><input v-model.number="limitsFormData[idx].max_calls" type="number" min="1" placeholder="-" class="h-7 w-20 rounded border border-slate-200 px-2 text-xs focus:border-purple-500/50 focus:outline-none" /></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="mb-4 text-sm text-slate-400">该 Key 未关联具体模型，无法设置限制</p>
      <p v-if="limitsError" class="mb-3 text-sm text-red-500">{{ limitsError }}</p>
      <div class="flex justify-end gap-3">
        <button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200" @click="showLimitsForm = false">取消</button>
        <button v-if="limitsFormData.length > 0" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 hover:from-purple-500 hover:to-blue-500" @click="handleSaveLimits">保存</button>
      </div>
    </div>
  </div>

  <ConfirmDialog
    :visible="!!deleteTarget"
    title="确认删除"
    :message="`确定要删除 Key「${deleteTarget?.name}」吗？此操作不可恢复。`"
    @confirm="handleConfirmDelete"
    @cancel="deleteTarget = null"
  />
</template>
