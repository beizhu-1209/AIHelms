import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '@aihelms/shared'

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('../layouts/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('../views/dashboard/DashboardView.vue'),
        },
        {
          path: 'departments',
          name: 'DepartmentManage',
          component: () => import('../views/departments/DepartmentManage.vue'),
          meta: { permission: 'department:read' },
        },
        {
          path: 'projects',
          name: 'ProjectManage',
          component: () => import('../views/projects/ProjectManage.vue'),
          meta: { permission: 'project:read' },
        },
        {
          path: 'users',
          name: 'UserList',
          component: () => import('../views/users/UserList.vue'),
          meta: { permission: 'user:read' },
        },
        {
          path: 'users/create',
          name: 'UserCreate',
          component: () => import('../views/users/UserForm.vue'),
          meta: { permission: 'user:create' },
        },
        {
          path: 'users/:id/edit',
          name: 'UserEdit',
          component: () => import('../views/users/UserForm.vue'),
          meta: { permission: 'user:update' },
        },
        {
          path: 'roles',
          name: 'RoleList',
          component: () => import('../views/roles/RoleList.vue'),
          meta: { permission: 'role:read' },
        },
        {
          path: 'ai-keys',
          name: 'AiKeyManage',
          component: () => import('../views/ai-keys/AiKeyManage.vue'),
          meta: { permission: 'user:read' },
        },
        {
          path: 'ai-keys/:id',
          name: 'AiKeyDetail',
          component: () => import('../views/ai-keys/AiKeyDetail.vue'),
          meta: { permission: 'user:read' },
        },
        {
          path: 'providers',
          name: 'ProviderManage',
          component: () => import('../views/providers/ProviderManage.vue'),
          meta: { permission: 'user:read' },
        },
        {
          path: 'models',
          name: 'ModelManage',
          component: () => import('../views/models/ModelManage.vue'),
          meta: { permission: 'user:read' },
        },
        {
          path: 'mcp',
          name: 'McpManage',
          component: () => import('../views/mcp/McpManage.vue'),
          meta: { permission: 'mcp:read' },
        },
        {
          path: 'skills',
          name: 'SkillList',
          component: () => import('../views/skills/SkillList.vue'),
          meta: { permission: 'skill:read' },
        },
        {
          path: 'skills/:id',
          name: 'SkillDetail',
          component: () => import('../views/skills/SkillDetail.vue'),
          meta: { permission: 'skill:read' },
        },
        {
          path: 'ai-policies',
          name: 'AiPolicies',
          component: () => import('../views/ai-policies/AiPoliciesView.vue'),
          meta: { permission: 'ai_policies:read' },
        },
        {
          path: 'ai-policies/audits/:auditId',
          name: 'AiPoliciesAuditReport',
          component: () => import('../views/ai-policies/AuditReportView.vue'),
          meta: { permission: 'ai_policies:read' },
        },
        {
          path: 'lab/ai-policies',
          name: 'AiPoliciesLab',
          component: () => import('../views/ai-policies/AiPoliciesLabView.vue'),
          meta: { permission: 'ai_policies:read' },
        },
        {
          path: 'agents',
          name: 'AgentList',
          component: () => import('../views/agents/AgentList.vue'),
          meta: { permission: 'agent:read' },
        },
        {
          path: 'agents/:id',
          name: 'AgentDetail',
          component: () => import('../views/agents/AgentDetail.vue'),
          meta: { permission: 'agent:read' },
        },
        {
          path: 'resource-approval',
          name: 'ResourceApprovalManage',
          component: () => import('../views/resource-approval/ResourceApprovalManage.vue'),
          meta: { permission: 'resource_application:read' },
        },
        {
          path: 'audit',
          name: 'AuditLogManage',
          component: () => import('../views/audit/AuditLogManage.vue'),
          meta: { permission: 'audit_log:read' },
        },
        {
          path: 'api-keys',
          name: 'ApiKeyManage',
          component: () => import('../views/api-keys/ApiKeyManage.vue'),
          meta: { permission: 'api_key:read' },
        },
        {
          path: 'logs',
          name: 'LogsManage',
          component: () => import('../views/logs/LogsManage.vue'),
          meta: { permission: 'usage_log:read' },
        },
        {
          path: 'export-tasks',
          name: 'ExportTasksManage',
          component: () => import('../views/audit/ExportTasksManage.vue'),
          meta: { permission: 'usage_log:read' },
        },
        {
          path: 'business-scenarios',
          name: 'BusinessScenarioManage',
          component: () => import('../views/business-scenarios/BusinessScenarioManage.vue'),
          meta: { permission: 'user:read' },
        },
        {
          path: 'system/branding',
          name: 'BrandingView',
          component: () => import('../views/system/BrandingView.vue'),
          meta: { permission: 'user:read' },
        },
        {
          path: 'system/license',
          name: 'LicenseView',
          component: () => import('../views/system/LicenseView.vue'),
          meta: { permission: 'user:read' },
        },
        {
          path: 'ai-health',
          name: 'AIHealth',
          component: () => import('../views/efficiency/HealthView.vue'),
          meta: { permission: 'efficiency:read' },
        },
        {
          path: 'efficiency',
          component: () => import('../views/efficiency/EfficiencyLayout.vue'),
          meta: { permission: 'efficiency:read' },
          children: [
            {
              path: '',
              name: 'EfficiencyOverview',
              component: () => import('../views/efficiency/OverviewView.vue'),
            },
            {
              path: 'adoption',
              name: 'EfficiencyAdoption',
              component: () => import('../views/efficiency/AdoptionView.vue'),
            },
            {
              path: 'cost',
              name: 'EfficiencyCost',
              component: () => import('../views/efficiency/CostView.vue'),
            },
            {
              path: 'budget',
              name: 'EfficiencyBudget',
              component: () => import('../views/efficiency/BudgetView.vue'),
            },
            {
              path: 'health',
              redirect: '/ai-health',
            },
            {
              path: 'reports',
              name: 'EfficiencyReports',
              component: () => import('../views/efficiency/ReportsView.vue'),
            },
          ],
        },
      ],
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem('aihelms_token')
  if (to.meta.requiresAuth !== false && !token) {
    next({ name: 'Login' })
    return
  }
  if (to.name === 'Login' && token) {
    next({ name: 'Dashboard' })
    return
  }
  if (to.meta.requiresAuth !== false && token) {
    const { currentUser, fetchCurrentUser } = useAuth()
    if (!currentUser.value) {
      await fetchCurrentUser()
    }
    if (currentUser.value && !currentUser.value.is_admin) {
      localStorage.removeItem('aihelms_token')
      next({ name: 'Login' })
      return
    }
  }
  next()
})

export default router
