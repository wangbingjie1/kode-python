import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Locale } from '@/i18n'

export const useLocaleStore = defineStore('locale', () => {
  const currentLocale = ref<Locale>(
    (localStorage.getItem('locale') as Locale) || 'zh-CN'
  )

  const setLocale = (locale: Locale) => {
    currentLocale.value = locale
    localStorage.setItem('locale', locale)

    // 更新 document.documentElement.lang
    document.documentElement.lang = locale

    // 通知后端
    try {
      // 在 API 请求时会自动带上 Accept-Language header
      localStorage.setItem('locale', locale)
    } catch (error) {
      console.error('Failed to persist locale:', error)
    }
  }

  const toggleLocale = () => {
    const newLocale: Locale = currentLocale.value === 'zh-CN' ? 'en-US' : 'zh-CN'
    setLocale(newLocale)
  }

  return {
    currentLocale,
    setLocale,
    toggleLocale
  }
})
