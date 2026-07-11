import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../views/ChatView.vue'),
    },
    {
      path: '/medicine',
      name: 'medicine',
      component: () => import('../views/MedicineView.vue'),
    },
    {
      path: '/multimodal',
      name: 'multimodal',
      component: () => import('../views/MultimodalView.vue'),
    },
    {
      path: '/knowledge',
      name: 'knowledge',
      component: () => import('../views/KnowledgeView.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/HistoryView.vue'),
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      props: {
        initialMode: 'login',
      },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/LoginView.vue'),
      props: {
        initialMode: 'register',
      },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/AdminView.vue'),
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: () => import('../views/AnalyticsView.vue'),
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue'),
    },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.requiresAuth) {
    return true
  }

  const hasUser = Boolean(localStorage.getItem('ragUser') && localStorage.getItem('ragToken'))

  if (hasUser) {
    return true
  }

  return {
    path: '/login',
    query: {
      redirect: to.fullPath,
    },
  }
})

export default router
