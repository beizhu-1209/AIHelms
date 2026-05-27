<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-slate-800">AI 身份管理</h1>
      <div class="flex items-center gap-3">
        <button
          class="rounded-xl border border-slate-200/60 bg-white/70 px-4 py-2.5 text-sm font-medium text-slate-600 backdrop-blur-xl transition hover:bg-white/90"
          @click="showScenarioDialog = true"
        >场景管理</button>
        <button
          class="rounded-xl bg-gradient-to-r from-purple-500 to-purple-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:from-purple-600 hover:to-purple-700"
          @click="showBatchResource = true"
        >批量设置</button>
      </div>
    </div>

    <div class="flex gap-1 rounded-xl bg-white/50 p-1 backdrop-blur-sm">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        :class="['rounded-lg px-4 py-2 text-sm font-medium transition', activeTab === tab.value ? 'bg-white/80 text-purple-700 shadow-sm' : 'text-slate-500 hover:text-slate-700']"
        @click="handleTabChange(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="flex items-center gap-3">
      <input
        v-model="keyword"
        type="text"
        placeholder="搜索..."
        class="w-64 rounded-xl border border-slate-200/60 bg-white/70 px-4 py-2 text-sm backdrop-blur-xl focus:outline-none focus:ring-2 focus:ring-purple-400/50"
        @keyup.enter="handleSearch"
      />
      <button class="rounded-xl border border-slate-200/60 bg-white/70 px-4 py-2 text-sm font-medium text-slate-600 backdrop-blur-xl transition hover:bg-white/90" @click="handleSearch">搜索</button>
    </div>

    <div class="rounded-2xl border border-slate-200/60 bg-white/70 shadow-sm backdrop-blur-xl">
      <div v-if="isLoading" class="flex items-center justify-center py-20">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>

      <div v-else-if="activeTab === 'user'">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200/60 text-left text-slate-500">
              <th class="w-10 px-4 py-3" />
              <th class="px-4 py-3 font-medium">用户</th>
              <th class="px-4 py-3 font-medium">Key</th>
              <th class="px-4 py-3 font-medium">资源</th>
              <th class="px-4 py-3 font-medium">预算</th>
              <th class="px-4 py-3 font-medium">状态</th>
              <th class="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="item in userItems" :key="item.user.id">
              <tr class="border-b border-slate-100/60 hover:bg-white/50">
                <td class="px-4 py-3">
                  <button v-if="item.scene_keys.length" class="text-slate-400 transition hover:text-slate-600" @click="toggleExpand(String(item.user.id))">
                    <svg :class="['h-3.5 w-3.5 transition-transform', expandedRows.has(String(item.user.id)) ? 'rotate-90' : '']" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" /></svg>
                  </button>
                </td>
                <td class="px-4 py-3">
                  <div class="font-medium text-slate-800">{{ item.user.display_name || item.user.username }}</div>
                  <div class="text-xs text-slate-400">{{ item.user.department_name || '-' }}</div>
                </td>
                <td class="px-4 py-3">
                  <div v-if="item.main_key?.litellm_key_id" class="flex items-center gap-1">
                    <code class="text-xs text-slate-600">{{ revealedKeys.has(item.main_key.id) ? item.main_key.litellm_key_id : maskKey(item.main_key.litellm_key_id) }}</code>
                    <button class="text-slate-400 hover:text-slate-600" @click="toggleReveal(item.main_key!.id)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path v-if="!revealedKeys.has(item.main_key!.id)" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /><path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M3 3l18 18" /></svg></button>
                    <button class="text-slate-400 hover:text-slate-600" @click="copyToClipboard(item.main_key!.litellm_key_id!)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                  </div>
                  <span v-else class="text-xs text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <div v-if="item.main_key" class="flex flex-wrap gap-1.5 text-xs">
                    <span v-if="item.main_key.models.length" class="rounded-full bg-purple-50 px-2 py-0.5 text-purple-600">模型 {{ item.main_key.models.length }}</span>
                    <span v-if="item.main_key.mcps.length" class="rounded-full bg-blue-50 px-2 py-0.5 text-blue-600">MCP {{ item.main_key.mcps.length }}</span>
                    <span v-if="item.main_key.skills.length" class="rounded-full bg-pink-50 px-2 py-0.5 text-pink-600">Skill {{ item.main_key.skills.length }}</span>
                    <span v-if="item.main_key.agents.length" class="rounded-full bg-orange-50 px-2 py-0.5 text-orange-600">智能体 {{ item.main_key.agents.length }}</span>
                    <span v-if="!item.main_key.models.length && !item.main_key.mcps.length && !item.main_key.skills.length && !item.main_key.agents.length" class="text-slate-400">无资源</span>
                  </div>
                  <span v-else class="text-xs text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <BudgetCell :key-data="item.main_key" />
                </td>
                <td class="px-4 py-3">
                  <button v-if="item.main_key" :class="['rounded-full px-3 py-1 text-xs font-medium transition', item.main_key.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500']" @click="handleToggle(item.main_key!)">
                    {{ item.main_key.is_active ? '已启用' : '已禁用' }}
                  </button>
                  <span v-else class="text-xs text-slate-400">未创建</span>
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <button v-if="item.main_key" class="text-xs text-purple-600 hover:text-purple-800" @click="handleEdit(item.main_key!)">编辑</button>
                    <button class="text-xs text-purple-600 hover:text-purple-800" @click="handleCreateForUser(item.user.id, item.main_key)">+场景Key</button>
                  </div>
                </td>
              </tr>
              <tr v-for="sk in expandedRows.has(String(item.user.id)) ? item.scene_keys : []" :key="sk.id" class="border-b border-slate-50 bg-slate-50/30">
                <td class="px-4 py-2" />
                <td class="px-4 py-2 pl-10">
                  <span class="text-xs text-slate-500">┗</span>
                  <span class="ml-1 text-slate-700">{{ sk.name }}</span>
                </td>
                <td class="px-4 py-2">
                  <div v-if="sk.litellm_key_id" class="flex items-center gap-1">
                    <code class="text-xs text-slate-600">{{ revealedKeys.has(sk.id) ? sk.litellm_key_id : maskKey(sk.litellm_key_id) }}</code>
                    <button class="text-slate-400 hover:text-slate-600" @click="toggleReveal(sk.id)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path v-if="!revealedKeys.has(sk.id)" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /><path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M3 3l18 18" /></svg></button>
                    <button class="text-slate-400 hover:text-slate-600" @click="copyToClipboard(sk.litellm_key_id!)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                  </div>
                  <span v-else class="text-xs text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <div class="flex flex-wrap gap-1.5 text-xs">
                    <span v-if="sk.models.length" class="rounded-full bg-purple-50 px-2 py-0.5 text-purple-600">模型 {{ sk.models.length }}</span>
                    <span v-if="sk.mcps.length" class="rounded-full bg-blue-50 px-2 py-0.5 text-blue-600">MCP {{ sk.mcps.length }}</span>
                    <span v-if="sk.skills.length" class="rounded-full bg-pink-50 px-2 py-0.5 text-pink-600">Skill {{ sk.skills.length }}</span>
                    <span v-if="sk.agents.length" class="rounded-full bg-orange-50 px-2 py-0.5 text-orange-600">智能体 {{ sk.agents.length }}</span>
                    <span v-if="!sk.models.length && !sk.mcps.length && !sk.skills.length && !sk.agents.length" class="text-slate-400">无资源</span>
                  </div>
                </td>
                <td class="px-4 py-2">
                  <BudgetCell :key-data="sk" />
                </td>
                <td class="px-4 py-2">
                  <button :class="['rounded-full px-3 py-1 text-xs font-medium transition', sk.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500']" @click="handleToggle(sk)">
                    {{ sk.is_active ? '已启用' : '已禁用' }}
                  </button>
                </td>
                <td class="px-4 py-2">
                  <div class="flex items-center gap-2">
                    <button class="text-xs text-purple-600 hover:text-purple-800" @click="handleEdit(sk)">编辑</button>
                    <button class="text-xs text-red-500 hover:text-red-700" @click="deleteTarget = sk">删除</button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <div v-if="!userItems.length" class="py-16 text-center text-sm text-slate-400">暂无数据</div>
      </div>

      <div v-else-if="activeTab === 'department'">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200/60 text-left text-slate-500">
              <th class="w-10 px-4 py-3" />
              <th class="px-4 py-3 font-medium">部门</th>
              <th class="px-4 py-3 font-medium">Key 值</th>
              <th class="px-4 py-3 font-medium">模型</th>
              <th class="px-4 py-3 font-medium">MCP</th>
              <th class="px-4 py-3 font-medium">Skill</th>
              <th class="px-4 py-3 font-medium">智能体</th>
              <th class="px-4 py-3 font-medium">预算</th>
              <th class="px-4 py-3 font-medium">状态</th>
              <th class="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="item in deptItems" :key="item.department.id">
              <tr class="border-b border-slate-100/60 hover:bg-white/50">
                <td class="px-4 py-3">
                  <button v-if="item.scene_keys.length" class="text-slate-400 transition hover:text-slate-600" @click="toggleExpand('dept-' + item.department.id)">
                    <svg :class="['h-3.5 w-3.5 transition-transform', expandedRows.has('dept-' + item.department.id) ? 'rotate-90' : '']" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" /></svg>
                  </button>
                </td>
                <td class="px-4 py-3">
                  <div class="font-medium text-slate-800">{{ item.department.name }}</div>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key">
                    <div v-if="item.main_key.litellm_key_id" class="flex items-center gap-1">
                      <code class="text-xs text-slate-600">{{ revealedKeys.has(item.main_key.id) ? item.main_key.litellm_key_id : maskKey(item.main_key.litellm_key_id) }}</code>
                      <button class="text-slate-400 hover:text-slate-600" @click="toggleReveal(item.main_key!.id)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path v-if="!revealedKeys.has(item.main_key!.id)" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /><path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M3 3l18 18" /></svg></button>
                      <button class="text-slate-400 hover:text-slate-600" @click="copyToClipboard(item.main_key!.litellm_key_id!)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                    </div>
                    <span v-else class="text-xs text-slate-400">-</span>
                  </template>
                  <span v-else class="text-xs text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key && item.main_key.models.length">
                    <span v-for="mid in item.main_key.models.slice(0, 3)" :key="mid" class="mr-1 rounded-full bg-purple-50 px-2 py-0.5 text-xs text-purple-600">{{ getModelName(mid) }}</span>
                    <span v-if="item.main_key.models.length > 3" class="text-xs text-slate-400">+{{ item.main_key.models.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key && item.main_key.mcps.length">
                    <span v-for="mid in item.main_key.mcps.slice(0, 3)" :key="mid" class="mr-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">{{ getMcpName(mid) }}</span>
                    <span v-if="item.main_key.mcps.length > 3" class="text-xs text-slate-400">+{{ item.main_key.mcps.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key && item.main_key.skills.length">
                    <span v-for="sid in item.main_key.skills.slice(0, 3)" :key="sid" class="mr-1 rounded-full bg-pink-50 px-2 py-0.5 text-xs text-pink-600">{{ getSkillName(sid) }}</span>
                    <span v-if="item.main_key.skills.length > 3" class="text-xs text-slate-400">+{{ item.main_key.skills.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key && item.main_key.agents.length">
                    <span v-for="aid in item.main_key.agents.slice(0, 3)" :key="aid" class="mr-1 rounded-full bg-orange-50 px-2 py-0.5 text-xs text-orange-600">{{ getAgentName(aid) }}</span>
                    <span v-if="item.main_key.agents.length > 3" class="text-xs text-slate-400">+{{ item.main_key.agents.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <button v-if="item.main_key" :class="['rounded-full px-3 py-1 text-xs font-medium transition', item.main_key.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500']" @click="handleToggle(item.main_key!)">{{ item.main_key.is_active ? '已启用' : '已禁用' }}</button>
                  <span v-else class="text-xs text-slate-400">未创建</span>
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <button v-if="item.main_key" class="text-xs text-purple-600 hover:text-purple-800" @click="handleEdit(item.main_key!)">编辑</button>
                    <button class="text-xs text-purple-600 hover:text-purple-800" @click="handleCreateForOwner('department', item.department.id, item.main_key)">+场景Key</button>
                  </div>
                </td>
              </tr>
              <tr v-for="sk in expandedRows.has('dept-' + item.department.id) ? item.scene_keys : []" :key="sk.id" class="border-b border-slate-50 bg-slate-50/30">
                <td class="px-4 py-2" />
                <td class="px-4 py-2 pl-10">
                  <span class="text-xs text-slate-500">┗</span>
                  <span class="ml-1 text-slate-700">{{ sk.name }}</span>
                </td>
                <td class="px-4 py-2">
                  <div v-if="sk.litellm_key_id" class="flex items-center gap-1">
                    <code class="text-xs text-slate-600">{{ revealedKeys.has(sk.id) ? sk.litellm_key_id : maskKey(sk.litellm_key_id) }}</code>
                    <button class="text-slate-400 hover:text-slate-600" @click="toggleReveal(sk.id)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path v-if="!revealedKeys.has(sk.id)" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /><path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M3 3l18 18" /></svg></button>
                    <button class="text-slate-400 hover:text-slate-600" @click="copyToClipboard(sk.litellm_key_id!)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                  </div>
                  <span v-else class="text-xs text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <template v-if="sk.models.length">
                    <span v-for="mid in sk.models.slice(0, 3)" :key="mid" class="mr-1 rounded-full bg-purple-50 px-2 py-0.5 text-xs text-purple-600">{{ getModelName(mid) }}</span>
                    <span v-if="sk.models.length > 3" class="text-xs text-slate-400">+{{ sk.models.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <template v-if="sk.mcps.length">
                    <span v-for="mid in sk.mcps.slice(0, 3)" :key="mid" class="mr-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">{{ getMcpName(mid) }}</span>
                    <span v-if="sk.mcps.length > 3" class="text-xs text-slate-400">+{{ sk.mcps.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <template v-if="sk.skills.length">
                    <span v-for="sid in sk.skills.slice(0, 3)" :key="sid" class="mr-1 rounded-full bg-pink-50 px-2 py-0.5 text-xs text-pink-600">{{ getSkillName(sid) }}</span>
                    <span v-if="sk.skills.length > 3" class="text-xs text-slate-400">+{{ sk.skills.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <template v-if="sk.agents.length">
                    <span v-for="aid in sk.agents.slice(0, 3)" :key="aid" class="mr-1 rounded-full bg-orange-50 px-2 py-0.5 text-xs text-orange-600">{{ getAgentName(aid) }}</span>
                    <span v-if="sk.agents.length > 3" class="text-xs text-slate-400">+{{ sk.agents.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <button :class="['rounded-full px-3 py-1 text-xs font-medium transition', sk.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500']" @click="handleToggle(sk)">{{ sk.is_active ? '已启用' : '已禁用' }}</button>
                </td>
                <td class="px-4 py-2">
                  <div class="flex items-center gap-2">
                    <button class="text-xs text-purple-600 hover:text-purple-800" @click="handleEdit(sk)">编辑</button>
                    <button class="text-xs text-red-500 hover:text-red-700" @click="deleteTarget = sk">删除</button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <div v-if="!deptItems.length" class="py-16 text-center text-sm text-slate-400">暂无数据</div>
      </div>

      <div v-else-if="activeTab === 'project'">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200/60 text-left text-slate-500">
              <th class="w-10 px-4 py-3" />
              <th class="px-4 py-3 font-medium">项目</th>
              <th class="px-4 py-3 font-medium">Key 值</th>
              <th class="px-4 py-3 font-medium">模型</th>
              <th class="px-4 py-3 font-medium">MCP</th>
              <th class="px-4 py-3 font-medium">Skill</th>
              <th class="px-4 py-3 font-medium">智能体</th>
              <th class="px-4 py-3 font-medium">预算</th>
              <th class="px-4 py-3 font-medium">状态</th>
              <th class="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="item in projectItems" :key="item.project.id">
              <tr class="border-b border-slate-100/60 hover:bg-white/50">
                <td class="px-4 py-3">
                  <button v-if="item.scene_keys.length" class="text-slate-400 transition hover:text-slate-600" @click="toggleExpand('proj-' + item.project.id)">
                    <svg :class="['h-3.5 w-3.5 transition-transform', expandedRows.has('proj-' + item.project.id) ? 'rotate-90' : '']" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" /></svg>
                  </button>
                </td>
                <td class="px-4 py-3">
                  <div class="font-medium text-slate-800">{{ item.project.name }}</div>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key">
                    <div v-if="item.main_key.litellm_key_id" class="flex items-center gap-1">
                      <code class="text-xs text-slate-600">{{ revealedKeys.has(item.main_key.id) ? item.main_key.litellm_key_id : maskKey(item.main_key.litellm_key_id) }}</code>
                      <button class="text-slate-400 hover:text-slate-600" @click="toggleReveal(item.main_key!.id)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path v-if="!revealedKeys.has(item.main_key!.id)" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /><path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M3 3l18 18" /></svg></button>
                      <button class="text-slate-400 hover:text-slate-600" @click="copyToClipboard(item.main_key!.litellm_key_id!)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                    </div>
                    <span v-else class="text-xs text-slate-400">-</span>
                  </template>
                  <span v-else class="text-xs text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key && item.main_key.models.length">
                    <span v-for="mid in item.main_key.models.slice(0, 3)" :key="mid" class="mr-1 rounded-full bg-purple-50 px-2 py-0.5 text-xs text-purple-600">{{ getModelName(mid) }}</span>
                    <span v-if="item.main_key.models.length > 3" class="text-xs text-slate-400">+{{ item.main_key.models.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key && item.main_key.mcps.length">
                    <span v-for="mid in item.main_key.mcps.slice(0, 3)" :key="mid" class="mr-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">{{ getMcpName(mid) }}</span>
                    <span v-if="item.main_key.mcps.length > 3" class="text-xs text-slate-400">+{{ item.main_key.mcps.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key && item.main_key.skills.length">
                    <span v-for="sid in item.main_key.skills.slice(0, 3)" :key="sid" class="mr-1 rounded-full bg-pink-50 px-2 py-0.5 text-xs text-pink-600">{{ getSkillName(sid) }}</span>
                    <span v-if="item.main_key.skills.length > 3" class="text-xs text-slate-400">+{{ item.main_key.skills.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <template v-if="item.main_key && item.main_key.agents.length">
                    <span v-for="aid in item.main_key.agents.slice(0, 3)" :key="aid" class="mr-1 rounded-full bg-orange-50 px-2 py-0.5 text-xs text-orange-600">{{ getAgentName(aid) }}</span>
                    <span v-if="item.main_key.agents.length > 3" class="text-xs text-slate-400">+{{ item.main_key.agents.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-3">
                  <button v-if="item.main_key" :class="['rounded-full px-3 py-1 text-xs font-medium transition', item.main_key.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500']" @click="handleToggle(item.main_key!)">{{ item.main_key.is_active ? '已启用' : '已禁用' }}</button>
                  <span v-else class="text-xs text-slate-400">未创建</span>
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <button v-if="item.main_key" class="text-xs text-purple-600 hover:text-purple-800" @click="handleEdit(item.main_key!)">编辑</button>
                    <button class="text-xs text-purple-600 hover:text-purple-800" @click="handleCreateForOwner('project', item.project.id, item.main_key)">+场景Key</button>
                  </div>
                </td>
              </tr>
              <tr v-for="sk in expandedRows.has('proj-' + item.project.id) ? item.scene_keys : []" :key="sk.id" class="border-b border-slate-50 bg-slate-50/30">
                <td class="px-4 py-2" />
                <td class="px-4 py-2 pl-10">
                  <span class="text-xs text-slate-500">┗</span>
                  <span class="ml-1 text-slate-700">{{ sk.name }}</span>
                </td>
                <td class="px-4 py-2">
                  <div v-if="sk.litellm_key_id" class="flex items-center gap-1">
                    <code class="text-xs text-slate-600">{{ revealedKeys.has(sk.id) ? sk.litellm_key_id : maskKey(sk.litellm_key_id) }}</code>
                    <button class="text-slate-400 hover:text-slate-600" @click="toggleReveal(sk.id)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path v-if="!revealedKeys.has(sk.id)" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /><path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M3 3l18 18" /></svg></button>
                    <button class="text-slate-400 hover:text-slate-600" @click="copyToClipboard(sk.litellm_key_id!)"><svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                  </div>
                  <span v-else class="text-xs text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <template v-if="sk.models.length">
                    <span v-for="mid in sk.models.slice(0, 3)" :key="mid" class="mr-1 rounded-full bg-purple-50 px-2 py-0.5 text-xs text-purple-600">{{ getModelName(mid) }}</span>
                    <span v-if="sk.models.length > 3" class="text-xs text-slate-400">+{{ sk.models.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <template v-if="sk.mcps.length">
                    <span v-for="mid in sk.mcps.slice(0, 3)" :key="mid" class="mr-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">{{ getMcpName(mid) }}</span>
                    <span v-if="sk.mcps.length > 3" class="text-xs text-slate-400">+{{ sk.mcps.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <template v-if="sk.skills.length">
                    <span v-for="sid in sk.skills.slice(0, 3)" :key="sid" class="mr-1 rounded-full bg-pink-50 px-2 py-0.5 text-xs text-pink-600">{{ getSkillName(sid) }}</span>
                    <span v-if="sk.skills.length > 3" class="text-xs text-slate-400">+{{ sk.skills.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <template v-if="sk.agents.length">
                    <span v-for="aid in sk.agents.slice(0, 3)" :key="aid" class="mr-1 rounded-full bg-orange-50 px-2 py-0.5 text-xs text-orange-600">{{ getAgentName(aid) }}</span>
                    <span v-if="sk.agents.length > 3" class="text-xs text-slate-400">+{{ sk.agents.length - 3 }}</span>
                  </template>
                  <span v-else class="text-slate-400">-</span>
                </td>
                <td class="px-4 py-2">
                  <button :class="['rounded-full px-3 py-1 text-xs font-medium transition', sk.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500']" @click="handleToggle(sk)">{{ sk.is_active ? '已启用' : '已禁用' }}</button>
                </td>
                <td class="px-4 py-2">
                  <div class="flex items-center gap-2">
                    <button class="text-xs text-purple-600 hover:text-purple-800" @click="handleEdit(sk)">编辑</button>
                    <button class="text-xs text-red-500 hover:text-red-700" @click="deleteTarget = sk">删除</button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <div v-if="!projectItems.length" class="py-16 text-center text-sm text-slate-400">暂无数据</div>
      </div>
    </div>

    <div v-if="total > pageSize" class="flex items-center justify-between">
      <span class="text-sm text-slate-500">共 {{ total }} 条</span>
      <div class="flex gap-1">
        <button :disabled="page <= 1" class="rounded-lg border border-slate-200/60 bg-white/70 px-3 py-1.5 text-sm disabled:opacity-40" @click="page--; fetchData()">上一页</button>
        <button :disabled="page * pageSize >= total" class="rounded-lg border border-slate-200/60 bg-white/70 px-3 py-1.5 text-sm disabled:opacity-40" @click="page++; fetchData()">下一页</button>
      </div>
    </div>

    <KeyFormDialog
      :visible="showKeyForm"
      :edit-key="editingKey"
      :template-key="templateKey"
      :default-owner-type="defaultOwnerType"
      :default-owner-id="defaultOwnerId"
      @close="showKeyForm = false"
      @saved="showKeyForm = false; fetchData()"
    />

    <ConfirmDialog
      :visible="!!deleteTarget"
      title="确认删除"
      :message="`确定要删除 Key「${deleteTarget?.name || ''}」吗？此操作不可恢复。`"
      confirm-text="删除"
      @confirm="handleConfirmDelete"
      @cancel="deleteTarget = null"
    />

    <div v-if="showScenarioDialog" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showScenarioDialog = false" />
      <div class="relative w-[600px] max-h-[80vh] overflow-y-auto bg-white/90 backdrop-blur-xl border border-slate-200/60 rounded-2xl shadow-xl p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-slate-800">使用场景管理</h3>
          <button class="text-slate-400 hover:text-slate-600" @click="showScenarioDialog = false">
            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" /></svg>
          </button>
        </div>
        <ScenarioTab />
      </div>
    </div>

    <BatchResourceDialog
      :visible="showBatchResource"
      @close="showBatchResource = false"
      @saved="showBatchResource = false; fetchData()"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getIdentityList,
  toggleAiKey,
  deleteAiKey,
  getActiveModels,
  getMcpServers,
  getSkills,
  getAgents,
  usePermission,
  toast,
  type AiKey,
  type ActiveModel,
  type McpServer,
  type Skill,
  type Agent,
  type IdentityUserItem,
  type IdentityDepartmentItem,
  type IdentityProjectItem,
} from '@aihelms/shared'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import KeyFormDialog from './KeyFormDialog.vue'
import ScenarioTab from './ScenarioTab.vue'
import BudgetCell from './BudgetCell.vue'
import BatchResourceDialog from './BatchResourceDialog.vue'

const { hasPermission } = usePermission()
const router = useRouter()

type TabType = 'user' | 'department' | 'project'

const tabs = [
  { value: 'user' as TabType, label: '人员' },
  { value: 'department' as TabType, label: '部门' },
  { value: 'project' as TabType, label: '项目' },
]

const activeTab = ref<TabType>('user')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const isLoading = ref(false)

const userItems = ref<IdentityUserItem[]>([])
const deptItems = ref<IdentityDepartmentItem[]>([])
const projectItems = ref<IdentityProjectItem[]>([])
const expandedRows = ref<Set<string>>(new Set())
const revealedKeys = ref<Set<number>>(new Set())
const activeModels = ref<ActiveModel[]>([])
const mcpServers = ref<McpServer[]>([])
const skills = ref<Skill[]>([])
const agents = ref<Agent[]>([])

const showKeyForm = ref(false)
const editingKey = ref<AiKey | null>(null)
const templateKey = ref<AiKey | null>(null)
const deleteTarget = ref<AiKey | null>(null)
const defaultOwnerType = ref<'user' | 'department' | 'project'>('user')
const defaultOwnerId = ref<number | undefined>(undefined)
const showScenarioDialog = ref(false)
const showBatchResource = ref(false)

async function fetchData(): Promise<void> {
  isLoading.value = true
  try {
    if (activeTab.value === 'user') {
      const result = await getIdentityList('user', page.value, pageSize.value, keyword.value || undefined)
      userItems.value = result.items
      total.value = result.total
    } else if (activeTab.value === 'department') {
      const result = await getIdentityList('department', page.value, pageSize.value, keyword.value || undefined)
      deptItems.value = result.items
      total.value = result.total
    } else if (activeTab.value === 'project') {
      const result = await getIdentityList('project', page.value, pageSize.value, keyword.value || undefined)
      projectItems.value = result.items
      total.value = result.total
    }
  } finally {
    isLoading.value = false
  }
}

async function fetchModels(): Promise<void> {
  activeModels.value = await getActiveModels()
}

async function fetchMcps(): Promise<void> {
  const res = await getMcpServers(1, 200)
  mcpServers.value = res.items
}

async function fetchSkills(): Promise<void> {
  const res = await getSkills(1, 200)
  skills.value = res.items
}

async function fetchAgents(): Promise<void> {
  const res = await getAgents(1, 200)
  agents.value = res.items
}

function getMcpName(mcpId: number): string {
  const found = mcpServers.value.find((m) => m.id === mcpId)
  return found ? found.name : `#${mcpId}`
}

function getSkillName(skillId: number): string {
  const found = skills.value.find((s) => s.id === skillId)
  return found ? found.name : `#${skillId}`
}

function getAgentName(agentId: number): string {
  const found = agents.value.find((a) => a.id === agentId)
  return found ? found.name : `#${agentId}`
}

function handleTabChange(tab: TabType): void {
  activeTab.value = tab
  page.value = 1
  keyword.value = ''
  expandedRows.value.clear()
  fetchData()
}

function handleSearch(): void {
  page.value = 1
  fetchData()
}

function handleCreateNew(): void {
  editingKey.value = null
  templateKey.value = null
  defaultOwnerType.value = activeTab.value
  defaultOwnerId.value = undefined
  showKeyForm.value = true
}

function handleCreateForUser(userId: number, mainKey: AiKey | null = null): void {
  editingKey.value = null
  templateKey.value = mainKey
  defaultOwnerType.value = 'user'
  defaultOwnerId.value = userId
  showKeyForm.value = true
}

function handleCreateForOwner(type: 'department' | 'project', id: number, mainKey: AiKey | null = null): void {
  editingKey.value = null
  templateKey.value = mainKey
  defaultOwnerType.value = type
  defaultOwnerId.value = id
  showKeyForm.value = true
}

function handleEdit(key: AiKey): void {
  router.push(`/ai-keys/${key.id}`)
}

async function handleToggle(key: AiKey): Promise<void> {
  await toggleAiKey(key.id)
  fetchData()
}

async function handleConfirmDelete(): Promise<void> {
  if (!deleteTarget.value) return
  await deleteAiKey(deleteTarget.value.id)
  deleteTarget.value = null
  fetchData()
}

function getModelName(modelId: string): string {
  const found = activeModels.value.find((m) => m.model_id === modelId)
  return found ? found.name : modelId
}

function toggleExpand(rowKey: string): void {
  if (expandedRows.value.has(rowKey)) {
    expandedRows.value.delete(rowKey)
  } else {
    expandedRows.value.add(rowKey)
  }
}

function maskKey(key: string): string {
  if (key.length <= 11) return key
  return key.slice(0, 7) + '****' + key.slice(-4)
}

function toggleReveal(keyId: number): void {
  if (revealedKeys.value.has(keyId)) {
    revealedKeys.value.delete(keyId)
  } else {
    revealedKeys.value.add(keyId)
  }
}

async function copyToClipboard(text: string): Promise<void> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    toast.success('已复制到剪贴板')
  } catch {
    toast.error('复制失败，请手动复制')
  }
}

onMounted(() => {
  fetchData()
  fetchModels()
  fetchMcps()
  fetchSkills()
  fetchAgents()
})
</script>
