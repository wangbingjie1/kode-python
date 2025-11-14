<template>
  <div v-if="question" class="user-input-dialog-overlay" @click.self="handleCancel">
    <div class="user-input-dialog">
      <!-- 问题标题 -->
      <div class="dialog-header">
        <h3 class="dialog-title">{{ question.question }}</h3>
      </div>

      <!-- 上下文说明（如果有） -->
      <div v-if="question.context" class="dialog-context">
        <i class="icon-info"></i>
        <span>{{ question.context }}</span>
      </div>

      <!-- 输入区域 -->
      <div class="dialog-body">
        <!-- 文本输入 -->
        <div v-if="question.question_type === 'text'" class="input-group">
          <input
            v-model="textAnswer"
            type="text"
            class="text-input"
            :placeholder="question.default_value || '请输入...'"
            @keyup.enter="handleSubmit"
            autofocus
          />
        </div>

        <!-- 单选 -->
        <div v-else-if="question.question_type === 'select'" class="options-group">
          <div
            v-for="option in question.options"
            :key="option"
            class="option-item"
            :class="{ selected: selectAnswer === option }"
            @click="selectAnswer = option"
          >
            <input
              type="radio"
              :value="option"
              v-model="selectAnswer"
              :id="`option-${option}`"
            />
            <label :for="`option-${option}`">{{ option }}</label>
          </div>
        </div>

        <!-- 多选 -->
        <div v-else-if="question.question_type === 'multiselect'" class="options-group">
          <div
            v-for="option in question.options"
            :key="option"
            class="option-item"
            :class="{ selected: multiselectAnswer.includes(option) }"
            @click="toggleMultiselect(option)"
          >
            <input
              type="checkbox"
              :value="option"
              v-model="multiselectAnswer"
              :id="`option-${option}`"
            />
            <label :for="`option-${option}`">{{ option }}</label>
          </div>
        </div>

        <!-- 确认框 -->
        <div v-else-if="question.question_type === 'confirm'" class="confirm-buttons">
          <button class="btn btn-confirm" @click="handleSubmit(true)">
            <i class="icon-check"></i>
            确认
          </button>
          <button class="btn btn-cancel" @click="handleSubmit(false)">
            <i class="icon-close"></i>
            取消
          </button>
        </div>
      </div>

      <!-- 操作按钮（除确认框外） -->
      <div v-if="question.question_type !== 'confirm'" class="dialog-footer">
        <button class="btn btn-secondary" @click="handleCancel">
          取消
        </button>
        <button
          class="btn btn-primary"
          @click="handleSubmit()"
          :disabled="!canSubmit"
        >
          提交
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { UserInputQuestion } from '@/stores/chat'

// Props
const props = defineProps<{
  question: UserInputQuestion | null
}>()

// Emits
const emit = defineEmits<{
  submit: [answer: any]
  cancel: []
}>()

// State
const textAnswer = ref('')
const selectAnswer = ref('')
const multiselectAnswer = ref<string[]>([])

// Computed
const canSubmit = computed(() => {
  if (!props.question) return false

  switch (props.question.question_type) {
    case 'text':
      return textAnswer.value.trim().length > 0 || !props.question.required
    case 'select':
      return selectAnswer.value.length > 0 || !props.question.required
    case 'multiselect':
      return multiselectAnswer.value.length > 0 || !props.question.required
    default:
      return true
  }
})

// Methods
function handleSubmit(answer?: any) {
  if (!props.question) return

  let finalAnswer: any

  if (props.question.question_type === 'confirm') {
    // 确认框直接传递参数
    finalAnswer = answer
  } else if (props.question.question_type === 'text') {
    finalAnswer = textAnswer.value || props.question.default_value || ''
  } else if (props.question.question_type === 'select') {
    finalAnswer = selectAnswer.value
  } else if (props.question.question_type === 'multiselect') {
    finalAnswer = multiselectAnswer.value
  }

  emit('submit', finalAnswer)
  resetForm()
}

function handleCancel() {
  if (props.question?.required) {
    // 必填问题不允许取消
    return
  }
  emit('cancel')
  resetForm()
}

function toggleMultiselect(option: string) {
  const index = multiselectAnswer.value.indexOf(option)
  if (index > -1) {
    multiselectAnswer.value.splice(index, 1)
  } else {
    multiselectAnswer.value.push(option)
  }
}

function resetForm() {
  textAnswer.value = ''
  selectAnswer.value = ''
  multiselectAnswer.value = []
}

// Watch for question changes
watch(
  () => props.question,
  (newQuestion) => {
    if (newQuestion) {
      resetForm()
      // 设置默认值
      if (newQuestion.default_value && newQuestion.question_type === 'text') {
        textAnswer.value = newQuestion.default_value
      }
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.user-input-dialog-overlay {
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
  backdrop-filter: blur(4px);
}

.user-input-dialog {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateY(-50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.dialog-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.dialog-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.dialog-context {
  padding: 12px 24px;
  background: #eff6ff;
  border-left: 4px solid #3b82f6;
  margin: 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 14px;
  color: #1e40af;
}

.dialog-context.warning {
  background: #fef3c7;
  border-left-color: #f59e0b;
  color: #92400e;
}

.icon-info::before {
  content: 'ℹ️';
  font-style: normal;
}

.dialog-body {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

.input-group {
  width: 100%;
}

.text-input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 15px;
  transition: all 0.2s;
  outline: none;
}

.text-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.options-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
}

.option-item:hover {
  border-color: #3b82f6;
  background: #f9fafb;
}

.option-item.selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.option-item input[type='radio'],
.option-item input[type='checkbox'] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #3b82f6;
}

.option-item label {
  flex: 1;
  cursor: pointer;
  font-size: 15px;
  color: #374151;
  user-select: none;
}

.confirm-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.dialog-footer {
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-confirm {
  background: #10b981;
  color: white;
  min-width: 120px;
  justify-content: center;
}

.btn-confirm:hover {
  background: #059669;
}

.btn-cancel {
  background: #ef4444;
  color: white;
  min-width: 120px;
  justify-content: center;
}

.btn-cancel:hover {
  background: #dc2626;
}

.icon-check::before {
  content: '✓';
  font-size: 18px;
}

.icon-close::before {
  content: '✕';
  font-size: 18px;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .user-input-dialog {
    background: #1f2937;
  }

  .dialog-title {
    color: #f9fafb;
  }

  .dialog-header {
    border-bottom-color: #374151;
  }

  .text-input {
    background: #374151;
    border-color: #4b5563;
    color: #f9fafb;
  }

  .text-input:focus {
    border-color: #3b82f6;
  }

  .option-item {
    background: #374151;
    border-color: #4b5563;
  }

  .option-item:hover {
    background: #4b5563;
  }

  .option-item.selected {
    background: #1e3a8a;
  }

  .option-item label {
    color: #e5e7eb;
  }

  .dialog-footer {
    border-top-color: #374151;
  }

  .btn-secondary {
    background: #374151;
    color: #e5e7eb;
  }

  .btn-secondary:hover {
    background: #4b5563;
  }
}
</style>
