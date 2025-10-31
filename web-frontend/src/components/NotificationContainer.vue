<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="notif in notifications"
          :key="notif.id"
          class="max-w-sm bg-white rounded-lg shadow-lg border overflow-hidden pointer-events-auto"
          :class="getBorderClass(notif.type)"
        >
          <div class="p-4 flex items-start gap-3">
            <div class="flex-shrink-0 text-xl">
              {{ getIcon(notif.type) }}
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-gray-900">{{ notif.title }}</p>
              <p v-if="notif.message" class="mt-1 text-sm text-gray-600">{{ notif.message }}</p>
            </div>
            <button
              @click="remove(notif.id)"
              class="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { notification } from '@/composables/useNotification'

const { notifications, remove } = notification

function getIcon(type: string): string {
  const icons: Record<string, string> = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  }
  return icons[type] || 'ℹ'
}

function getBorderClass(type: string): string {
  const classes: Record<string, string> = {
    success: 'border-l-4 border-green-500',
    error: 'border-l-4 border-red-500',
    warning: 'border-l-4 border-yellow-500',
    info: 'border-l-4 border-blue-500'
  }
  return classes[type] || 'border-l-4 border-blue-500'
}
</script>

<style scoped>
.toast-enter-active {
  transition: all 0.3s ease;
}

.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.toast-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>
