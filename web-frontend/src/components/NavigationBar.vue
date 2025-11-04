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
    </div>
  </nav>
</template>

<script setup lang="ts">
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
}
</style>
