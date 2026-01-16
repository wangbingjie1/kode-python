export type QuestionType = "single-choice" | "multiple-choice" | "text-reply"

export interface QuestionOption {
  id: string
  label: string
}

export interface PendingQuestion {
  id: string
  type: QuestionType
  question: string
  description?: string
  options?: QuestionOption[] // 选择题的选项
  placeholder?: string // 回复题的 placeholder
}

export interface QuestionAnswer {
  questionId: string
  // 单选: string, 多选: string[], 回复: string
  value: string | string[] | null
}

export interface AutoResolveResult {
  questionId: string
  questionText: string
  resolved: boolean
  resolvedValue?: string
  dataSource?: string
  rowsScanned?: number
}
