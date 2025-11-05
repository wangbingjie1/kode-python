<template>
  <nav class="navigation-bar">
    <div class="nav-inner">
      <router-link to="/chat" class="nav-brand" aria-label="返回主页">
        <span class="brand-logo">Kode AI</span>
      </router-link>
      <div class="nav-links">
        <router-link to="/chat" class="nav-link">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V7a2 2 0 012-2h14a2 2 0 012 2v7a2 2 0 01-2 2h-5l-5 5v-4z" />
          </svg>
          <span>对话</span>
        </router-link>
        <router-link to="/database" class="nav-link">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
          <span>数据库</span>
        </router-link>
      </div>

      <!-- 用户菜单 -->
      <div class="user-menu">
        <div v-if="authStore.currentUser" class="user-info" @click="toggleMenu">
          <div class="user-avatar">
            {{ authStore.currentUser.username.charAt(0).toUpperCase() }}
          </div>
          <span class="user-name">{{ authStore.currentUser.username }}</span>
          <svg class="dropdown-icon" :class="{ 'is-open': isMenuOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>

        <div v-if="isMenuOpen" class="dropdown-menu" @click="isMenuOpen = false">
          <div class="menu-item user-detail">
            <div class="user-email">{{ authStore.currentUser?.email }}</div>
          </div>
          <div class="menu-divider"></div>
          <button class="menu-item logout-btn" @click="handleLogout">
            <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            退出登录
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { notification } from '@/composables/useNotification'

const router = useRouter()
const authStore = useAuthStore()
const isMenuOpen = ref(false)

function toggleMenu() {
  isMenuOpen.value = !isMenuOpen.value
}

async function handleLogout() {
  authStore.logout()
  notification.success('已退出登录', '期待您的再次光临')
  router.push('/login')
}

// 点击外部关闭菜单
if (typeof document !== 'undefined') {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    if (!target.closest('.user-menu')) {
      isMenuOpen.value = false
    }
  })
}
</script>

<style scoped>
.navigation-bar {
  width: 100%;
  padding: 0.75rem 2.5rem;
  background: #ffffff;
  border-bottom: 1px solid #eadfd3;
  box-shadow: 0 8px 24px rgba(198, 173, 144, 0.08);
}

.nav-inner {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.nav-brand {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
}

.brand-logo {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2b6cb0;
  letter-spacing: 0.02em;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.8rem;
  border-radius: 9999px;
  font-size: 0.9rem;
  color: #736659;
  text-decoration: none;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.nav-link:hover {
  background: rgba(244, 229, 213, 0.6);
  color: #2f2720;
}

.nav-link.router-link-active {
  background: rgba(236, 211, 184, 0.8);
  color: #2f2720;
  font-weight: 600;
}

.nav-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: #c58d63;
}

/* 用户菜单 */
.user-menu {
  margin-left: auto;
  position: relative;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  border-radius: 9999px;
  cursor: pointer;
  transition: background-color 0.2s;
  user-select: none;
}

.user-info:hover {
  background: rgba(244, 229, 213, 0.6);
}

.user-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: #2f2720;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-icon {
  width: 1rem;
  height: 1rem;
  color: #736659;
  transition: transform 0.2s;
}

.dropdown-icon.is-open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  min-width: 220px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
  border: 1px solid #eadfd3;
  overflow: hidden;
  z-index: 1000;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.menu-item {
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  border: none;
  background: none;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 0.875rem;
  color: #2f2720;
  text-align: left;
}

.menu-item:hover {
  background: rgba(244, 229, 213, 0.4);
}

.user-detail {
  cursor: default;
  padding: 1rem;
}

.user-detail:hover {
  background: none;
}

.user-email {
  font-size: 0.813rem;
  color: #736659;
  word-break: break-all;
}

.menu-divider {
  height: 1px;
  background: #eadfd3;
}

.logout-btn {
  color: #dc2626;
  font-weight: 500;
}

.logout-btn:hover {
  background: rgba(220, 38, 38, 0.1);
}

.menu-icon {
  width: 1.125rem;
  height: 1.125rem;
}

@media (max-width: 768px) {
  .navigation-bar {
    padding: 0.75rem 1.25rem;
  }

  .nav-inner {
    gap: 1.25rem;
  }

  .nav-links {
    gap: 0.75rem;
  }

  .user-name {
    display: none;
  }

  .dropdown-icon {
    display: none;
  }

  .dropdown-menu {
    right: -0.5rem;
  }
}
</style>
