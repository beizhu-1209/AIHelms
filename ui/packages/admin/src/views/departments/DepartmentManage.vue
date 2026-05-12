<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  getDepartmentTree,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  getDepartmentMembers,
  addDepartmentMember,
  removeDepartmentMember,
  updateDepartmentManagers,
  getUsers,
  type DeptTreeNode,
  type DeptMember,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()

const tree = ref<DeptTreeNode[]>([])
const selectedDept = ref<DeptTreeNode | null>(null)
const members = ref<DeptMember[]>([])
const showCreateForm = ref(false)
const showAddMember = ref(false)
const deleteTarget = ref<DeptTreeNode | null>(null)
const removeMemberTarget = ref<DeptMember | null>(null)

const formName = ref('')
const formDescription = ref('')
const formParentId = ref<number | null>(null)
const errorMessage = ref('')

const addMemberKeyword = ref('')
const addMemberResults = ref<{ id: number; username: string; display_name: string }[]>([])

const isEditing = ref(false)

async function fetchTree(): Promise<void> {
  tree.value = await getDepartmentTree()
}

async function fetchMembers(deptId: number): Promise<void> {
  members.value = await getDepartmentMembers(deptId)
}

function handleSelectDept(dept: DeptTreeNode): void {
  selectedDept.value = dept
  fetchMembers(dept.id)
}

function handleCreate(parentId: number | null = null): void {
  isEditing.value = false
  formName.value = ''
  formDescription.value = ''
  formParentId.value = parentId
  errorMessage.value = ''
  showCreateForm.value = true
}

function handleEdit(): void {
  if (!selectedDept.value) return
  isEditing.value = true
  formName.value = selectedDept.value.name
  formDescription.value = selectedDept.value.description
  errorMessage.value = ''
  showCreateForm.value = true
}

