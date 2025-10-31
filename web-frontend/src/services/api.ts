/**
 * HTTP API Service
 *
 * Provides REST API calls to the backend
 */

import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
  (config) => {
    // TODO: Add auth token if available
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Types
export interface Conversation {
  id: string
  title: string
  project_id: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  metadata: Record<string, any>
  created_at: string
}

export interface CreateConversationRequest {
  title?: string
  project_id: string
}

// API Functions

/**
 * Create a new conversation
 */
export async function createConversation(
  data: CreateConversationRequest
): Promise<Conversation> {
  const response = await apiClient.post<Conversation>('/chat/conversations', data)
  return response.data
}

/**
 * Get conversation by ID
 */
export async function getConversation(conversationId: string): Promise<Conversation> {
  const response = await apiClient.get<Conversation>(`/chat/conversations/${conversationId}`)
  return response.data
}

/**
 * Get conversation messages
 */
export async function getConversationMessages(
  conversationId: string,
  limit = 100
): Promise<Message[]> {
  const response = await apiClient.get<Message[]>(
    `/chat/conversations/${conversationId}/messages`,
    { params: { limit } }
  )
  return response.data
}

/**
 * Delete conversation
 */
export async function deleteConversation(conversationId: string): Promise<void> {
  await apiClient.delete(`/chat/conversations/${conversationId}`)
}

/**
 * List conversations for a project
 */
export async function listProjectConversations(projectId: string): Promise<Conversation[]> {
  const response = await apiClient.get<Conversation[]>(
    `/chat/projects/${projectId}/conversations`
  )
  return response.data
}

/**
 * Get system configuration
 */
export async function getConfig(): Promise<any> {
  const response = await apiClient.get('/config')
  return response.data
}

export default apiClient
