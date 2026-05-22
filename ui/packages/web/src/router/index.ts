import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('../layouts/WebLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'Identity', component: () => import('../views/MyIdentityView.vue') },
        { path: 'market', name: 'Market', component: () => import('../views/MarketView.vue') },
        { path: 'models', name: 'Models', component: () => import('../views/ModelSquare.vue') },
        { path: 'agents', name: 'Agents', component: () => import('../views/AgentCenter.vue') },
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
    next({ name: 'Identity' })
    return
  }
  next()
})

export default router