<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
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
const selectedUserIds = ref<Set<number>>(new Set())
const isSearching = ref(false)
const searchPage = ref(1)
const searchHasMore = ref(false)
const isLoadingMore = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | null = null
const PAGE_SIZE = 20

const existingMemberIds = computed(() => new Set(members.value.map((m: ProjectMember) => m.id)))

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
  isSearching.value = true
  searchPage.value = 1
  const result = await getUsers(1, PAGE_SIZE, addMemberKeyword.value || undefined)
  addMemberResults.value = result.items.map((u: { id: number; username: string; display_name: string }) => ({
    id: u.id,
    username: u.username,
    display_name: u.display_name,
  }))
  searchHasMore.value = result.total > PAGE_SIZE
  isSearching.value = false
}

async function handleLoadMore(): Promise<void> {
  if (isLoadingMore.value || !searchHasMore.value) return
  isLoadingMore.value = true
  searchPage.value += 1
  const result = await getUsers(searchPage.value, PAGE_SIZE, addMemberKeyword.value || undefined)
  const newItems = result.items.map((u: { id: number; username: string; display_name: string }) => ({
    id: u.id,
    username: u.username,
    display_name: u.display_name,
  }))
  addMemberResults.value = [...addMemberResults.value, ...newItems]
  searchHasMore.value = addMemberResults.value.length < result.total
  isLoadingMore.value = false
}

function handleListScroll(event: Event): void {
  const el = event.target as HTMLElement
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
    handleLoadMore()
  }
}

function handleSearchInput(): void {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    handleSearchUsers()
  }, 300)
}

function toggleUserSelection(userId: number): void {
  const newSet = new Set(selectedUserIds.value)
  if (newSet.has(userId)) {
    newSet.delete(userId)
  } else {
    newSet.add(userId)
  }
  selectedUserIds.value = newSet
}

function toggleSelectAll(): void {
  const selectableUsers = addMemberResults.value.filter(u => !existingMemberIds.value.has(u.id))
  if (selectedUserIds.value.size === selectableUsers.length && selectableUsers.length > 0) {
    selectedUserIds.value = new Set()
  } else {
    selectedUserIds.value = new Set(selectableUsers.map(u => u.id))
  }
}

async function handleBatchAddMembers(): Promise<void> {
  if (!selectedProject.value || selectedUserIds.value.size === 0) return
  try {
    for (const userId of selectedUserIds.value) {
      await addProjectMember(selectedProject.value.id, userId)
    }
    showAddMember.value = false
    addMemberKeyword.value = ''
    addMemberResults.value = []
    selectedUserIds.value = new Set()
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
              @click="showAddMember = true; handleSearchUsers()"
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

    <!-- 添加成员弹窗 - 穿梭框 -->
    <div v-if="showAddMember" class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="w-full max-w-2xl rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">添加成员</h3>
        <div class="flex gap-4">
          <!-- 左侧：搜索候选 -->
          <div class="flex-1">
            <div class="mb-2">
              <input
                v-model="addMemberKeyword"
                placeholder="输入用户名或姓名搜索"
                class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
                @input="handleSearchInput"
              />
            </div>
            <div class="h-64 overflow-y-auto rounded-lg border border-slate-200 bg-white" @scroll="handleListScroll">
              <div v-if="addMemberResults.length > 0" class="flex items-center border-b border-slate-100 px-3 py-2">
                <label class="flex cursor-pointer items-center gap-2 text-xs text-slate-500">
                  <input
                    type="checkbox"
                    class="h-3.5 w-3.5 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
                    :checked="selectedUserIds.size > 0 && selectedUserIds.size === addMemberResults.filter(u => !existingMemberIds.has(u.id)).length"
                    @change="toggleSelectAll"
                  />
                  全选
                </label>
              </div>
              <div
                v-for="user in addMemberResults"
                :key="user.id"
                class="flex items-center gap-3 px-3 py-2 transition-colors"
                :class="existingMemberIds.has(user.id) ? 'cursor-not-allowed bg-slate-50 opacity-50' : selectedUserIds.has(user.id) ? 'cursor-pointer bg-purple-50' : 'cursor-pointer hover:bg-slate-50'"
                @click="!existingMemberIds.has(user.id) && toggleUserSelection(user.id)"
              >
                <input
                  type="checkbox"
                  class="h-3.5 w-3.5 rounded border-slate-300 text-purple-600 focus:ring-purple-500/20"
                  :checked="selectedUserIds.has(user.id) || existingMemberIds.has(user.id)"
                  :disabled="existingMemberIds.has(user.id)"
                  @click.stop
                  @change="!existingMemberIds.has(user.id) && toggleUserSelection(user.id)"
                />
                <div class="flex-1 truncate">
                  <span class="text-sm text-slate-900">{{ user.display_name || user.username }}</span>
                  <span v-if="user.display_name" class="ml-2 text-xs text-slate-400">{{ user.username }}</span>
                </div>
                <span v-if="existingMemberIds.has(user.id)" class="shrink-0 text-xs text-slate-400">已添加</span>
              </div>
              <div v-if="isLoadingMore" class="py-2 text-center text-xs text-slate-400">加载中...</div>
              <div v-else-if="searchHasMore && addMemberResults.length > 0" class="py-2 text-center text-xs text-slate-300">滚动加载更多</div>
              <div v-if="isSearching && addMemberResults.length === 0" class="py-8 text-center text-sm text-slate-400">加载中...</div>
              <div v-else-if="!isSearching && addMemberResults.length === 0" class="py-8 text-center text-sm text-slate-400">暂无用户</div>
            </div>
          </div>

          <!-- 右侧：已选列表 -->
          <div class="w-48 shrink-0">
            <div class="mb-2 flex h-10 items-center">
              <span class="text-sm font-medium text-slate-700">已选 {{ selectedUserIds.size }} 人</span>
            </div>
            <div class="h-64 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50/50">
              <div
                v-for="user in addMemberResults.filter(u => selectedUserIds.has(u.id))"
                :key="user.id"
                class="flex items-center justify-between px-3 py-2"
              >
                <span class="truncate text-sm text-slate-700">{{ user.display_name || user.username }}</span>
                <button
                  class="shrink-0 text-xs text-red-400 transition-colors hover:text-red-600"
                  @click="toggleUserSelection(user.id)"
                >
                  移除
                </button>
              </div>
              <div v-if="selectedUserIds.size === 0" class="py-8 text-center text-sm text-slate-400">请从左侧选择</div>
            </div>
          </div>
        </div>

        <p v-if="errorMessage" class="mt-3 text-sm text-red-500">{{ errorMessage }}</p>
        <div class="mt-4 flex justify-end gap-3">
          <button
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
            @click="showAddMember = false; addMemberResults = []; selectedUserIds = new Set()"
          >
            取消
          </button>
          <button
            class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500 active:scale-[0.98] disabled:opacity-50"
            :disabled="selectedUserIds.size === 0"
            @click="handleBatchAddMembers"
          >
            确认添加 ({{ selectedUserIds.size }})
          </button>
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
