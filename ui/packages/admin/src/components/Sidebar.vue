<script setup lang="ts">
import { useAuth, usePermission } from '@aihelms/shared'
import { useRoute } from 'vue-router'
import { ref } from 'vue'

const route = useRoute()
const { hasPermission } = usePermission()
const { currentUser } = useAuth()

interface MenuItem {
  label: string
  path?: string
  permission?: string
  children?: MenuItem[]
  disabled?: boolean
}

const menuGroups = ref<{ title: string; items: MenuItem[] }[]>([
  {
    title: 'AI身份',
    items: [
      {
        label: '组织管理',
        children: [
          { label: '部门管理', path: '/admin/organizations', permission: 'organization:read' },
          { label: '人员管理', path: '/admin/users', permission: 'user:read' },
          { label: '角色管理', path: '/admin/roles', permission: 'role:read' },
          { label: '分支机构', path: '/admin/branches', permission: 'organization:read' },
          { label: 'SSO集成', path: '/admin/sso', disabled: true },
        ],
      },
      {
        label: 'AI身份',
        children: [
          { label: 'API Key管理', path: '/admin/api-keys', disabled: true },
        ],
      },
    ],
  },
  {
    title: '智能体管理',
    items: [
      { label: '智能体列表', path: '/admin/agents', disabled: true },
    ],
  },
  {
    title: 'AI市场',
    items: [
      { label: 'Skill管理', path: '/admin/skills', disabled: true },
      { label: 'MCP管理', path: '/admin/mcp', disabled: true },
      { label: '审批管理', path: '/admin/approvals', disabled: true },
    ],
  },
  {
    title: '模型纳管',
    items: [
      { label: '供应商管理', path: '/admin/providers', disabled: true },
      { label: '模型管理', path: '/admin/models', disabled: true },
    ],
  },
  {
    title: '数据中心',
    items: [
      { label: '成本中心', path: '/admin/cost', disabled: true },
      { label: '日志管理', path: '/admin/logs', disabled: true },
    ],
  },
  {
    title: '安全',
    items: [
      { label: '管理员日志', path: '/admin/audit', disabled: true },
      { label: '敏感信息识别', path: '/admin/sensitive', disabled: true },
    ],
  },
  {
    title: 'AI实验室',
    items: [
      { label: '上下文缓存', path: '/admin/caching', disabled: true },
      { label: '策略管理', path: '/admin/policies', disabled: true },
      { label: '文件处理', path: '/admin/files', disabled: true },
    ],
  },
])

const expandedGroups = ref<Set<string>>(new Set(['AI身份']))

function toggleGroup(title: string): void {
  if (expandedGroups.value.has(title)) {
    expandedGroups.value.delete(title)
  } else {
    expandedGroups.value.add(title)
  }
}

function isActive(path: string | undefined): boolean {
  if (!path) return false
  return route.path.startsWith(path)
}

function isVisible(item: MenuItem): boolean {
  if (!item.permission) return true
  return hasPermission(item.permission)
}
</script>

<template>
  <aside class="flex w-56 flex-col overflow-y-auto bg-gray-900">
    <div class="flex h-14 shrink-0 items-center justify-center border-b border-gray-700">
      <h1 class="text-lg font-bold text-white">AIHelms</h1>
    </div>

    <nav class="mt-2 flex-1 px-2">
      <div v-for="group in menuGroups" :key="group.title" class="mb-1">
        <button
          class="flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-400 hover:text-gray-200"
          @click="toggleGroup(group.title)"
        >
          {{ group.title }}
          <span class="text-[10px]">{{ expandedGroups.has(group.title) ? '▾' : '▸' }}</span>
        </button>

        <div v-if="expandedGroups.has(group.title)" class="ml-1">
          <template v-for="item in group.items" :key="item.label">
            <template v-if="item.children">
              <div class="mb-1 mt-1 px-2 text-[11px] font-medium text-gray-500">{{ item.label }}</div>
              <template v-for="child in item.children" :key="child.label">
                <RouterLink
                  v-if="!child.disabled && isVisible(child) && child.path"
                  :to="child.path"
                  class="block rounded-md px-3 py-1.5 text-sm transition-colors"
                  :class="isActive(child.path) ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'"
                >
                  {{ child.label }}
                </RouterLink>
                <span
                  v-else-if="child.disabled"
                  class="block cursor-not-allowed rounded-md px-3 py-1.5 text-sm text-gray-600"
                >
                  {{ child.label }}
                  <span class="ml-1 text-[10px] text-gray-700">即将上线</span>
                </span>
              </template>
            </template>
            <template v-else>
              <RouterLink
                v-if="!item.disabled && isVisible(item) && item.path"
                :to="item.path"
                class="block rounded-md px-3 py-1.5 text-sm transition-colors"
                :class="isActive(item.path) ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'"
              >
                {{ item.label }}
              </RouterLink>
              <span
                v-else-if="item.disabled"
                class="block cursor-not-allowed rounded-md px-3 py-1.5 text-sm text-gray-600"
              >
                {{ item.label }}
                <span class="ml-1 text-[10px] text-gray-700">即将上线</span>
              </span>
            </template>
          </template>
        </div>
      </div>
    </nav>

    <div class="shrink-0 border-t border-gray-700 p-4">
      <p class="truncate text-xs text-gray-400">{{ currentUser?.username }}</p>
    </div>
  </aside>
</template>
