<script setup lang="ts">
// AI能力评估 - 信息展示页
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6 p-6">
    <!-- 页面标题区 -->
    <div class="rounded-xl bg-gradient-to-r from-indigo-50 to-violet-50 p-8">
      <h1 class="text-2xl font-bold text-slate-800">AI 能力评估</h1>
      <p class="mt-2 text-base text-slate-600">
        评估员工 AI 使用深度与效率，识别高效实践并推动组织 AI 能力提升
      </p>
    </div>

    <!-- 两栏卡片 -->
    <div class="grid gap-6 md:grid-cols-2">
      <!-- 人的 AI 能力评估 -->
      <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex items-center gap-3">
          <div
            class="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100"
          >
            <svg
              class="h-5 w-5 text-indigo-600"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-slate-800">
            人的 AI 能力评估
          </h2>
        </div>
        <p class="mb-4 text-sm text-slate-500">
          从多维度衡量员工对 AI 工具的掌握与运用水平
        </p>
        <ul class="space-y-2 text-sm text-slate-600">
          <li class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
            使用频率 — 日均调用次数与活跃天数
          </li>
          <li class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
            使用广度 — 覆盖模型与工具的多样性
          </li>
          <li class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
            使用深度 — 高级功能与复杂场景的运用
          </li>
          <li class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
            使用效率 — 单次交互的产出质量
          </li>
          <li class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
            成长趋势 — 能力提升的时间曲线
          </li>
        </ul>
      </div>

      <!-- 智能体/Skill 价值评估 -->
      <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex items-center gap-3">
          <div
            class="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100"
          >
            <svg
              class="h-5 w-5 text-violet-600"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 2v4" />
              <path d="m6.8 15-3.5 2" />
              <path d="m20.7 17-3.5-2" />
              <path d="M6.5 8.8 3 7" />
              <path d="m20.7 7-3.5 1.8" />
              <path d="M12 12v10" />
              <circle cx="12" cy="12" r="4" />
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-slate-800">
            智能体/Skill 价值评估
          </h2>
        </div>
        <p class="mb-4 text-sm text-slate-500">
          量化智能体与 Skill 对业务的实际贡献
        </p>
        <ul class="space-y-2 text-sm text-slate-600">
          <li class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-violet-400"></span>
            使用量 — 各智能体/Skill 的调用频次统计
          </li>
          <li class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-violet-400"></span>
            使用人数 — 活跃用户数与渗透率
          </li>
          <li class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-violet-400"></span>
            增长趋势 — 周/月环比变化与预测
          </li>
          <li class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 rounded-full bg-violet-400"></span>
            业务覆盖度 — 跨部门/场景的应用分布
          </li>
        </ul>
      </div>
    </div>

    <!-- 底部提示 -->
    <div
      class="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 px-5 py-4"
    >
      <svg
        class="h-5 w-5 shrink-0 text-slate-400"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4" />
        <path d="M12 8h.01" />
      </svg>
      <p class="text-sm text-slate-500">
        该模块将在成本分析数据积累充分后自动启用
      </p>
    </div>
  </div>
</template>
