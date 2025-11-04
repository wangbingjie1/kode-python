import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '@/views/ChatView.vue'
import DatabaseView from '@/views/DatabaseView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/chat'
    },
    {
      path: '/chat',
      name: 'chat',
      component: ChatView
    },
    {
      path: '/chat/:conversationId',
      name: 'chat-conversation',
      component: ChatView
    },
    {
      path: '/database',
      name: 'database',
      component: DatabaseView
    }
  ]
})

export default router
