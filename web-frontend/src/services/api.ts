/**
 * HTTP API Service
 *
 * Provides REST API calls to the backend
 */

import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 180000,  // 3 minutes for long-running operations like schema extraction
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor for adding auth token and language
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Add Accept-Language header
    const locale = localStorage.getItem('locale') || 'zh-CN'
    config.headers['Accept-Language'] = locale

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 如果是401错误且不是刷新token的请求,尝试刷新token
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/auth/refresh') &&
      !originalRequest.url.includes('/auth/login')
    ) {
      originalRequest._retry = true

      try {
        // 动态导入useAuthStore避免循环依赖
        const { useAuthStore } = await import('@/stores/auth')
        const authStore = useAuthStore()

        // 尝试刷新token
        const refreshed = await authStore.refreshAccessToken()

        if (refreshed) {
          // 重新设置Authorization头
          const newToken = localStorage.getItem('access_token')
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          // 重试原请求
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError)
        // 刷新失败,跳转到登录页
        const { useAuthStore } = await import('@/stores/auth')
        const authStore = useAuthStore()
        authStore.logout()

        // 重定向到登录页
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      }
    }

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

// Database Management Types
export interface DatabaseConnection {
  name: string
  db_type: string
  host: string
  port: number
  database: string
  username: string
  schema?: string
  ssl: boolean
}

export interface CreateDatabaseConnectionRequest {
  name: string
  db_type: string
  host: string
  port: number
  database: string
  username: string
  password: string
  db_schema?: string | null
  ssl?: boolean
}

export interface UpdateDatabaseConnectionRequest {
  host?: string
  port?: number
  database?: string
  username?: string
  password?: string
  db_schema?: string | null
  ssl?: boolean
}

export interface DatabaseTestResult {
  status: string
  message: string
  connection?: DatabaseConnection
  error?: string
}

export interface TableSchema {
  name: string
  columns: any[]
  primary_keys: string[]
  foreign_keys: any[]
  indexes: any[]
}

export interface DatabaseSchema {
  connection_name: string
  tables: TableSchema[]
  table_count: number
}

export interface OntologySearchQuery {
  query: string
  entity_types?: string[]
  limit?: number
}

// Database API Functions

/**
 * Create a database connection
 */
export async function createDatabaseConnection(
  data: CreateDatabaseConnectionRequest
): Promise<DatabaseConnection> {
  const response = await apiClient.post<DatabaseConnection>('/database/connections', data)
  return response.data
}

/**
 * List all database connections
 */
export async function listDatabaseConnections(): Promise<DatabaseConnection[]> {
  const response = await apiClient.get<DatabaseConnection[]>('/database/connections')
  return response.data
}

/**
 * Get a specific database connection
 */
export async function getDatabaseConnection(name: string): Promise<DatabaseConnection> {
  const response = await apiClient.get<DatabaseConnection>(`/database/connections/${name}`)
  return response.data
}

/**
 * Update a database connection
 */
export async function updateDatabaseConnection(
  name: string,
  data: UpdateDatabaseConnectionRequest
): Promise<DatabaseConnection> {
  const response = await apiClient.put<DatabaseConnection>(
    `/database/connections/${name}`,
    data
  )
  return response.data
}

/**
 * Delete a database connection
 */
export async function deleteDatabaseConnection(name: string): Promise<void> {
  await apiClient.delete(`/database/connections/${name}`)
}

/**
 * Test a database connection
 */
export async function testDatabaseConnection(name: string): Promise<DatabaseTestResult> {
  const response = await apiClient.post<DatabaseTestResult>(
    `/database/connections/${name}/test`
  )
  return response.data
}

/**
 * Get database schema
 */
export async function getDatabaseSchema(name: string): Promise<DatabaseSchema> {
  const response = await apiClient.get<DatabaseSchema>(`/database/connections/${name}/schema`)
  return response.data
}

/**
 * List all ontologies
 */
export async function listOntologies(): Promise<any[]> {
  const response = await apiClient.get<any[]>('/database/ontologies')
  return response.data
}

/**
 * Get a specific ontology
 */
export async function getOntology(name: string): Promise<any> {
  const response = await apiClient.get<any>(`/database/ontologies/${name}`)
  return response.data
}

/**
 * Search within an ontology
 */
export async function searchOntology(
  name: string,
  query: OntologySearchQuery
): Promise<any[]> {
  const response = await apiClient.post<any[]>(`/database/ontologies/${name}/search`, query)
  return response.data
}

/**
 * Execute SQL query on a database connection
 */
export async function executeDatabaseQuery(
  connectionName: string,
  sql: string,
  params?: Record<string, any>,
  fetchLimit?: number
): Promise<any> {
  const response = await apiClient.post<any>(
    `/database/connections/${connectionName}/query`,
    {
      sql,
      params,
      fetch_limit: fetchLimit || 100
    }
  )
  return response.data
}

export default apiClient
