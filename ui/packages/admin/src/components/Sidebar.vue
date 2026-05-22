<script setup lang="ts">
import { useAuth, usePermission } from '@aihelms/shared'
import { useRoute } from 'vue-router'
import { ref, type Component } from 'vue'
import {
  FolderTree,
  Users,
  KeyRound,
  GitBranch,
  Brain,
  Zap,
  Plug,
  Factory,
  Package,
  Wallet,
  FileText,
  Shield,
  Search,
  Database,
  Ruler,
  File,
  Key,
  Fingerprint,
  Bot,
  Store,
  Cpu,
  BarChart3,
  Lock,
  FlaskConical,
  LayoutDashboard,
  ClipboardCheck,
  UserCircle2,
} from 'lucide-vue-next'

const route = useRoute()
const { hasPermission } = usePermission()
const { currentUser } = useAuth()

interface MenuItem {
  label: string
  icon?: Component
  path?: string
  permission?: string
  children?: MenuItem[]
  disabled?: boolean
}

const menuGroups = ref<{ title: string; icon?: Component; items: MenuItem[] }[]>([
  {
    title: 'AI身份',
    icon: Fingerprint,
    items: [
      { label: '部门管理', icon: FolderTree, path: '/departments', permission: 'department:read' },
      { label: '项目管理', icon: GitBranch, path: '/projects', permission: 'project:read' },
      { label: '人员管理', icon: Users, path: '/users', permission: 'user:read' },
      { label: 'AI身份管理', icon: Key, path: '/ai-keys', permission: 'user:read' },
    ],
  },
  {
    title: '资源审计',
    icon: ClipboardCheck,
    items: [
      { label: '审批管理', icon: ClipboardCheck, path: '/resource-approval', permission: 'resource_application:read' },
      { label: '日志管理', icon: FileText, path: '/logs', permission: 'usage_log:read' },
    ],
  },
  {
    title: '智能体中心',
    icon: Bot,
    items: [
      { label: '智能体列表', icon: Brain, path: '/agents', permission: 'agent:read' },
    ],
  },
  {
    title: 'AI市场',
    icon: Store,
    items: [
      { label: 'Skill管理', icon: Zap, path: '/skills', permission: 'skill:read' },
      { label: 'MCP管理', icon: Plug, path: '/mcp', permission: 'mcp:read' },
    ],
  },
  {
    title: '模型纳管',
    icon: Cpu,
    items: [
      { label: '供应商管理', icon: Factory, path: '/providers', permission: 'user:read' },
      { label: '模型管理', icon: Package, path: '/models', permission: 'user:read' },
    ],
  },
  {
    title: 'AI效能',
    icon: Wallet,
    items: [
      { label: 'AI总览', icon: LayoutDashboard, path: '/efficiency', permission: 'efficiency:read' },
      { label: '多维度分析', icon: BarChart3, path: '/efficiency/analysis', permission: 'efficiency:read' },
      { label: '智能体经营', icon: Bot, path: '/efficiency/agents', permission: 'efficiency:read' },
      { label: '模型偏好', icon: Cpu, path: '/efficiency/models', permission: 'efficiency:read' },
      { label: '预算管控', icon: Wallet, path: '/efficiency/budget', permission: 'efficiency:read' },
      { label: '分析报告', icon: FileText, path: '/efficiency/reports', permission: 'efficiency:read' },
      { label: 'AI能力评估', icon: Brain, path: '/efficiency/capability', disabled: true },
    ],
  },
  {
    title: '安全',
    icon: Lock,
    items: [
      { label: '管理员日志', icon: Shield, path: '/audit', permission: 'audit_log:read' },
      { label: '敏感信息识别', icon: Search, path: '/sensitive', disabled: true },
      { label: 'API Key', icon: KeyRound, path: '/api-keys', permission: 'api_key:read' },
    ],
  },
  {
    title: 'AI实验室',
    icon: FlaskConical,
    items: [
      { label: '上下文缓存', icon: Database, path: '/caching', disabled: true },
      { label: '策略管理', icon: Ruler, path: '/policies', disabled: true },
      { label: '文件处理', icon: File, path: '/files', disabled: true },
    ],
  },
])

const expandedGroups = ref<Set<string>>(new Set(['AI身份', '资源审计', '智能体中心', 'AI市场', '模型纳管', 'AI效能', '安全', 'AI实验室']))

function toggleGroup(title: string): void {
  if (expandedGroups.value.has(title)) {
    expandedGroups.value.delete(title)
  } else {
    expandedGroups.value.add(title)
  }
}

