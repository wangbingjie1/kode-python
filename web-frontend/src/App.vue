<template>
  <div id="app" class="h-screen">
    <RouterView />
    <NotificationContainer />
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { RouterView } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'
import NotificationContainer from '@/components/NotificationContainer.vue'

// 初始化 i18n 和 locale store
const i18n = useI18n()
const localeStore = useLocaleStore()

// 监听 localeStore 的变化，确保 i18n 全局 locale 保持同步
watch(() => localeStore.currentLocale, (newLocale) => {
  console.log('[App.vue] Locale changed to:', newLocale)
  console.log('[App.vue] Current i18n locale:', i18n.locale.value)
  i18n.locale.value = newLocale
  console.log('[App.vue] Updated i18n locale to:', i18n.locale.value)
}, { immediate: true })
</script>

<style scoped>
#app {
  height: 100vh;
  overflow: hidden;
}
</style>
