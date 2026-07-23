<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  getBusinessScenarios,
  createBusinessScenario,
  updateBusinessScenario,
  deleteBusinessScenario,
  type BusinessScenario,
} from '@aihelms/shared'
import { usePermission } from '@aihelms/shared'
import HostedIcon from '@aihelms/shared/src/components/HostedIcon.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import IconPicker from '../../components/IconPicker.vue'

const { hasPermission } = usePermission()

const scenarios = ref<BusinessScenario[]>([])
const total = ref(0)
const isLoading = ref(false)
const keyword = ref('')
const includeInactive = ref(false)

const showForm = ref(false)
const editingId = ref<number | null>(null)
const formCode = ref('')
const formName = ref('')
const formDescription = ref('')
const formIconUrl = ref('/icons/v1/default.svg')
const formSortOrder = ref(0)
const formIsActive = ref(true)
const formError = ref('')
const deleteTarget = ref<BusinessScenario | null>(null)

async function fetchData(): Promise<void> {
  isLoading.value = true
  try {
    const result = await getBusinessScenarios(1, 100, keyword.value || undefined, includeInactive.value)
    scenarios.value = result.items
    total.value = result.total
  } finally {
    isLoading.value = false
  }
}

function handleCreate(): void {
  editingId.value = null
  formCode.value = ''
  formName.value = ''
  formDescription.value = ''
  formIconUrl.value = '/icons/v1/default.svg'
  formSortOrder.value = 0
  formIsActive.value = true
  formError.value = ''
  showForm.value = true
}

function handleEdit(scenario: BusinessScenario): void {
  editingId.value = scenario.id
  formCode.value = scenario.code
  formName.value = scenario.name
  formDescription.value = scenario.description
  formIconUrl.value = scenario.icon_url
  formSortOrder.value = scenario.sort_order
  formIsActive.value = scenario.is_active
  formError.value = ''
  showForm.value = true
}