function isActive(path: string | undefined): boolean {
  if (!path) return false
  // 精确匹配优先：如果有其他菜单项的 path 是当前 path 的更长前缀，则当前项不应高亮
  if (route.path === path) return true
  // 子路径匹配：仅当不存在更精确的菜单项时
  if (!route.path.startsWith(path + '/')) return false
  // 查找是否存在更精确（更长）的菜单 path 匹配当前路由
  const allPaths = menuGroups.value.flatMap((g) => g.items.map((i) => i.path).filter(Boolean) as string[])
  const moreSpecific = allPaths.some(
    (p) => p !== path && p.startsWith(path + '/') && (route.path === p || route.path.startsWith(p + '/')),
  )
  return !moreSpecific
}

function isVisible(item: MenuItem): boolean {
  if (!item.permission) return true
  return hasPermission(item.permission)
}
</script>

<template>
  <aside class="relative z-10 flex w-[13rem] flex-col overflow-hidden border-r border-slate-200/60 bg-white/60 backdrop-blur-xl">
    <div class="flex h-14 shrink-0 items-center justify-center border-b border-slate-200/60">
      <img src="/static/img/logo.png" alt="AIHelms" class="h-7" />
    </div>

    <nav class="flex-1 overflow-y-auto p-2">
      <!-- Dashboard 独立项 -->
      <RouterLink
        to="/"
        class="mb-2 flex h-9 items-center gap-2 rounded-md px-2 text-sm font-semibold transition-all duration-150"
        :class="route.path === '/'
          ? 'bg-purple-50 text-purple-700'
          : 'text-slate-900 hover:bg-slate-100 active:bg-slate-200'"
      >
        <LayoutDashboard class="h-4 w-4" :class="route.path === '/' ? 'text-purple-500' : 'text-slate-500'" />
        Dashboard
      </RouterLink>

      <div v-for="group in menuGroups" :key="group.title" class="mb-3">
        <!-- 一级：分组标题（可折叠） -->
        <button
          class="flex h-9 w-full items-center justify-between rounded-md px-2 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-100"
          @click="toggleGroup(group.title)"
        >
          <span class="flex items-center gap-2">
            <component :is="group.icon" v-if="group.icon" class="h-4 w-4 text-slate-500" />
            {{ group.title }}
          </span>
          <svg
            class="h-3.5 w-3.5 text-slate-400 transition-transform duration-200"
            :class="expandedGroups.has(group.title) ? 'rotate-90' : ''"
            viewBox="0 0 16 16"
          >
            <path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" />
          </svg>
        </button>

        <!-- 展开内容 -->
        <div v-if="expandedGroups.has(group.title)" class="mt-0.5 ml-3">
          <template v-for="item in group.items" :key="item.label">
            <RouterLink
              v-if="!item.disabled && isVisible(item) && item.path"
              :to="item.path"
              class="flex h-8 items-center gap-2 rounded-md px-2 text-sm transition-all duration-150"
              :class="isActive(item.path)
                ? 'bg-purple-50 font-medium text-purple-700'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 active:bg-slate-200'"
            >
              <component
                :is="item.icon"
                v-if="item.icon"
                class="h-4 w-4 shrink-0 transition-colors"
                :class="isActive(item.path) ? 'text-purple-500' : 'text-slate-400'"
              />
              {{ item.label }}
            </RouterLink>
            <span
              v-else-if="item.disabled"
              class="flex h-8 cursor-not-allowed items-center gap-2 rounded-md px-2 text-sm text-slate-400"
            >
              <component :is="item.icon" v-if="item.icon" class="h-4 w-4 shrink-0 opacity-40" />
              {{ item.label }}
            </span>
          </template>
        </div>
      </div>
    </nav>

    <div class="shrink-0 border-t border-slate-200/60 p-2">
      <a
        href="/web/"
        class="mb-1 flex h-8 items-center gap-2 rounded-md px-2 text-sm text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
        title="切换到用户端"
      >
        <UserCircle2 class="h-4 w-4 text-slate-400" />
        切换到用户端
      </a>
      <div class="flex items-center gap-2 rounded-md px-2 py-2 transition-colors hover:bg-slate-100">
        <div class="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-r from-purple-500 to-blue-500 text-xs font-medium text-white">
          {{ currentUser?.username?.charAt(0)?.toUpperCase() }}
        </div>
        <span class="truncate text-sm text-slate-700">{{ currentUser?.username }}</span>
      </div>
    </div>
  </aside>
</template>
