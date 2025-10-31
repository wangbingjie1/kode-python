/**
 * Notification Composable
 *
 * Provides a reactive notification system for displaying toast messages
 */

import { reactive } from 'vue'

export interface Notification {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
  silent?: boolean  // If true, only show for important messages
}

const notifications = reactive<Notification[]>([])
let notificationId = 0

export function useNotification() {
  function show(notification: Omit<Notification, 'id'>) {
    const id = ++notificationId
    const fullNotification: Notification = {
      id,
      duration: 3000,
      ...notification
    }

    // Don't show silent notifications (only log to console)
    if (fullNotification.silent) {
      console.log(`[${fullNotification.type.toUpperCase()}] ${fullNotification.title}`, fullNotification.message)
      return id
    }

    notifications.push(fullNotification)

    if (fullNotification.duration && fullNotification.duration > 0) {
      setTimeout(() => {
        remove(id)
      }, fullNotification.duration)
    }

    return id
  }

  function success(title: string, message?: string, duration?: number, silent = false) {
    return show({ type: 'success', title, message, duration, silent })
  }

  function error(title: string, message?: string, duration?: number, silent = false) {
    return show({ type: 'error', title, message, duration: duration ?? 5000, silent })
  }

  function warning(title: string, message?: string, duration?: number, silent = false) {
    return show({ type: 'warning', title, message, duration, silent })
  }

  function info(title: string, message?: string, duration?: number, silent = false) {
    return show({ type: 'info', title, message, duration, silent })
  }

  function remove(id: number) {
    const index = notifications.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.splice(index, 1)
    }
  }

  return {
    notifications,
    show,
    success,
    error,
    warning,
    info,
    remove
  }
}

// Global notification instance
export const notification = useNotification()
