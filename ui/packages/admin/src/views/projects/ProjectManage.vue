<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getProjects,
  createProject,
  updateProject,
  deleteProject,
  getProjectMembers,
  addProjectMember,
  removeProjectMember,
  getUsers,
  type Project,
  type ProjectMember,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { hasPermission } = usePermission()

const projects = ref<Project[]>([])
const selectedProject = ref<Project | null>(null)
const members = ref<ProjectMember[]>([])
const showCreateForm = ref(false)
const showAddMember = ref(false)
const deleteTarget = ref<Project | null>(null)
const removeMemberTarget = ref<ProjectMember | null>(null)

const formName = ref('')
const formDescription = ref('')
const errorMessage = ref('')
const isEditing = ref(false)

const addMemberKeyword = ref('')
const addMemberResults = ref<{ id: number; username: string; display_name: string }[]>([])

async function fetchProjects(): Promise<void> {
  const result = await getProjects(1, 100)
  projects.value = result.items
}

async function fetchMembers(projectId: number): Promise<void> {
  members.value = await getProjectMembers(projectId)
}

function handleSelectProject(project: Project): void {
  selectedProject.value = project
  fetchMembers(project.id)
}

function handleCreate(): void {
  isEditing.value = false
  formName.value = ''
  formDescription.value = ''
  errorMessage.value = ''
  showCreateForm.value = true
}

function handleEdit(): void {
  if (!selectedProject.value) return
  isEditing.value = true
  formName.value = selectedProject.value.name
  formDescription.value = selectedProject.value.description
  errorMessage.value = ''
  showCreateForm.value = true
}

async function handleSubmit(): Promise<void> {
  errorMessage.value = ''
  if (!formName.value) {
    errorMessage.value = '请输入项目名称'
    return
  }
  try {
    if (isEditing.value && selectedProject.value) {
      await updateProject(selectedProject.value.id, {
        name: formName.value,
        description: formDescription.value,
      })
    } else {
      await createProject({
        name: formName.value,
        description: formDescription.value,
      })
    }
    showCreateForm.value = false
    await fetchProjects()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  try {
    await deleteProject(deleteTarget.value.id)
    if (selectedProject.value?.id === deleteTarget.value.id) {
      selectedProject.value = null
      members.value = []
    }
    deleteTarget.value = null
    await fetchProjects()
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
  if (!selectedProject.value) return
  try {
    await addProjectMember(selectedProject.value.id, userId)
    showAddMember.value = false
    addMemberKeyword.value = ''
    addMemberResults.value = []
    await fetchMembers(selectedProject.value.id)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '添加失败'
  }
}

async function handleConfirmRemoveMember(): Promise<void> {
  if (!selectedProject.value || !removeMemberTarget.value) return
  try {
    await removeProjectMember(selectedProject.value.id, removeMemberTarget.value.id)
    removeMemberTarget.value = null
    await fetchMembers(selectedProject.value.id)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '移除失败'
    removeMemberTarget.value = null
  }
}

onMounted(fetchProjects)
</script>

<template>
  <div class="flex h-full gap-4">
    <!-- 左侧：项目列表 -->
    <div class="w-72 shrink-0 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
        <h3 class="text-sm font-semibold text-slate-900">项目</h3>
        <button
          v-if="hasPermission('project:create')"
          class="rounded-md bg-purple-600 px-2.5 py-1 text-xs font-medium text-white transition-all hover:bg-purple-500"
          @click="handleCreate"
        >
          新建
        </button>
      </div>
      <div class="overflow-y-auto p-2" style="max-height: calc(100vh - 10rem)">
        <div
          v-for="project in projects"
          :key="project.id"
          class="mb-0.5 flex cursor-pointer items-center rounded-md px-3 py-2 text-sm transition-colors"
          :class="selectedProject?.id === project.id ? 'bg-purple-50 font-medium text-purple-700' : 'text-slate-700 hover:bg-slate-100'"
          @click="handleSelectProject(project)"
        >
          {{ project.name }}
        </div>
        <div v-if="projects.length === 0" class="py-8 text-center text-sm text-slate-400">
          暂无项目
        </div>
      </div>
    </div>

    <!-- 右侧：成员管理 -->
    <div class="flex-1 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <template v-if="selectedProject">
        <div class="flex h-12 items-center justify-between border-b border-slate-200/60 px-4">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-semibold text-slate-900">{{ selectedProject.name }}</h3>
            <span class="text-xs text-slate-400">{{ members.length }} 人</span>
          </div>
          <div class="flex gap-2">
            <button
              v-if="hasPermission('project:update')"
              class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200"
              @click="handleEdit"
            >
              编辑
            </button>
            <button
              v-if="hasPermission('project:update')"
              class="rounded-md bg-purple-600 px-2.5 py-1 text-xs font-medium text-white transition-all hover:bg-purple-500"
              @click="showAddMember = true"
            >
              添加成员
            </button>
            <button
              v-if="hasPermission('project:delete')"
              class="rounded-md bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-100"
              @click="deleteTarget = selectedProject"
            >
              删除
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
                <th class="px-3 py-2 font-medium text-slate-600">加入时间</th>
                <th class="px-3 py-2 font-medium text-slate-600">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="member in members" :key="member.id" class="border-b border-slate-100 last:border-0">
                <td class="px-3 py-2 text-slate-900">{{ member.display_name || member.username }}</td>
                <td class="px-3 py-2 text-slate-600">{{ member.username }}</td>
                <td class="px-3 py-2 text-slate-500">{{ member.position || '-' }}</td>
                <td class="px-3 py-2 text-slate-400">{{ member.joined_at?.slice(0, 10) || '-' }}</td>
                <td class="px-3 py-2">
                  <button
                    v-if="hasPermission('project:update')"
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
          请选择左侧项目
        </div>
      </template>
    </div>

    <!-- 新建/编辑项目弹窗 -->
    <div v-if="showCreateForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">{{ isEditing ? '编辑项目' : '新建项目' }}</h3>
        <form @submit.prevent="handleSubmit">
          <div class="mb-4">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">项目名称</label>
            <input
              v-model="formName"
              placeholder="请输入项目名称"
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
      :message="`确定要删除项目「${deleteTarget?.name}」吗？`"
      @confirm="handleConfirmDelete"
      @cancel="deleteTarget = null"
    />

    <ConfirmDialog
      :visible="!!removeMemberTarget"
      title="确认移除"
      :message="`确定要将「${removeMemberTarget?.display_name || removeMemberTarget?.username}」从项目中移除吗？`"
      @confirm="handleConfirmRemoveMember"
      @cancel="removeMemberTarget = null"
    />
  </div>
</template>