async function handleSubmit(): Promise<void> {
  errorMessage.value = ''
  if (!formName.value) {
    errorMessage.value = '请输入部门名称'
    return
  }
  try {
    if (isEditing.value && selectedDept.value) {
      await updateDepartment(selectedDept.value.id, {
        name: formName.value,
        description: formDescription.value,
      })
    } else {
      await createDepartment({
        name: formName.value,
        parent_id: formParentId.value,
        description: formDescription.value,
      })
    }
    showCreateForm.value = false
    await fetchTree()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  const targetId = deleteTarget.value.id
  try {
    await deleteDepartment(targetId)
    if (selectedDept.value?.id === targetId) {
      selectedDept.value = null
      members.value = []
    }
    deleteTarget.value = null
    await fetchTree()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '删除失败'
    deleteTarget.value = null
  }
}

async function handleSearchUsers(): Promise<void> {
  if (!addMemberKeyword.value) return
  const result = await getUsers(1, 20, addMemberKeyword.value)
  addMemberResults.value = result.items.map((u: { id: number; username: string; display_name: string }) => ({
    id: u.id,
    username: u.username,
    display_name: u.display_name,
  }))
}

async function handleAddMember(userId: number): Promise<void> {
  if (!selectedDept.value) return
  try {
    await addDepartmentMember(selectedDept.value.id, userId)
    showAddMember.value = false
    addMemberKeyword.value = ''
    addMemberResults.value = []
    await fetchMembers(selectedDept.value.id)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '添加失败'
  }
}

async function handleConfirmRemoveMember(): Promise<void> {
  if (!selectedDept.value || !removeMemberTarget.value) return
  try {
    await removeDepartmentMember(selectedDept.value.id, removeMemberTarget.value.id)
    removeMemberTarget.value = null
    await fetchMembers(selectedDept.value.id)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '移除失败'
    removeMemberTarget.value = null
  }
}

async function handleToggleManager(member: DeptMember): Promise<void> {
  if (!selectedDept.value) return
  const currentManagers = members.value.filter((m: DeptMember) => m.is_manager).map((m: DeptMember) => m.id)
  let newManagers: number[]
  if (member.is_manager) {
    newManagers = currentManagers.filter((id: number) => id !== member.id)
  } else {
    newManagers = [...currentManagers, member.id]
  }
  try {
    await updateDepartmentManagers(selectedDept.value.id, newManagers)
    await fetchMembers(selectedDept.value.id)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '设置主管失败'
  }
}

const isLeaf = computed(() => {
  if (!selectedDept.value) return false
  return !selectedDept.value.children || selectedDept.value.children.length === 0
})

interface FlatNode {
  node: DeptTreeNode
  depth: number
}

function flattenTree(nodes: DeptTreeNode[], depth: number = 0): FlatNode[] {
  const result: FlatNode[] = []
  for (const node of nodes) {
    result.push({ node, depth })
    if (node.children?.length) {
      result.push(...flattenTree(node.children, depth + 1))
    }
  }
  return result
}

const flatNodes = computed(() => flattenTree(tree.value))

onMounted(fetchTree)
</script>

<template>
  <div class="flex h-full gap-4">
    <!-- 左侧：部门树 -->
    <div class="w-80 shrink-0 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
        <h3 class="text-sm font-semibold text-slate-900">部门</h3>
        <button
          v-if="hasPermission('department:create')"
          class="rounded-md bg-purple-600 px-2.5 py-1 text-xs font-medium text-white transition-all hover:bg-purple-500"
          @click="handleCreate(null)"
        >
          新建一级部门
        </button>
      </div>
      <div class="overflow-y-auto p-2" style="max-height: calc(100vh - 10rem)">
        <div
          v-for="{ node, depth } in flatNodes"
          :key="node.id"
          class="group mb-0.5 flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-sm transition-colors"
          :class="selectedDept?.id === node.id ? 'bg-purple-50 font-medium text-purple-700' : 'text-slate-700 hover:bg-slate-100'"
          :style="{ paddingLeft: (depth * 16 + 12) + 'px' }"
          @click="handleSelectDept(node)"
        >
          <span class="truncate">{{ node.name }}</span>
          <div class="flex shrink-0 gap-1 opacity-0 group-hover:opacity-100">
            <button
              v-if="hasPermission('department:create')"
              class="rounded px-1.5 py-0.5 text-xs text-purple-600 transition-colors hover:bg-purple-100"
              title="增加下级部门"
              @click.stop="handleCreate(node.id)"
            >
              +子级
            </button>
            <button
              v-if="hasPermission('department:delete')"
              class="rounded px-1.5 py-0.5 text-xs text-red-500 transition-colors hover:bg-red-50"
              title="删除部门"
              @click.stop="deleteTarget = node"
            >
              删除
            </button>
          </div>
        </div>
        <div v-if="flatNodes.length === 0" class="py-8 text-center text-sm text-slate-400">
          暂无部门
        </div>
      </div>
    </div>

    <!-- 右侧：成员管理 -->
    <div class="flex-1 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <template v-if="selectedDept">
        <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-semibold text-slate-900">{{ selectedDept.name }}</h3>
            <span class="text-xs text-slate-400">{{ members.length }} 人</span>
          </div>
          <div class="flex gap-2">
            <button
              v-if="hasPermission('department:update')"
              class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200"
              @click="handleEdit"
            >
              编辑
            </button>
            <button
              v-if="hasPermission('department:update') && isLeaf"
              class="rounded-md bg-purple-600 px-2.5 py-1 text-xs font-medium text-white transition-all hover:bg-purple-500"
              @click="showAddMember = true"
            >
              添加成员
            </button>
          </div>
        </div>
        <div class="overflow-y-auto p-4" style="max-height: calc(100vh - 10rem)">
          <table class="w-full text-left text-sm">
            <thead class="border-b border-slate-200/60 bg-slate-50/50">
              <tr>
                <th class="px-3 py-2 font-medium text-slate-600">姓名</th>
                <th class="px-3 py-2 font-medium text-slate-600">用户名</th>
                <th class="px-3 py-2 font-medium text-slate-600">职位</th>
                <th class="px-3 py-2 font-medium text-slate-600">主管</th>
                <th class="px-3 py-2 font-medium text-slate-600">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="member in members" :key="member.id" class="border-b border-slate-100 last:border-0">
                <td class="px-3 py-2 text-slate-900">{{ member.display_name || member.username }}</td>
                <td class="px-3 py-2 text-slate-600">{{ member.username }}</td>
                <td class="px-3 py-2 text-slate-500">{{ member.position || '-' }}</td>
                <td class="px-3 py-2">
                  <button
                    v-if="hasPermission('department:update')"
                    class="rounded-full px-2 py-0.5 text-xs font-medium transition-colors"
                    :class="member.is_manager ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                    @click="handleToggleManager(member)"
                  >
                    {{ member.is_manager ? '主管' : '设为主管' }}
                  </button>
                  <span v-else class="text-xs text-slate-400">{{ member.is_manager ? '是' : '-' }}</span>
                </td>
                <td class="px-3 py-2">
                  <button
                    v-if="hasPermission('department:update')"
                    class="text-xs text-red-500 transition-colors hover:text-red-600"
                    @click="removeMemberTarget = member"
                  >
                    移除
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="members.length === 0" class="py-8 text-center text-sm text-slate-400">
            暂无成员
          </div>
        </div>
      </template>
      <template v-else>
        <div class="flex h-full items-center justify-center text-sm text-slate-400">
          请选择左侧部门
        </div>
      </template>
    </div>

    <!-- 新建/编辑部门弹窗 -->
    <div v-if="showCreateForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ isEditing ? '编辑部门' : '新建部门' }}</h3>
        <form @submit.prevent="handleSubmit">
          <div class="mb-4">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">部门名称</label>
            <input
              v-model="formName"
              placeholder="请输入部门名称"
              class="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <div class="mb-4">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">描述</label>
            <textarea
              v-model="formDescription"
              rows="2"
              class="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <p v-if="errorMessage" class="mb-4 text-sm text-red-500">{{ errorMessage }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showCreateForm = false">取消</button>
            <button type="submit" class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98]">保存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 添加成员弹窗 -->
    <div v-if="showAddMember" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">添加成员</h3>
        <div class="mb-4 flex gap-2">
          <input
            v-model="addMemberKeyword"
            placeholder="搜索用户名或姓名"
            class="flex h-10 flex-1 rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            @keyup.enter="handleSearchUsers"
          />
          <button class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-purple-500" @click="handleSearchUsers">搜索</button>
        </div>
        <div class="mb-4 max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white">
          <div
            v-for="user in addMemberResults"
            :key="user.id"
            class="flex items-center justify-between px-4 py-2 transition-colors hover:bg-slate-50"
          >
            <span class="text-sm text-slate-700">{{ user.display_name || user.username }}</span>
            <button class="text-xs text-purple-600 transition-colors hover:text-purple-700" @click="handleAddMember(user.id)">添加</button>
          </div>
          <div v-if="addMemberResults.length === 0" class="py-4 text-center text-sm text-slate-400">搜索用户以添加</div>
        </div>
        <div class="flex justify-end">
          <button class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200" @click="showAddMember = false; addMemberResults = []">关闭</button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteTarget"
      title="确认删除"
      :message="`确定要删除部门「${deleteTarget?.name}」吗？`"
      @confirm="handleConfirmDelete"
      @cancel="deleteTarget = null"
    />

    <ConfirmDialog
      :visible="!!removeMemberTarget"
      title="确认移除"
      :message="`确定要将「${removeMemberTarget?.display_name || removeMemberTarget?.username}」从部门中移除吗？`"
      @confirm="handleConfirmRemoveMember"
      @cancel="removeMemberTarget = null"
    />
  </div>
</template>
