import { createRouter, createWebHistory } from 'vue-router'

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
          component: () => import('../views/Dashboard.vue'),
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
      ],
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('aihelms_token')
  if (to.meta.requiresAuth !== false && !token) {
    next({ name: 'Login' })
    return
  }
  if (to.name === 'Login' && token) {
    next({ name: 'Dashboard' })
    return
  }
  next()
})

export default router
