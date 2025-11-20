<template>
  <!-- <Teleport to="body"> -->
    <Transition name="dialog-fade">
      <div v-if="visible" class="dialog-overlay" @click.self="handleClose">
        <div class="dialog-container">
          <!-- Header -->
          <div class="dialog-header">
            <div>
              <h2 class="dialog-title">业务不确定性问题批量回答</h2>
              <p class="dialog-subtitle">共 {{ totalQuestions }} 个高优先级问题需要确认</p>
            </div>
            <button @click="handleClose" class="close-button" title="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Content -->
          <div class="dialog-content">
            <!-- 按域分组展示 -->
            <div
              v-for="(group, groupIdx) in data?.groups || []"
              :key="groupIdx"
              class="uncertainty-group"
            >
              <div class="group-header">
                <h3 class="group-title">{{ group.domain }}</h3>
                <span class="group-count">{{ group.question_count }} 个问题</span>
              </div>

              <!-- 问题列表 -->
              <div
                v-for="(question, qIdx) in group.questions"
                :key="question.id"
                class="uncertainty-item"
              >
                <div class="question-header">
                  <span class="question-number">问题 {{ qIdx + 1 }}</span>
                  <span class="question-priority" :class="`priority-${question.priority || 'high'}`">
                    {{ question.priority === 'high' ? '高优先级' : question.priority }}
                  </span>
                </div>

                <div class="question-content">
                  <p class="question-text">{{ question.question }}</p>

                  <div v-if="question.context" class="question-context">
                    <strong>上下文：</strong>{{ question.context }}
                  </div>

                  <div v-if="question.impact" class="question-impact">
                    <strong>影响：</strong>{{ question.impact }}
                  </div>

                  <div v-if="question.suggestions && question.suggestions.length > 0" class="question-suggestions">
                    <strong>建议：</strong>
                    <ul>
                      <li v-for="(suggestion, sIdx) in question.suggestions" :key="sIdx">
                        {{ suggestion }}
                      </li>
                    </ul>
                  </div>
                </div>

                <div class="answer-input-group">
                  <label :for="`answer-${question.id}`" class="answer-label">你的回答：</label>
                  <textarea
                    :id="`answer-${question.id}`"
                    v-model="answers[question.id]"
                    class="answer-textarea"
                    placeholder="请输入你的回答..."
                    rows="3"
                  ></textarea>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="dialog-footer">
            <div class="footer-info">
              <span class="answered-count">
                已回答 {{ answeredCount }} / {{ totalQuestions }} 题
              </span>
            </div>
            <div class="footer-actions">
              <button @click="handleClose" class="cancel-button">
                稍后回答
              </button>
              <button
                @click="handleSubmit"
                :disabled="isSubmitting || answeredCount === 0"
                class="submit-button"
              >
                <svg v-if="!isSubmitting" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <svg v-else class="animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v4m0 8v4m8-8h-4M8 12H4m12.364-7.364l-2.828 2.828M8.464 15.536l-2.828 2.828m0-12.728l2.828 2.828m8.485 8.485l2.828 2.828" />
                </svg>
                <span>{{ isSubmitting ? '提交中...' : '提交所有答案' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  <!-- </Teleport> -->
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { notification } from '@/composables/useNotification'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()

interface UncertaintyData {
  connection_name?: string
  total_loaded: number
  groups: Array<{
    domain: string
    question_count: number
    questions: Array<{
      id: string
      question: string
      priority?: string
      context?: string
      impact?: string
      suggestions?: string[]
      domain?: string
    }>
  }>
}

interface Props {
  visible: boolean
  data: UncertaintyData | null
  connectionName?: string
}

const props = defineProps<Props>()
const emit = defineEmits(['update:visible', 'submit'])

const answers = ref<Record<string, string>>({})
const isSubmitting = ref(false)

const totalQuestions = computed(() => {
  if (!props.data?.groups) return 0
  return props.data.groups.reduce((sum, group) => sum + group.question_count, 0)
})

const answeredCount = computed(() => {
  return Object.values(answers.value).filter(a => a?.trim()).length
})

// 调试：监听 visible prop 变化
watch(() => props.visible, (newVal) => {
  console.log('[UncertaintyBatchDialog] visible prop changed to:', newVal)
  console.log('[UncertaintyBatchDialog] data:', props.data)
})

// 监听对话框关闭时清空答案
watch(() => props.visible, (newVal) => {
  if (!newVal) {
    // 延迟清空，等动画结束
    setTimeout(() => {
      answers.value = {}
      isSubmitting.value = false
    }, 300)
  }
})

function handleClose() {
  if (isSubmitting.value) {
    notification.warning('提示', '正在提交中，请稍候...')
    return
  }

  if (answeredCount.value > 0) {
    if (!confirm(`你已经回答了 ${answeredCount.value} 个问题，确定要关闭吗？已填写的内容将丢失。`)) {
      return
    }
  }

  emit('update:visible', false)
}

async function handleSubmit() {
  if (!props.data) {
    notification.error('错误', '无法加载问题数据')
    return
  }

  const connectionName = props.data.connection_name || props.connectionName

  if (!connectionName) {
    notification.error('错误', '无法确定数据库连接名称')
    return
  }

  // 检查是否有未填写的问题
  const allQuestions: any[] = []
  props.data.groups?.forEach((group) => {
    if (group.questions) {
      allQuestions.push(...group.questions)
    }
  })

  const unansweredCount = allQuestions.filter(q => !answers.value[q.id]?.trim()).length
  
  // 移除 confirm 确认框，直接提交
  // 用户点击提交按钮即表示确认提交当前已填写的内容
  
  isSubmitting.value = true

  try {
    console.log('[UncertaintyBatchDialog] Submitting answers:', answers.value)
    
    // 使用 chatStore 的 submitUserResponse 方法
    // 传递 connection_name 和 answers
    await chatStore.submitUserResponse({
      connection_name: connectionName,
      answers: answers.value
    })

    notification.success('提交成功', '所有问题已记录，AI 正在继续处理...')
    emit('update:visible', false)
    emit('submit', answers.value)

    console.log('[UncertaintyBatchDialog] Answers submitted, Agent should continue now')
  } catch (error: any) {
    console.error('[UncertaintyBatchDialog] Submission error:', error)
    notification.error('提交失败', error.message || '网络错误')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
}

.dialog-container {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.dialog-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 0.25rem 0;
}

.dialog-subtitle {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
}

.close-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: #f3f4f6;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.close-button:hover {
  background: #e5e7eb;
}

.close-button svg {
  width: 18px;
  height: 18px;
  color: #6b7280;
}

.dialog-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.dialog-content::-webkit-scrollbar {
  width: 10px;
}

.dialog-content::-webkit-scrollbar-track {
  background: #f3f4f6;
  border-radius: 5px;
}

.dialog-content::-webkit-scrollbar-thumb {
  background: #9ca3af;
  border-radius: 5px;
}

.dialog-content::-webkit-scrollbar-thumb:hover {
  background: #6b7280;
}

.uncertainty-group {
  margin-bottom: 2rem;
  background: #f9fafb;
  border-radius: 0.75rem;
  padding: 1.25rem;
  border: 1px solid #e5e7eb;
}

.uncertainty-group:last-child {
  margin-bottom: 0;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
}

.group-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.group-count {
  font-size: 0.8125rem;
  color: #6b7280;
  background: white;
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  font-weight: 500;
}

.uncertainty-item {
  margin-bottom: 1.5rem;
  padding: 1.25rem;
  background: white;
  border-radius: 0.625rem;
  border: 1px solid #e5e7eb;
  transition: all 0.15s ease;
}

.uncertainty-item:hover {
  border-color: #d1d5db;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.uncertainty-item:last-child {
  margin-bottom: 0;
}

.question-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.875rem;
}

.question-number {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #374151;
}

.question-priority {
  font-size: 0.8125rem;
  padding: 0.3125rem 0.625rem;
  border-radius: 0.3125rem;
  font-weight: 500;
}

.priority-high {
  background: #fee2e2;
  color: #dc2626;
}

.priority-medium {
  background: #fef3c7;
  color: #d97706;
}

.priority-low {
  background: #e0e7ff;
  color: #4f46e5;
}

.question-content {
  margin-bottom: 1.125rem;
}

.question-text {
  font-size: 0.9375rem;
  font-weight: 500;
  color: #111827;
  margin-bottom: 0.875rem;
  line-height: 1.6;
}

.question-context,
.question-impact {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.625rem;
  line-height: 1.5;
  padding: 0.625rem;
  background: #f9fafb;
  border-radius: 0.4375rem;
  border-left: 3px solid #d1d5db;
}

.question-context strong,
.question-impact strong {
  color: #374151;
  margin-right: 0.25rem;
}

.question-suggestions {
  font-size: 0.875rem;
  color: #6b7280;
  margin-top: 0.625rem;
  padding: 0.625rem;
  background: #eff6ff;
  border-radius: 0.4375rem;
  border-left: 3px solid #3b82f6;
}

.question-suggestions strong {
  color: #1e40af;
  display: block;
  margin-bottom: 0.375rem;
}

.question-suggestions ul {
  margin: 0.625rem 0 0 0;
  padding-left: 1.375rem;
  list-style-type: disc;
}

.question-suggestions li {
  margin-bottom: 0.3125rem;
  line-height: 1.5;
}

.answer-input-group {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.answer-label {
  font-size: 0.9375rem;
  font-weight: 500;
  color: #374151;
}

.answer-textarea {
  width: 100%;
  padding: 0.875rem;
  border: 1px solid #d1d5db;
  border-radius: 0.4375rem;
  font-size: 0.9375rem;
  line-height: 1.5;
  color: #111827;
  background: white;
  resize: vertical;
  transition: all 0.15s ease;
  font-family: inherit;
}

.answer-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.answer-textarea::placeholder {
  color: #9ca3af;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
  flex-shrink: 0;
  border-bottom-left-radius: 0.75rem;
  border-bottom-right-radius: 0.75rem;
}

.footer-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.answered-count {
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
}

.footer-actions {
  display: flex;
  gap: 0.75rem;
}

.cancel-button {
  padding: 0.625rem 1.25rem;
  border-radius: 0.4375rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s ease;
  font-weight: 500;
  font-size: 0.9375rem;
}

.cancel-button:hover {
  border-color: #9ca3af;
  background: #f9fafb;
  color: #374151;
}

.submit-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.5rem;
  border-radius: 0.4375rem;
  border: none;
  background: #3b82f6;
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
  font-weight: 600;
  font-size: 0.9375rem;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.submit-button:hover:not(:disabled) {
  background: #2563eb;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}

.submit-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.submit-button svg {
  width: 1.125rem;
  height: 1.125rem;
}

/* Transitions */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.25s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

.dialog-fade-enter-active .dialog-container {
  animation: dialog-bounce-in 0.3s ease;
}

.dialog-fade-leave-active .dialog-container {
  animation: dialog-bounce-out 0.25s ease;
}

@keyframes dialog-bounce-in {
  0% {
    transform: scale(0.95) translateY(-10px);
    opacity: 0;
  }
  100% {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

@keyframes dialog-bounce-out {
  0% {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
  100% {
    transform: scale(0.95) translateY(-10px);
    opacity: 0;
  }
}
</style>
