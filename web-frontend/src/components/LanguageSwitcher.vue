<template>
  <button
    type="button"
    class="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50"
    @click="toggleLanguage"
    :title="currentLocale === 'zh-CN' ? '切换到英文' : 'Switch to Chinese'"
  >
    <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
      />
    </svg>
    <span>{{ currentLocale === 'zh-CN' ? 'EN' : '中文' }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useLocaleStore } from '@/stores/locale'

const localeStore = useLocaleStore()
const currentLocale = computed(() => localeStore.currentLocale)

const toggleLanguage = () => {
  const newLocale = currentLocale.value === 'zh-CN' ? 'en-US' : 'zh-CN'
  console.log('[LanguageSwitcher] Switching from', currentLocale.value, 'to', newLocale)
  localeStore.setLocale(newLocale)
  console.log('[LanguageSwitcher] After setLocale, currentLocale is:', localeStore.currentLocale)
}
</script>
