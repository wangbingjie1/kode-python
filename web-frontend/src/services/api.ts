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

    // 🔥 处理 429 配额不足错误 - 不要登出，显示友好提示
    if (error.response?.status === 429) {
      console.warn('[API] Token quota exceeded (429)')
      const errorData = error.response?.data || {}
      // 标记错误类型，前端可以据此显示特定 UI
      error.isQuotaExceeded = true
      error.quotaMessage = errorData.detail || 'Token 配额已用尽，请升级套餐或等待下个计费周期'
      error.errorCode = errorData.error_code || 'TOKEN_QUOTA_EXCEEDED'
      // 不要 logout，直接返回错误让调用方处理
      return Promise.reject(error)
    }

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
  matched_message?: string  // 搜索时匹配到的消息片段
}

export interface ConversationListResponse {
  items: Conversation[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface ListConversationsParams {
  limit?: number
  offset?: number
  search?: string
  search_content?: boolean
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
 * List conversations for a project with pagination and search
 */
export async function listProjectConversations(
  projectId: string,
  params: ListConversationsParams = {}
): Promise<ConversationListResponse> {
  const response = await apiClient.get<ConversationListResponse>(
    `/chat/projects/${projectId}/conversations`,
    { params }
  )
  return response.data
}

/**
 * Get or create default project for current user
 */
export async function getOrCreateDefaultProject(): Promise<any> {
  const response = await apiClient.get('/projects/user/default')
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

// Ontology Export Types
export interface OntologyExportRequest {
  format: 'json' | 'csv' | 'markdown'
  include_concepts: boolean
  include_relationships: boolean
  include_business_rules: boolean
  include_uncertainties: boolean
  selected_domains?: string[]
}

/**
 * Delete an ontology
 */
export async function deleteOntology(name: string): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.delete<{ success: boolean; message: string }>(
    `/database/ontologies/${name}`
  )
  return response.data
}

/**
 * Export ontology in specified format
 * Returns a Blob for file download
 */
export async function exportOntology(
  name: string,
  options: OntologyExportRequest
): Promise<Blob> {
  const response = await apiClient.post(
    `/database/ontologies/${name}/export`,
    options,
    {
      responseType: 'blob'
    }
  )
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

// Billing Types
export interface Plan {
  id: string
  name: string
  display_name: string
  description: string
  price: number
  billing_period: 'monthly' | 'yearly'
  token_quota: number  // 唯一计费项
  database_connection_quota: number
  database_access: boolean
  advanced_analysis: boolean
  ontology_building: boolean
  priority_support: boolean
  features: Record<string, any> | null
  is_active: boolean
  sort_order: number
}

export interface Subscription {
  id: string
  user_id: string
  plan_id: string
  status: 'active' | 'expired' | 'cancelled' | 'trial'
  start_date: string
  end_date: string
  auto_renew: boolean
  payment_method: string | null
  last_payment_date: string | null
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  created_at: string
  updated_at: string
  plan?: Plan
}

export interface Usage {
  id: string
  user_id: string
  subscription_id: string | null
  period_start: string
  period_end: string
  token_count: number  // 唯一计费项
  database_query_count: number
  created_at: string
  updated_at: string
}

export interface UsageSummary {
  current_period_start: string
  current_period_end: string
  token_used: number  // 已使用 Token
  token_quota: number  // Token 配额（唯一计费项）
  token_remaining: number  // 剩余 Token
  database_query_count: number
  is_quota_exceeded: boolean  // 是否超出 Token 配额
}

export interface CreateSubscriptionRequest {
  plan_id: string
  auto_renew?: boolean
}

export interface StripeCheckoutRequest {
  plan_id: string
  success_url: string
  cancel_url: string
}

export interface StripeCheckoutResponse {
  session_id: string
  checkout_url: string
}

// Billing API Functions

/**
 * List all available plans
 */
export async function listPlans(activeOnly = true): Promise<Plan[]> {
  const response = await apiClient.get<Plan[]>('/billing/plans', {
    params: { active_only: activeOnly }
  })
  return response.data
}

/**
 * Get a specific plan
 */
export async function getPlan(planId: string): Promise<Plan> {
  const response = await apiClient.get<Plan>(`/billing/plans/${planId}`)
  return response.data
}

/**
 * Get current user's subscription
 */
export async function getMySubscription(): Promise<Subscription> {
  const response = await apiClient.get<Subscription>('/billing/subscriptions/me')
  return response.data
}

/**
 * Create a new subscription
 */
export async function createSubscription(
  data: CreateSubscriptionRequest
): Promise<Subscription> {
  const response = await apiClient.post<Subscription>('/billing/subscriptions', data)
  return response.data
}

/**
 * Cancel a subscription
 */
export async function cancelSubscription(
  subscriptionId: string,
  immediate = false
): Promise<Subscription> {
  const response = await apiClient.post<Subscription>(
    `/billing/subscriptions/${subscriptionId}/cancel`,
    { immediate }
  )
  return response.data
}

/**
 * Get current user's usage
 */
export async function getMyUsage(): Promise<Usage> {
  const response = await apiClient.get<Usage>('/billing/usage/me')
  return response.data
}

/**
 * Get current user's usage summary
 */
export async function getMyUsageSummary(): Promise<UsageSummary> {
  const response = await apiClient.get<UsageSummary>('/billing/usage/me/summary')
  return response.data
}

/**
 * Create Stripe checkout session
 */
export async function createStripeCheckout(
  data: StripeCheckoutRequest
): Promise<StripeCheckoutResponse> {
  const response = await apiClient.post<StripeCheckoutResponse>(
    '/billing/stripe/checkout',
    data
  )
  return response.data
}

/**
 * Submit user response to interactive question
 *
 * Used when Agent calls AskUserTool and needs user input
 */
export interface UserResponsePayload {
  answer: any  // string | boolean | string[]
  question_type: 'text' | 'select' | 'multiselect' | 'confirm' | 'batch_form'
}

export async function submitUserResponse(
  conversationId: string,
  data: UserResponsePayload
): Promise<{ success: boolean; message: string; conversation_id: string }> {
  const response = await apiClient.post(
    `/sse/chat/${conversationId}/user-response`,
    data
  )
  return response.data
}

/**
 * Cancel ongoing streaming response
 *
 * Stops the AI from generating further responses in the current conversation
 */
export async function cancelStreaming(
  conversationId: string
): Promise<{ success: boolean; message: string; conversation_id: string }> {
  const response = await apiClient.post(
    `/sse/chat/${conversationId}/cancel`
  )
  return response.data
}

// ============== Uncertainty Sidebar API ==============

export interface UncertaintyItem {
  id: string
  domain: string
  type: string
  category: string
  priority: 'high' | 'medium' | 'low'
  entity: string
  question: string
  context?: string
  impact?: string
  suggestions: string[]
  status?: string
  answer?: string
  answered_at?: string
}

export interface UncertaintyGroup {
  domain: string
  question_count: number
  questions: UncertaintyItem[]
}

export interface SidebarLoadRequest {
  connection_name: string
  priority_filter?: string[]
  status_filter?: string[]
  group_by?: 'domain' | 'priority' | 'none'
  limit?: number
}

export interface SidebarLoadResponse {
  status: 'success' | 'no_analysis'
  connection_name: string
  total_count: number
  filtered_count: number
  groups: UncertaintyGroup[]
  summary: Record<string, { total: number; resolved: number; skipped: number; remaining: number }>
  can_build_ontology: boolean
  message: string
}

export interface SingleAnswerRequest {
  connection_name: string
  uncertainty_id: string
  answer: string
}

export interface SingleAnswerResponse {
  status: string
  uncertainty_id: string
  message: string
  remaining_high_priority: number
  can_build_ontology: boolean
}

export interface SkipQuestionRequest {
  connection_name: string
  uncertainty_id: string
  reason?: string
}

export interface SkipQuestionResponse {
  status: string
  uncertainty_id: string
  skipped_priority: string
  message: string
  remaining_high_priority: number
  can_build_ontology: boolean
}

export interface UncertaintyStatusResponse {
  status: string
  connection_name: string
  summary: Record<string, { total: number; resolved: number; skipped: number; remaining: number }>
  can_build_ontology: boolean
  message: string
}

/**
 * Load uncertainties for sidebar questionnaire
 */
export async function sidebarLoadUncertainties(
  request: SidebarLoadRequest
): Promise<SidebarLoadResponse> {
  const response = await apiClient.post<SidebarLoadResponse>('/uncertainty/sidebar/load', request)
  return response.data
}

/**
 * Answer a single uncertainty question
 */
export async function sidebarAnswerSingle(
  request: SingleAnswerRequest
): Promise<SingleAnswerResponse> {
  const response = await apiClient.post<SingleAnswerResponse>('/uncertainty/sidebar/answer', request)
  return response.data
}

/**
 * Skip a non-high-priority question
 */
export async function sidebarSkipQuestion(
  request: SkipQuestionRequest
): Promise<SkipQuestionResponse> {
  const response = await apiClient.post<SkipQuestionResponse>('/uncertainty/sidebar/skip', request)
  return response.data
}

/**
 * Get uncertainty status for a connection
 */
export async function getUncertaintyStatus(
  connectionName: string
): Promise<UncertaintyStatusResponse> {
  const response = await apiClient.get<UncertaintyStatusResponse>(`/uncertainty/status/${connectionName}`)
  return response.data
}

// ============== AI 分析相关 API ==============

export interface AcceptAIAnswerRequest {
  connection_name: string
  uncertainty_id: string
  answer: string
  confidence?: string
  reasoning?: string
}

export interface AcceptAIAnswerResponse {
  status: string
  uncertainty_id: string
  message: string
  remaining_high_priority: number
  can_build_ontology: boolean
}

/**
 * Accept AI analysis answer
 * 采纳 AI 分析生成的答案，写入本体文件
 */
export async function acceptAIAnswer(
  request: AcceptAIAnswerRequest
): Promise<AcceptAIAnswerResponse> {
  const response = await apiClient.post<AcceptAIAnswerResponse>('/uncertainty/sidebar/accept-ai-answer', request)
  return response.data
}

export default apiClient
