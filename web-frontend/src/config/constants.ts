/**
 * Application Constants
 */

// Default project ID for conversations
// In a real application, this should be fetched from user context or project settings
export const DEFAULT_PROJECT_ID = 'default'

// API Configuration
export const API_BASE_URL = '/api'
export const API_CONFIG = {
  baseURL: '/api',
  timeout: 30000,
}

// SSE Configuration (Server-Sent Events)
export const SSE_CONFIG = {
  reconnectDelay: 3000, // 3 seconds before reconnect
  timeout: 300000, // 5 minutes timeout
}

// UI Configuration
export const UI_CONFIG = {
  messageHistoryLimit: 100,
  notificationDuration: 3000,
  errorNotificationDuration: 5000,
}
