<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Users,
  Activity,
  DollarSign,
  AlertCircle,
  ArrowUpRight,
  Package,
  Plug,
  Zap,
  Brain,
  Key,
  UserCheck,
  FolderTree,
  GitBranch,
  CircleDot,
} from 'lucide-vue-next'
import { getDashboard } from '@aihelms/shared'
import type { DashboardData, ResourceSummary } from '@aihelms/shared'

const router = useRouter()
const isLoading = ref(true)
const data = ref<DashboardData | null>(null)

const RESOURCE_ICONS: Record<string, typeof Package> = {
  model: Package,
  mcp: Plug,
  skill: Zap,
  agent: Brain,
  ai_key: Key,
  user: UserCheck,
  department: FolderTree,
  project: GitBranch,
}

const maxHourlyRequests = computed(() => {
  if (!data.value) return 1
  return Math.max(...data.value.hourlyTrend.map((h) => h.requests), 1)
})

async function loadData() {
  isLoading.value = true
  try {
    data.value = await getDashboard()
  } finally {
    isLoading.value = false
  }
}

function handleNavigate(path: string) {
  router.push(path)
}

function getResourceIcon(item: ResourceSummary) {
  return RESOURCE_ICONS[item.icon] || Package
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-5">
    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
    </div>

    <template v-else-if="data">
      <!-- Status Cards -->
      <div class="grid grid-cols-4 gap-4">
        <!-- Active Users -->
        <button
          class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 text-left shadow-sm backdrop-blur-xl transition hover:shadow-md"
          @click="handleNavigate('/efficiency')"
        >
          <div class="flex items-center justify-between">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50">
              <Users class="h-5 w-5 text-blue-600" />
            </div>
            <ArrowUpRight class="h-4 w-4 text-slate-300" />
          </div>
          <div class="mt-3 text-2xl font-bold text-slate-900">
            {{ data.status.activeUsers }}<span class="text-sm font-normal text-slate-500">人</span>
          </div>
          <div class="mt-1 text-xs text-slate-500">今日活跃用户</div>
          <div class="mt-1 text-xs text-green-600">
            较昨日 +{{ data.status.activeUsersChange }}
          </div>
        </button>

        <!-- Today Requests -->
        <button
          class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 text-left shadow-sm backdrop-blur-xl transition hover:shadow-md"
          @click="handleNavigate('/logs')"
        >
          <div class="flex items-center justify-between">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50">
              <Activity class="h-5 w-5 text-indigo-600" />
            </div>
            <ArrowUpRight class="h-4 w-4 text-slate-300" />
          </div>
          <div class="mt-3 text-2xl font-bold text-slate-900">
            {{ data.status.todayRequests.toLocaleString() }}<span class="text-sm font-normal text-slate-500">次</span>
          </div>
          <div class="mt-1 text-xs text-slate-500">今日调用</div>
          <div class="mt-1 text-xs text-slate-400">
            LLM {{ data.status.llmRequests }} / MCP {{ data.status.mcpRequests }}
          </div>
        </button>

        <!-- Today Cost -->
        <button
          class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 text-left shadow-sm backdrop-blur-xl transition hover:shadow-md"
          @click="handleNavigate('/efficiency')"
        >
          <div class="flex items-center justify-between">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50">
              <DollarSign class="h-5 w-5 text-amber-600" />
            </div>
            <ArrowUpRight class="h-4 w-4 text-slate-300" />
          </div>
          <div class="mt-3 text-2xl font-bold text-slate-900">
            ¥{{ data.status.todayCost.toLocaleString() }}
          </div>
          <div class="mt-1 text-xs text-slate-500">今日成本</div>
          <div class="mt-1 text-xs" :class="data.status.costChangePercent > 0 ? 'text-red-500' : 'text-green-600'">
            较昨日 {{ data.status.costChangePercent > 0 ? '+' : '' }}{{ data.status.costChangePercent }}%
          </div>
        </button>

        <!-- Pending Items -->
        <button
          class="rounded-2xl border p-5 text-left shadow-sm backdrop-blur-xl transition hover:shadow-md"
          :class="data.status.pendingCount > 0
            ? 'border-red-200 bg-red-50/70'
            : 'border-slate-200/60 bg-white/70'"
          @click="handleNavigate('/resource-approval')"
        >
          <div class="flex items-center justify-between">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg" :class="data.status.pendingCount > 0 ? 'bg-red-100' : 'bg-slate-100'">
              <AlertCircle class="h-5 w-5" :class="data.status.pendingCount > 0 ? 'text-red-600' : 'text-slate-500'" />
            </div>
            <span v-if="data.status.pendingCount > 0" class="flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
              {{ data.status.pendingCount }}
            </span>
            <ArrowUpRight v-else class="h-4 w-4 text-slate-300" />
          </div>
          <div class="mt-3 text-2xl font-bold" :class="data.status.pendingCount > 0 ? 'text-red-700' : 'text-slate-900'">
            {{ data.status.pendingCount }}<span class="text-sm font-normal" :class="data.status.pendingCount > 0 ? 'text-red-500' : 'text-slate-500'">件</span>
          </div>
          <div class="mt-1 text-xs text-slate-500">待处理</div>
          <div class="mt-1 text-xs text-slate-400">
            {{ data.status.pendingApprovals }}审批 + {{ data.status.pendingAlerts }}预警
          </div>
        </button>
      </div>

      <!-- Hourly Trend (full width) -->
      <div class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-slate-900">今日调用趋势</h3>
          <span class="cursor-help text-xs text-slate-400" title="今天 0:00 至当前时刻的逐小时调用量。可快速判断是否有异常尖峰或服务中断。">?</span>
        </div>
        <div class="flex h-36 items-end gap-1.5">
          <div
            v-for="point in data.hourlyTrend"
            :key="point.hour"
            class="group relative flex flex-1 flex-col items-center"
          >
            <div
              class="w-full rounded-t transition-all"
              :class="point.hour >= 9 && point.hour <= 18 ? 'bg-indigo-400' : 'bg-indigo-200'"
              :style="{ height: `${(point.requests / maxHourlyRequests) * 100}%`, minHeight: point.requests > 0 ? '4px' : '2px' }"
            ></div>
            <div class="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 rounded bg-slate-800 px-2 py-1 text-xs text-white opacity-0 shadow transition group-hover:opacity-100">
              {{ point.hour }}:00 — {{ point.requests }}次
            </div>
          </div>
        </div>
        <div class="mt-2 flex justify-between text-xs text-slate-400">
          <span>0:00</span>
          <span>6:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>23:00</span>
        </div>
      </div>

      <!-- Middle row: Pending Items + Recent Activities -->
      <div class="grid grid-cols-5 gap-4">
        <!-- Pending Items (60%) -->
        <div class="col-span-3 rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-slate-900">待办事项</h3>
            <span class="cursor-help text-xs text-slate-400" title="需要管理员处理的事项汇总。包括：待审批的资源申请、触发超支预警的预算项。点击可直接跳转处理。">?</span>
          </div>

          <div v-if="data.pendingItems.length === 0" class="flex flex-col items-center justify-center py-8">
            <div class="text-2xl">&#x2705;</div>
            <p class="mt-2 text-sm text-slate-500">一切正常，暂无需要处理的事项</p>
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="(item, idx) in data.pendingItems"
              :key="idx"
              class="flex items-center gap-3 rounded-xl border border-slate-100 bg-white/80 px-4 py-3 transition hover:border-slate-200 hover:shadow-sm"
            >
              <span class="shrink-0 text-base">
                {{ item.type === 'approval' ? '\uD83D\uDD34' : '\u26A0\uFE0F' }}
              </span>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm text-slate-700">{{ item.description }}</p>
                <p class="mt-0.5 text-xs text-slate-400">{{ item.timeAgo }}</p>
              </div>
              <button
                class="shrink-0 rounded-md bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600 transition hover:bg-indigo-100"
                @click="handleNavigate(item.linkUrl)"
              >
                去处理 &rarr;
              </button>
            </div>
          </div>
        </div>

        <!-- Recent Activities (40%) -->
        <div class="col-span-2 rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-slate-900">近期动态</h3>
            <span class="cursor-help text-xs text-slate-400" title="最近的管理操作记录（取自管理员审计日志最新 5 条）。点击可查看操作详情。">?</span>
          </div>
          <div class="space-y-3">
            <div
              v-for="(activity, idx) in data.recentActivities"
              :key="idx"
              class="flex items-start gap-3"
            >
              <div class="mt-1.5 flex flex-col items-center">
                <CircleDot class="h-3 w-3 text-indigo-400" />
                <div v-if="idx < data.recentActivities.length - 1" class="mt-1 h-6 w-px bg-slate-200"></div>
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-sm text-slate-700">
                  <span class="font-medium text-slate-900">{{ activity.actor }}</span>
                  {{ activity.action }}
                </p>
                <p class="mt-0.5 text-xs text-slate-400">{{ activity.timeAgo }}</p>
              </div>
            </div>
          </div>
          <div class="mt-4 border-t border-slate-100 pt-3">
            <button
              class="text-xs font-medium text-indigo-600 hover:text-indigo-700"
              @click="handleNavigate('/audit')"
            >
              查看全部日志 &rarr;
            </button>
          </div>
        </div>
      </div>

      <!-- Bottom row: Resource Summary (full width) -->
      <div class="rounded-2xl border border-slate-200/60 bg-white/70 p-5 shadow-sm backdrop-blur-xl">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-slate-900">资源概览</h3>
          <span class="cursor-help text-xs text-slate-400" title="平台当前管理的各类 AI 资源数量汇总。点击数字可跳转到对应管理页面。">?</span>
        </div>
        <div class="grid grid-cols-4 gap-3">
          <button
            v-for="resource in data.resources"
            :key="resource.name"
            class="flex items-center gap-3 rounded-xl border border-slate-100 bg-white/80 px-3 py-3 text-left transition hover:border-slate-200 hover:shadow-sm"
            @click="handleNavigate(resource.linkPath)"
          >
            <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-50">
              <component :is="getResourceIcon(resource)" class="h-4 w-4 text-slate-600" />
            </div>
            <div class="min-w-0">
              <div class="truncate text-xs font-medium text-slate-700">{{ resource.name }}</div>
              <div class="mt-0.5 text-xs text-slate-400">
                <span class="font-semibold text-slate-900">{{ resource.total }}</span> 总数
                <template v-if="resource.active !== null">
                  / <span class="font-semibold text-green-600">{{ resource.active }}</span> {{ resource.activeLabel }}
                </template>
              </div>
            </div>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
