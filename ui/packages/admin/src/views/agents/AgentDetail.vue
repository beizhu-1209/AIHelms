<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getAgentById,
  getAgentCategories,
  getAgentPlatforms,
  createAgent,
  updateAgent,
  deleteAgent,
  getDepartmentTree,
  getAiKeys,
  type Agent,
  type AgentCategory,
  type AgentPlatform,
  type DeptTreeNode,
  type AiKey,
} from '@aihelms/shared'
import { toast, usePermission } from '@aihelms/shared'
import { ArrowLeft, Trash2, ExternalLink, Copy } from 'lucide-vue-next'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import IconPicker from '../../components/IconPicker.vue'

const { hasPermission } = usePermission()
const route = useRoute()
const router = useRouter()

const isNew = computed(() => route.params.id === 'new')
const agentId = computed(() => (isNew.value ? null : Number(route.params.id)))

const agent = ref<Agent | null>(null)
const categories = ref<AgentCategory[]>([])
const platforms = ref<AgentPlatform[]>([])
const deptTree = ref<DeptTreeNode[]>([])
const sceneKeys = ref<AiKey[]>([])
const loading = ref(false)
const saving = ref(false)
const showDelete = ref(false)
const urlCopied = ref(false)

const form = ref({
  name: '',
  icon: '',
  description: '',
  platform: '',
  category: 'general',
  department_id: null as number | null,
  project_id: null as number | null,
  cost_attribution: 'owner',
  ai_key_id: null as number | null,
  chat_url: '',
  tags: '',
  status: 'online',
  is_published: false,
  requires_approval: false,
})

interface FlatDept { id: number; name: string; depth: number }

function flattenDepts(nodes: DeptTreeNode[], depth: number = 0): FlatDept[] {
  const result: FlatDept[] = []
  for (const n of nodes) {
    result.push({ id: n.id, name: n.name, depth })
    if (n.children?.length) result.push(...flattenDepts(n.children, depth + 1))
  }
  return result
}

const flatDepts = computed(() => flattenDepts(deptTree.value))

