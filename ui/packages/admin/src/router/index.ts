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
          path: 'organizations',
          name: 'OrgList',
          component: () => import('../views/organizations/OrgList.vue'),
          meta: { permission: 'organization:read' },
        },
        {
          path: 'branches',
          name: 'BranchList',
          component: () => import('../views/organizations/BranchList.vue'),
          meta: { permission: 'organization:read' },
        },
        {
          path: 'roles',
          name: 'RoleList',
          component: () => import('../views/roles/RoleList.vue'),
          meta: { permission: 'role:read' },
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
