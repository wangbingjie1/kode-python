import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '@/views/ChatView.vue'
import DatabaseView from '@/views/DatabaseView.vue'
import LoginView from '@/views/LoginView.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      name: 'home',
      redirect: '/chat',
      meta: { requiresAuth: true }
    },
    {
      path: '/chat',
      name: 'chat',
      component: ChatView,
      meta: { requiresAuth: true }
    },
    {
      path: '/chat/:conversationId',
      name: 'chat-conversation',
      component: ChatView,
      meta: { requiresAuth: true }
    },
    {
      path: '/database',
      name: 'database',
      component: DatabaseView,
      meta: { requiresAuth: true }
    }
  ]
})

// 路由守卫 - 检查认证状态
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false // 默认需要认证

  if (requiresAuth && !authStore.isAuthenticated) {
    // 未登录,重定向到登录页
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.name === 'login' && authStore.isAuthenticated) {
    // 已登录,访问登录页时重定向到首页
    next({ name: 'home' })
  } else {
    next()
  }
})

export default router
