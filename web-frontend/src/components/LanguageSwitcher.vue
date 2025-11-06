<template>
  <div class="language-switcher">
    <button
      @click="toggleLanguage"
      class="lang-btn"
      :title="currentLocale === 'zh-CN' ? '切换到英文' : 'Switch to Chinese'"
    >
      <svg
        v-if="currentLocale === 'zh-CN'"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        class="icon"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
        />
      </svg>
      <span class="lang-text">{{ currentLocale === 'zh-CN' ? 'EN' : '中文' }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'

const { locale } = useI18n()
const localeStore = useLocaleStore()

const currentLocale = computed(() => localeStore.currentLocale)

const toggleLanguage = () => {
  const newLocale = currentLocale.value === 'zh-CN' ? 'en-US' : 'zh-CN'
  localeStore.setLocale(newLocale)
  locale.value = newLocale
}
</script>

<style scoped>
.language-switcher {
  display: inline-flex;
  align-items: center;
}

.lang-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.375rem;
  color: rgba(255, 255, 255, 0.9);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
}

.lang-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
}

.icon {
  width: 1rem;
  height: 1rem;
}

.lang-text {
  font-weight: 500;
}
</style>