async function handleSubmit(): Promise<void> {
  formError.value = ''
  if (!formCode.value.trim()) {
    formError.value = '请输入场景编码'
    return
  }
  if (!formName.value.trim()) {
    formError.value = '请输入场景名称'
    return
  }
  try {
    if (editingId.value) {
      await updateBusinessScenario(editingId.value, {
        name: formName.value.trim(),
        description: formDescription.value.trim(),
        icon_url: formIconUrl.value,
        sort_order: formSortOrder.value,
        is_active: formIsActive.value,
      })
    } else {
      await createBusinessScenario({
        code: formCode.value.trim(),
        name: formName.value.trim(),
        description: formDescription.value.trim(),
        icon_url: formIconUrl.value,
        sort_order: formSortOrder.value,
      })
    }
    showForm.value = false
    await fetchData()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  try {
    await deleteBusinessScenario(deleteTarget.value.id)
  } finally {
    deleteTarget.value = null
    await fetchData()
  }
}

const isEditing = computed(() => editingId.value !== null)

onMounted(fetchData)
</script>

<template>
  <div class="p-6">
    <div class="mb-5">
      <h2 class="text-lg font-semibold text-slate-900">业务场景管理</h2>
      <p class="mt-1 text-sm text-slate-500">
        业务场景用于给模型、MCP、Skill、智能体打标，支撑 AI 效能模块的业务场景维度分析。
      </p>
    </div>

    <div class="mb-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <input
          v-model="keyword"
          placeholder="搜索编码或名称..."
          class="h-8 w-52 rounded-lg border border-slate-200 bg-white px-3 text-sm placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
          @keyup.enter="fetchData"
        />
        <button
          class="h-8 rounded-lg bg-slate-100 px-3 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200"
          @click="fetchData"
        >
          搜索
        </button>
        <label class="flex items-center gap-2 text-xs text-slate-600">
          <input v-model="includeInactive" type="checkbox" class="rounded" @change="fetchData" />
          显示已停用
        </label>
      </div>
      <button
        v-if="hasPermission('user:update')"
        class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-3.5 py-1.5 text-xs font-medium text-white shadow-sm shadow-purple-500/20 transition-all hover:from-purple-500 hover:to-blue-500"
        @click="handleCreate"
      >
        新建场景
      </button>
    </div>

    <div class="overflow-hidden rounded-xl border border-slate-200/60 bg-white/60 backdrop-blur-xl">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-slate-200/60 bg-slate-50/50">
          <tr>
            <th class="px-4 py-2.5 font-medium text-slate-600">图标</th>
            <th class="px-4 py-2.5 font-medium text-slate-600">编码</th>
            <th class="px-4 py-2.5 font-medium text-slate-600">名称</th>
            <th class="px-4 py-2.5 font-medium text-slate-600">描述</th>
            <th class="px-4 py-2.5 font-medium text-slate-600">排序</th>
            <th class="px-4 py-2.5 font-medium text-slate-600">状态</th>
            <th class="px-4 py-2.5 font-medium text-slate-600">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="s in scenarios"
            :key="s.id"
            class="border-b border-slate-100 transition-colors hover:bg-slate-50/50"
          >
            <td class="px-4 py-3">
              <HostedIcon :src="s.icon_url" :size="20" :alt="s.name" />
            </td>
            <td class="px-4 py-3 font-mono text-xs text-slate-600">{{ s.code }}</td>
            <td class="px-4 py-3 font-medium text-slate-900">{{ s.name }}</td>
            <td class="px-4 py-3 text-slate-600">{{ s.description || '-' }}</td>
            <td class="px-4 py-3 text-xs text-slate-500">{{ s.sort_order }}</td>
            <td class="px-4 py-3">
              <span
                v-if="s.is_active"
                class="inline-flex rounded-md bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700"
              >
                启用
              </span>
              <span
                v-else
                class="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500"
              >
                停用
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex gap-3">
                <button
                  v-if="hasPermission('user:update')"
                  class="text-xs text-purple-500 hover:text-purple-600"
                  @click="handleEdit(s)"
                >
                  编辑
                </button>
                <button
                  v-if="hasPermission('user:delete')"
                  class="text-xs text-red-500 hover:text-red-600"
                  @click="deleteTarget = s"
                >
                  停用
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="isLoading" class="py-12 text-center text-sm text-slate-400">加载中...</div>
      <div v-if="!isLoading && scenarios.length === 0" class="py-12 text-center text-sm text-slate-400">
        暂无业务场景
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <div
      v-if="showForm"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
    >
      <div class="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white/90 p-6 shadow-xl backdrop-blur-xl">
        <h3 class="mb-4 text-lg font-semibold text-slate-900">
          {{ isEditing ? '编辑业务场景' : '新建业务场景' }}
        </h3>
        <form @submit.prevent="handleSubmit">
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">
              编码 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="formCode"
              :disabled="isEditing"
              placeholder="如：code_dev、customer_service"
              class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 font-mono text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20 disabled:bg-slate-50 disabled:text-slate-500"
            />
            <p v-if="isEditing" class="mt-1 text-xs text-slate-400">编码创建后不可修改</p>
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">
              名称 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="formName"
              placeholder="如：代码开发、客户服务"
              class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <div class="mb-3">
            <label class="mb-1.5 block text-sm font-medium text-slate-700">描述</label>
            <input
              v-model="formDescription"
              placeholder="可选"
              class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
            />
          </div>
          <div class="mb-3">
            <IconPicker v-model="formIconUrl" label="图标" />
          </div>
          <div class="mb-3 grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-slate-700">排序</label>
              <input
                v-model.number="formSortOrder"
                type="number"
                class="flex h-10 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm text-slate-900 focus:border-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
              />
            </div>
            <div v-if="isEditing">
              <label class="mb-1.5 block text-sm font-medium text-slate-700">状态</label>
              <label class="flex h-10 items-center gap-2 px-2">
                <input v-model="formIsActive" type="checkbox" class="rounded" />
                <span class="text-sm text-slate-700">启用</span>
              </label>
            </div>
          </div>
          <p v-if="formError" class="mb-3 text-sm text-red-500">{{ formError }}</p>
          <div class="flex justify-end gap-3">
            <button
              type="button"
              class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
              @click="showForm = false"
            >
              取消
            </button>
            <button
              type="submit"
              class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-purple-500/20 hover:from-purple-500 hover:to-blue-500"
            >
              {{ isEditing ? '保存' : '创建' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      :visible="!!deleteTarget"
      title="停用业务场景"
      :message="`确定停用「${deleteTarget?.name}」？停用后将不再显示在资源选择列表中。`"
      @confirm="handleConfirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>