const filteredKeys = computed(() => {
  return sceneKeys.value
})

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const [cats, plats, tree, keysRes] = await Promise.all([
      getAgentCategories(),
      getAgentPlatforms(),
      getDepartmentTree(),
      getAiKeys(1, 200),
    ])
    categories.value = cats
    platforms.value = plats
    deptTree.value = tree
    sceneKeys.value = keysRes.items.filter(k => k.key_type.includes('scene'))
    if (!isNew.value && agentId.value) {
      const a = await getAgentById(agentId.value)
      agent.value = a
      form.value = {
        name: a.name,
        icon: a.icon,
        description: a.description,
        platform: a.platform,
        category: a.category,
        department_id: a.department_id ?? null,
        project_id: a.project_id ?? null,
        cost_attribution: a.cost_attribution || 'owner',
        ai_key_id: a.ai_key_id ?? null,
        chat_url: a.chat_url,
        tags: (a.tags || []).join(', '),
        status: a.status,
        is_published: a.is_published,
        requires_approval: a.requires_approval,
      }
    } else {
      form.value.category = cats[0]?.name || 'general'
      form.value.platform = plats[0]?.name || ''
    }
  } catch (e) {
    toast.error((e as { message?: string }).message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function handleSave(): Promise<void> {
  if (!form.value.name) {
    toast.error('请填写名称')
    return
  }
  if (!form.value.platform) {
    toast.error('请选择平台')
    return
  }
  saving.value = true
  try {
    const tags = form.value.tags
      ? form.value.tags.split(',').map((t) => t.trim()).filter(Boolean)
      : []
    const payload = {
      name: form.value.name,
      icon: form.value.icon,
      description: form.value.description,
      platform: form.value.platform,
      category: form.value.category,
      department_id: form.value.department_id,
      project_id: form.value.project_id,
      cost_attribution: form.value.cost_attribution,
      ai_key_id: form.value.ai_key_id,
      chat_url: form.value.chat_url,
      tags,
      status: form.value.status,
      is_published: form.value.is_published,
      requires_approval: form.value.requires_approval,
    }
    if (isNew.value) {
      const created = await createAgent(payload)
      toast.success('智能体创建成功')
      router.replace(`/agents/${created.id}`)
    } else if (agentId.value) {
      const updated = await updateAgent(agentId.value, payload)
      toast.success('智能体更新成功')
      agent.value = updated
    }
  } catch (e) {
    toast.error((e as { message?: string }).message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(): Promise<void> {
  if (!agentId.value) return
  try {
    await deleteAgent(agentId.value)
    toast.success('智能体删除成功')
    router.push('/agents')
  } catch (e) {
    toast.error((e as { message?: string }).message || '删除失败')
  }
}

function copyUrl(): void {
  if (!form.value.chat_url) return
  navigator.clipboard.writeText(form.value.chat_url)
  urlCopied.value = true
  setTimeout(() => (urlCopied.value = false), 2000)
}

function openUrl(): void {
  if (form.value.chat_url) window.open(form.value.chat_url, '_blank')
}

onMounted(loadData)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <button
        class="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
        @click="router.push('/agents')"
      >
        <ArrowLeft class="h-4 w-4" />
        返回列表
      </button>
      <div v-if="!isNew && hasPermission('agent:delete')" class="flex gap-2">
        <button
          class="flex items-center gap-1 rounded-lg bg-red-50 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-100"
          @click="showDelete = true"
        >
          <Trash2 class="h-4 w-4" />
          删除
        </button>
      </div>
    </div>

    <div v-if="loading" class="py-20 text-center text-sm text-slate-400">加载中...</div>
    <template v-else>
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 class="mb-5 text-xl font-bold text-slate-900">
          {{ isNew ? '新建智能体' : `编辑：${agent?.name}` }}
        </h1>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">名称 *</label>
            <input
              v-model="form.name"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div>
            <IconPicker v-model="form.icon" label="图标" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">平台 *</label>
            <select
              v-model="form.platform"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            >
              <option v-for="p in platforms" :key="p.id" :value="p.name">{{ p.label || p.name }}</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">分类</label>
            <select
              v-model="form.category"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            >
              <option v-for="c in categories" :key="c.id" :value="c.name">{{ c.name }}</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">描述</label>
            <textarea
              v-model="form.description"
              rows="2"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>

          <!-- 归属与成本 -->
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">归属部门 *</label>
            <select
              v-model="form.department_id"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            >
              <option :value="null">请选择</option>
              <option v-for="d in flatDepts" :key="d.id" :value="d.id">
                {{ '　'.repeat(d.depth) + d.name }}
              </option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">成本归属</label>
            <select
              v-model="form.cost_attribution"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            >
              <option value="owner">归属部门/项目（owner）</option>
              <option value="user">归属使用人（user）</option>
            </select>
          </div>
          <div v-if="form.cost_attribution === 'owner'" class="col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">绑定场景 Key</label>
            <select
              v-model="form.ai_key_id"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            >
              <option :value="null">不绑定</option>
              <option v-for="k in filteredKeys" :key="k.id" :value="k.id">
                {{ k.name }} ({{ k.models?.length || 0 }} 模型, {{ k.mcps?.length || 0 }} MCP)
              </option>
            </select>
            <p class="mt-1 text-xs text-slate-400">选择该智能体使用的场景 Key，成本将计入 Key 所属的部门/项目</p>
          </div>
          <div v-else class="col-span-2">
            <p class="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
              user 模式：系统将为每位用户创建独立的场景 Key，成本归属到个人（二期功能）
            </p>
          </div>
          <div class="col-span-2">
            <div class="mb-1 flex items-center justify-between">
              <label class="text-sm font-medium text-slate-700">Chat URL</label>
              <div v-if="form.chat_url" class="flex gap-1">
                <button class="flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 hover:bg-slate-200" @click="copyUrl">
                  <Copy class="h-3 w-3" />
                  {{ urlCopied ? '已复制' : '复制' }}
                </button>
                <button class="flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 hover:bg-slate-200" @click="openUrl">
                  <ExternalLink class="h-3 w-3" />
                  打开
                </button>
              </div>
            </div>
            <input
              v-model="form.chat_url"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-xs focus:border-purple-500 focus:outline-none"
              placeholder="https://dify.example.com/chatbot/xxx"
            />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">状态</label>
            <select
              v-model="form.status"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            >
              <option value="online">在线</option>
              <option value="offline">下线</option>
              <option value="loading">加载中</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">标签（逗号分隔）</label>
            <input
              v-model="form.tags"
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
              placeholder="客服, 多轮对话"
            />
          </div>
          <div class="col-span-2 flex items-center gap-4">
            <label class="flex items-center gap-2 text-sm text-slate-700">
              <input v-model="form.is_published" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
              发布到用户端
            </label>
            <label class="flex items-center gap-2 text-sm text-slate-700">
              <input
                v-model="form.requires_approval"
                type="checkbox"
                :disabled="!form.is_published"
                class="h-4 w-4 rounded border-slate-300 disabled:opacity-50"
              />
              领用前需要审批
            </label>
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-3 border-t border-slate-100 pt-4">
          <button
            class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            @click="router.push('/agents')"
          >
            取消
          </button>
          <button
            class="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
            :disabled="saving"
            @click="handleSave"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </template>

    <ConfirmDialog
      :visible="showDelete"
      title="删除智能体"
      :message="`确认删除 ${agent?.name}？此操作不可恢复。`"
      @confirm="handleDelete"
      @cancel="showDelete = false"
    />
  </div>
</template>
