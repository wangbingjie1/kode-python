<template>
  <aside :class="panelClass">
    <header class="flex items-center justify-between px-5 pb-4 pt-6">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.26em] text-[#b6a493]">Questionnaire</p>
        <p class="mt-2 text-lg font-semibold text-[#2f2720]">数据库问卷</p>
      </div>
      <button
        type="button"
        class="flex h-9 w-9 items-center justify-center rounded-full border border-transparent text-[#a38b75] transition hover:border-[#eadfd3] hover:bg-white/80 hover:text-[#7c6551]"
        aria-label="关闭问卷"
        @click="$emit('close')"
      >
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 6l12 12M6 18L18 6" />
        </svg>
      </button>
    </header>

    <div class="flex-1 overflow-y-auto px-5 pb-8">
      <!-- 无连接状态 -->
      <div v-if="!connectionName" class="flex flex-col items-center justify-center py-12 text-center">
        <svg class="h-12 w-12 text-[#b6a493]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p class="mt-4 text-sm text-[#9a8b7c]">请先选择数据库连接</p>
      </div>

      <!-- 加载中 -->
      <div v-else-if="loading" class="flex flex-col items-center justify-center py-12">
        <div class="h-8 w-8 animate-spin rounded-full border-2 border-[#b6a493] border-t-transparent"></div>
        <p class="mt-4 text-sm text-[#9a8b7c]">加载中...</p>
      </div>

      <!-- 未分析状态 -->
      <div v-else-if="loadStatus === 'no_analysis'" class="flex flex-col items-center justify-center py-12 text-center">
        <svg class="h-12 w-12 text-[#e6a23c]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="mt-4 text-sm font-medium text-[#6d5f52]">尚未进行不确定性分析</p>
        <p class="mt-2 text-xs text-[#9a8b7c]">请先让 AI 分析数据库结构</p>
      </div>

      <!-- 问卷内容 -->
      <div v-else class="space-y-4">
        <!-- 进度条 -->
        <section class="rounded-2xl border border-[#eadfd3] bg-white/80 p-4 shadow-sm">
          <div class="flex items-center justify-between text-sm">
            <span class="text-[#6d5f52]">高优先级问题进度</span>
            <span class="font-medium text-[#5c4f43]">
              {{ summary.high?.resolved || 0 }} / {{ summary.high?.total || 0 }}
            </span>
          </div>
          <div class="mt-3 h-2 w-full overflow-hidden rounded-full bg-[#f0ebe4]">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="canBuildOntology ? 'bg-emerald-400' : 'bg-[#b6a493]'"
              :style="{ width: `${highPriorityProgress}%` }"
            ></div>
          </div>
          <div v-if="canBuildOntology" class="mt-3 flex items-center gap-2 text-xs text-emerald-600">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span>可以构建本体</span>
          </div>
        </section>

        <!-- 过滤器 -->
        <div class="flex flex-wrap gap-2">
          <!-- 优先级过滤 -->
          <div class="flex gap-1">
            <button
              v-for="filter in priorityFilterOptions"
              :key="filter"
              class="rounded-full px-3 py-1.5 text-xs font-medium transition"
              :class="priorityFilter === filter
                ? 'bg-[#5c4f43] text-white'
                : 'bg-[#f0ebe4] text-[#6d5f52] hover:bg-[#e5ddd3]'"
              @click="priorityFilter = filter; loadQuestions()"
            >
              {{ filter === 'high' ? '高优先级' : '全部优先级' }}
            </button>
          </div>
          <!-- 状态过滤 -->
          <div class="flex gap-1">
            <button
              v-for="filter in statusFilterOptions"
              :key="filter"
              class="rounded-full px-3 py-1.5 text-xs font-medium transition"
              :class="statusFilter === filter
                ? 'bg-[#7c6551] text-white'
                : 'bg-[#f0ebe4] text-[#6d5f52] hover:bg-[#e5ddd3]'"
              @click="statusFilter = filter; loadQuestions()"
            >
              {{ filter === 'pending' ? '待回答' : '全部状态' }}
            </button>
          </div>
          <!-- AI 分析按钮 -->
          <button
            class="ml-auto flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#5c4f43] to-[#7c6551] px-3 py-1.5 text-xs font-medium text-white transition hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!connectionName || pendingCount === 0"
            @click="showAIAnalysisModal = true"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.591.659H9.061a2.25 2.25 0 01-1.591-.659L5 14.5m14 0l.94 2.06a2.25 2.25 0 01-2.093 3.19H6.153a2.25 2.25 0 01-2.093-3.19L5 14.5" />
            </svg>
            AI 分析
          </button>
        </div>

        <!-- AI 分析弹窗 -->
        <AIAnalysisModal
          v-if="showAIAnalysisModal"
          :connection-name="connectionName"
          :pending-count="pendingCount"
          @close="showAIAnalysisModal = false"
          @accepted="handleAIAnswerAccepted"
        />

        <!-- 问题列表 -->
        <div class="space-y-3">
          <div
            v-for="group in questionGroups"
            :key="group.domain"
            class="rounded-2xl border border-[#eadfd3] bg-white/70 overflow-hidden"
          >
            <!-- 分组标题 -->
            <button
              class="flex w-full items-center justify-between p-4 text-left transition hover:bg-[#faf8f5]"
              @click="toggleGroup(group.domain)"
            >
              <span class="text-sm font-semibold text-[#3d3430]">{{ group.domain }}</span>
              <div class="flex items-center gap-2">
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="getGroupProgress(group) === group.question_count
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-[#f0ebe4] text-[#6d5f52]'"
                >
                  {{ getGroupAnswered(group) }}/{{ group.question_count }}
                </span>
                <svg
                  class="h-4 w-4 text-[#b6a493] transition-transform"
                  :class="{ 'rotate-180': expandedGroups.includes(group.domain) }"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>

            <!-- 问题列表 -->
            <div v-if="expandedGroups.includes(group.domain)" class="border-t border-[#eadfd3]">
              <div
                v-for="question in group.questions"
                :key="question.id"
                class="border-b border-[#f0ebe4] p-4 last:border-b-0"
                :class="{ 'bg-emerald-50/50': question.status === 'resolved' }"
              >
                <!-- 标签 -->
                <div class="flex flex-wrap gap-2 mb-2">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="getPriorityClass(question.priority)"
                  >
                    {{ question.priority }}
                  </span>
                  <span class="rounded-full bg-[#f0ebe4] px-2 py-0.5 text-xs text-[#6d5f52]">
                    {{ question.entity }}
                  </span>
                </div>

                <!-- 问题 -->
                <p class="text-sm text-[#3d3430] leading-relaxed">{{ question.question }}</p>

                <!-- 上下文 -->
                <div v-if="question.context" class="mt-2 rounded-lg bg-[#f8f6f3] p-2 text-xs text-[#9a8b7c]">
                  {{ question.context }}
                </div>

                <!-- 建议选项 -->
                <div v-if="question.suggestions?.length" class="mt-3 flex flex-wrap gap-1">
                  <span class="text-xs text-[#9a8b7c]">建议：</span>
                  <button
                    v-for="(s, idx) in question.suggestions.slice(0, 3)"
                    :key="idx"
                    class="rounded-full bg-[#f0ebe4] px-2 py-0.5 text-xs text-[#6d5f52] transition hover:bg-[#e5ddd3]"
                    @click="fillSuggestion(question.id, s)"
                  >
                    {{ s }}
                  </button>
                </div>

                <!-- 已回答显示（可编辑） -->
                <div v-if="question.status === 'resolved'" class="mt-3 space-y-2">
                  <!-- 非编辑模式：显示答案 -->
                  <div v-if="!editingIds.includes(question.id)" class="flex items-start gap-2">
                    <svg class="h-4 w-4 flex-shrink-0 text-emerald-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    <span class="flex-1 text-sm text-[#5c4f43]">{{ question.answer }}</span>
                    <button
                      class="flex-shrink-0 rounded px-2 py-1 text-xs text-[#9a8b7c] transition hover:bg-[#f0ebe4] hover:text-[#6d5f52]"
                      @click="startEdit(question)"
                    >
                      修改
                    </button>
                  </div>
                  <!-- 编辑模式 -->
                  <div v-else>
                    <textarea
                      v-model="answers[question.id]"
                      rows="2"
                      class="w-full rounded-lg border border-[#eadfd3] bg-white px-3 py-2 text-sm text-[#3d3430] placeholder-[#b6a493] focus:border-[#b6a493] focus:outline-none focus:ring-1 focus:ring-[#b6a493]"
                      placeholder="输入答案..."
                    ></textarea>
                    <div class="mt-2 flex gap-2">
                      <button
                        class="rounded-lg bg-[#5c4f43] px-3 py-1.5 text-xs font-medium text-white transition hover:bg-[#4a3f35] disabled:opacity-50"
                        :disabled="!answers[question.id]?.trim() || savingIds.includes(question.id)"
                        @click="saveAnswer(question.id)"
                      >
                        {{ savingIds.includes(question.id) ? '保存中...' : '保存' }}
                      </button>
                      <button
                        class="rounded-lg bg-[#f0ebe4] px-3 py-1.5 text-xs font-medium text-[#6d5f52] transition hover:bg-[#e5ddd3]"
                        @click="cancelEdit(question.id)"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                </div>

                <!-- 未回答：输入框 -->
                <div v-else class="mt-3 space-y-2">
                  <textarea
                    v-model="answers[question.id]"
                    rows="2"
                    class="w-full rounded-lg border border-[#eadfd3] bg-white px-3 py-2 text-sm text-[#3d3430] placeholder-[#b6a493] focus:border-[#b6a493] focus:outline-none focus:ring-1 focus:ring-[#b6a493]"
                    placeholder="输入答案..."
                    @blur="handleAnswerBlur(question.id)"
                  ></textarea>
                  <div class="flex gap-2">
                    <button
                      class="rounded-lg bg-[#5c4f43] px-3 py-1.5 text-xs font-medium text-white transition hover:bg-[#4a3f35] disabled:opacity-50"
                      :disabled="!answers[question.id]?.trim() || savingIds.includes(question.id)"
                      @click="saveAnswer(question.id)"
                    >
                      {{ savingIds.includes(question.id) ? '保存中...' : '保存' }}
                    </button>
                    <button
                      v-if="question.priority !== 'high'"
                      class="rounded-lg bg-[#f0ebe4] px-3 py-1.5 text-xs font-medium text-[#6d5f52] transition hover:bg-[#e5ddd3] disabled:opacity-50"
                      :disabled="skippingIds.includes(question.id)"
                      @click="skipQuestion(question.id)"
                    >
                      {{ skippingIds.includes(question.id) ? '跳过中...' : '跳过' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="questionGroups.length === 0" class="flex flex-col items-center justify-center py-8 text-center">
            <svg class="h-10 w-10 text-[#b6a493]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="mt-3 text-sm text-[#9a8b7c]">暂无待回答的问题</p>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  sidebarLoadUncertainties,
  sidebarAnswerSingle,
  sidebarSkipQuestion,
  type UncertaintyGroup,
  type SidebarLoadResponse
} from '@/services/api'
import AIAnalysisModal from './AIAnalysisModal.vue'

interface Props {
  connectionName?: string
  modal?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  answered: [canBuild: boolean]
}>()

const panelClass = computed(() => [
  'flex h-full flex-col bg-[#fdfaf4] text-[#2f2720]',
  props.modal
    ? 'w-full max-w-md shadow-2xl ring-1 ring-black/10 sm:ml-auto sm:w-[420px] sm:rounded-l-3xl'
    : '',
])

// 状态
const loading = ref(false)
const loadStatus = ref<'success' | 'no_analysis' | ''>('')
const questionGroups = ref<UncertaintyGroup[]>([])
const summary = ref<Record<string, { total: number; resolved: number; skipped: number; remaining: number }>>({})
const canBuildOntology = ref(false)
const priorityFilter = ref<'high' | 'all'>('high')
const priorityFilterOptions: ('high' | 'all')[] = ['high', 'all']
const statusFilter = ref<'pending' | 'all'>('all')
const statusFilterOptions: ('pending' | 'all')[] = ['pending', 'all']
const expandedGroups = ref<string[]>([])
const answers = ref<Record<string, string>>({})
const savingIds = ref<string[]>([])
const skippingIds = ref<string[]>([])
const editingIds = ref<string[]>([])
const showAIAnalysisModal = ref(false)

// 计算待处理问题数
const pendingCount = computed(() => {
  return summary.value.high?.remaining || 0
})

// 计算属性
const highPriorityProgress = computed(() => {
  const high = summary.value.high
  if (!high || high.total === 0) return 100
  return Math.round((high.resolved / high.total) * 100)
})

// 方法
const loadQuestions = async () => {
  if (!props.connectionName) return

  loading.value = true
  try {
    const response = await sidebarLoadUncertainties({
      connection_name: props.connectionName,
      priority_filter: priorityFilter.value === 'high' ? ['high'] : undefined,
      status_filter: statusFilter.value === 'pending' ? ['pending'] : undefined,
      group_by: 'domain'
    })

    loadStatus.value = response.status
    questionGroups.value = response.groups
    summary.value = response.summary
    canBuildOntology.value = response.can_build_ontology

    // 默认展开第一个分组
    if (response.groups.length > 0 && expandedGroups.value.length === 0) {
      expandedGroups.value = [response.groups[0].domain]
    }

    // 初始化答案
    response.groups.forEach(group => {
      group.questions.forEach(q => {
        if (!answers.value[q.id]) {
          answers.value[q.id] = ''
        }
      })
    })
  } catch (error: any) {
    console.error('加载问卷失败:', error)
  } finally {
    loading.value = false
  }
}

const saveAnswer = async (questionId: string) => {
  const answer = answers.value[questionId]?.trim()
  if (!answer || !props.connectionName) return

  savingIds.value.push(questionId)
  try {
    const response = await sidebarAnswerSingle({
      connection_name: props.connectionName,
      uncertainty_id: questionId,
      answer
    })

    canBuildOntology.value = response.can_build_ontology
    emit('answered', response.can_build_ontology)

    // 清除编辑状态
    editingIds.value = editingIds.value.filter(id => id !== questionId)

    // 重新加载问题列表
    await loadQuestions()
  } catch (error: any) {
    console.error('保存失败:', error)
  } finally {
    savingIds.value = savingIds.value.filter(id => id !== questionId)
  }
}

const skipQuestion = async (questionId: string) => {
  if (!props.connectionName) return

  skippingIds.value.push(questionId)
  try {
    await sidebarSkipQuestion({
      connection_name: props.connectionName,
      uncertainty_id: questionId
    })
    await loadQuestions()
  } catch (error: any) {
    console.error('跳过失败:', error)
  } finally {
    skippingIds.value = skippingIds.value.filter(id => id !== questionId)
  }
}

const handleAnswerBlur = (questionId: string) => {
  // 失焦时不自动保存，让用户主动点击保存
}

const fillSuggestion = (questionId: string, suggestion: string) => {
  answers.value[questionId] = suggestion
}

const startEdit = (question: { id: string; answer?: string }) => {
  answers.value[question.id] = question.answer || ''
  editingIds.value.push(question.id)
}

const cancelEdit = (questionId: string) => {
  editingIds.value = editingIds.value.filter(id => id !== questionId)
  delete answers.value[questionId]
}

const toggleGroup = (domain: string) => {
  const index = expandedGroups.value.indexOf(domain)
  if (index === -1) {
    expandedGroups.value.push(domain)
  } else {
    expandedGroups.value.splice(index, 1)
  }
}

const getPriorityClass = (priority: string) => {
  switch (priority) {
    case 'high': return 'bg-rose-100 text-rose-700'
    case 'medium': return 'bg-amber-100 text-amber-700'
    case 'low': return 'bg-blue-100 text-blue-700'
    default: return 'bg-gray-100 text-gray-700'
  }
}

const getGroupAnswered = (group: UncertaintyGroup) => {
  return group.questions.filter(q => q.status === 'resolved').length
}

const getGroupProgress = (group: UncertaintyGroup) => {
  return getGroupAnswered(group)
}

// 处理 AI 答案采纳
const handleAIAnswerAccepted = async () => {
  // 重新加载问题列表以获取最新状态
  await loadQuestions()
}

// 监听 connectionName 变化
watch(() => props.connectionName, (newVal) => {
  if (newVal) {
    loadQuestions()
  }
}, { immediate: true })

onMounted(() => {
  if (props.connectionName) {
    loadQuestions()
  }
})
</script>
