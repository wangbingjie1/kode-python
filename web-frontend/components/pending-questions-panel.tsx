"use client"

import { useState } from "react"
import type { PendingQuestion, QuestionAnswer, AutoResolveResult } from "@/types/pending-questions"
import { pendingQuestionsData, autoResolvableQuestions } from "@/lib/pending-questions-data"

interface PendingQuestionsPanelProps {
  pendingQuestions?: QuestionAnswer[]
  onSubmit?: (answers: QuestionAnswer[]) => void
}

export function PendingQuestionsPanel({ onSubmit, pendingQuestions }: PendingQuestionsPanelProps) {
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({})
  const [isResolving, setIsResolving] = useState(false)
  const [resolveResults, setResolveResults] = useState<AutoResolveResult[] | null>(null)
  const [resolvedQuestionIds, setResolvedQuestionIds] = useState<Set<string>>(new Set())

  const totalQuestions = pendingQuestionsData.length
  const autoResolvableCount = autoResolvableQuestions.length

  // 处理单选
  const handleSingleChoice = (questionId: string, optionId: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: optionId }))
  }

  // 处理多选
  const handleMultipleChoice = (questionId: string, optionId: string) => {
    setAnswers((prev) => {
      const current = (prev[questionId] as string[]) || []
      if (current.includes(optionId)) {
        return { ...prev, [questionId]: current.filter((id) => id !== optionId) }
      }
      return { ...prev, [questionId]: [...current, optionId] }
    })
  }

  // 处理文本回复
  const handleTextReply = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  // 执行自动解决
  const handleAutoResolve = async () => {
    setIsResolving(true)
    setResolveResults(null)

    // 模拟 AI Agent 流程
    const results: AutoResolveResult[] = []

    for (const qId of autoResolvableQuestions) {
      const question = pendingQuestionsData.find((q) => q.id === qId)
      if (!question) continue

      // 模拟延迟，逐个处理
      await new Promise((resolve) => setTimeout(resolve, 1500))

      const result: AutoResolveResult = {
        questionId: qId,
        questionText: question.question,
        resolved: true,
        dataSource: getDataSourceForQuestion(qId),
        rowsScanned: Math.floor(Math.random() * 50000) + 10000,
        resolvedValue: getResolvedValueForQuestion(question),
      }
      results.push(result)
      setResolveResults([...results])
    }

    // 更新已解决的问题
    setResolvedQuestionIds(new Set(autoResolvableQuestions))

    // 自动填入答案
    const autoAnswers: Record<string, string | string[]> = {}
    for (const result of results) {
      if (result.resolved && result.resolvedValue) {
        autoAnswers[result.questionId] = result.resolvedValue
      }
    }
    setAnswers((prev) => ({ ...prev, ...autoAnswers }))

    setIsResolving(false)
  }

  // 提交答案
  const handleSubmit = () => {
    const formattedAnswers: QuestionAnswer[] = Object.entries(answers).map(([questionId, value]) => ({
      questionId,
      value: value || null,
    }))
    onSubmit?.(formattedAnswers)
  }

  // 获取已回答的问题数量
  const answeredCount = Object.keys(answers).filter((key) => {
    const val = answers[key]
    if (Array.isArray(val)) return val.length > 0
    return val && val.trim() !== ""
  }).length

  // 未解决的问题
  const unresolvedQuestions = pendingQuestionsData.filter((q) => !resolvedQuestionIds.has(q.id))

  return (
    <div className="flex flex-col h-full">
      {/* 问题列表 */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className="mb-4 text-sm text-slate-500">
          共 {totalQuestions} 个问题，已回答 {answeredCount} 个
          {resolvedQuestionIds.size > 0 && (
            <span className="ml-2 text-green-600">（AI 已解决 {resolvedQuestionIds.size} 个）</span>
          )}
        </div>

        {/* AI 解决流程展示 */}
        {resolveResults && resolveResults.length > 0 && (
          <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
            <div className="text-sm font-medium text-blue-800 mb-3 flex items-center gap-2">
              <span>🤖</span>
              <span>AI Agent 执行记录</span>
            </div>
            <div className="space-y-2">
              {resolveResults.map((result, idx) => (
                <div key={result.questionId} className="text-sm">
                  <div className="flex items-start gap-2">
                    <span className={result.resolved ? "text-green-600" : "text-red-500"}>
                      {result.resolved ? "✓" : "✗"}
                    </span>
                    <div className="flex-1">
                      <div className="text-slate-700">{result.questionText}</div>
                      <div className="text-xs text-slate-500 mt-1">
                        查询 <span className="font-mono text-blue-600">{result.dataSource}</span>
                        ，扫描 {result.rowsScanned?.toLocaleString()} 条数据
                        {result.resolved && <span className="ml-2 text-green-600">→ 已解决</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {isResolving && (
              <div className="mt-3 flex items-center gap-2 text-sm text-blue-600">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
                  <div
                    className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  ></div>
                  <div
                    className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  ></div>
                </div>
                <span>正在分析...</span>
              </div>
            )}
          </div>
        )}

        {/* 问题卡片列表 */}
        <div className="space-y-4">
          {unresolvedQuestions.map((q, index) => (
            <QuestionCard
              key={q.id}
              question={q}
              index={index + 1 + resolvedQuestionIds.size}
              answer={answers[q.id]}
              onSingleChoice={(optionId) => handleSingleChoice(q.id, optionId)}
              onMultipleChoice={(optionId) => handleMultipleChoice(q.id, optionId)}
              onTextReply={(value) => handleTextReply(q.id, value)}
            />
          ))}
        </div>

        {unresolvedQuestions.length === 0 && resolvedQuestionIds.size > 0 && (
          <div className="text-center py-8 text-slate-500">
            <div className="text-4xl mb-3">🎉</div>
            <div className="text-sm">所有问题已由 AI 自动解决</div>
          </div>
        )}
      </div>

      {/* 底部操作区 */}
      <div className="shrink-0 px-5 py-4 bg-slate-100/80 border-t border-slate-200">
        {/* 自动解决提示 */}
        {!resolveResults && (
          <div className="mb-4 p-3 bg-amber-50 rounded-lg border border-amber-100">
            <div className="text-sm text-amber-800">
              针对待确认问题，读取更多数据后，预计将自动解决
              <span className="font-semibold text-amber-900"> {autoResolvableCount} </span>
              条问题，请问是否执行？
            </div>
            <button
              onClick={handleAutoResolve}
              disabled={isResolving}
              className="mt-3 flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-600 text-white rounded-lg text-sm font-medium shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isResolving ? (
                <>
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce"></div>
                    <div
                      className="w-1.5 h-1.5 bg-white rounded-full animate-bounce"
                      style={{ animationDelay: "150ms" }}
                    ></div>
                    <div
                      className="w-1.5 h-1.5 bg-white rounded-full animate-bounce"
                      style={{ animationDelay: "300ms" }}
                    ></div>
                  </div>
                  <span>执行中...</span>
                </>
              ) : (
                <>
                  <span>⚡</span>
                  <span>执行</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* 提交按钮 */}
        <button
          onClick={handleSubmit}
          className="w-full py-3 bg-gradient-to-r from-[#5A95A8] to-[#7AB8CC] text-white rounded-lg text-sm font-medium shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5"
        >
          提交已回答的问题（{answeredCount}/{totalQuestions}）
        </button>
      </div>
    </div>
  )
}

// 问题卡片组件
function QuestionCard({
  question,
  index,
  answer,
  onSingleChoice,
  onMultipleChoice,
  onTextReply,
}: {
  question: PendingQuestion
  index: number
  answer: string | string[] | undefined
  onSingleChoice: (optionId: string) => void
  onMultipleChoice: (optionId: string) => void
  onTextReply: (value: string) => void
}) {
  return (
    <div className="p-4 bg-white rounded-lg shadow-sm border border-slate-100">
      <div className="flex items-start gap-3 mb-3">
        <span className="flex-shrink-0 w-6 h-6 bg-slate-100 rounded-full flex items-center justify-center text-xs font-medium text-slate-600">
          {index}
        </span>
        <div className="flex-1">
          <div className="text-sm font-medium text-slate-800">{question.question}</div>
          {question.description && <div className="mt-1 text-xs text-slate-500">{question.description}</div>}
        </div>
      </div>

      <div className="pl-9">
        {question.type === "single-choice" && question.options && (
          <div className="space-y-2">
            {question.options.map((option) => (
              <label key={option.id} className="flex items-center gap-2 cursor-pointer group">
                <div
                  className={`w-4 h-4 rounded-full border-2 flex items-center justify-center transition-all ${
                    answer === option.id
                      ? "border-[#5A95A8] bg-[#5A95A8]"
                      : "border-slate-300 group-hover:border-slate-400"
                  }`}
                >
                  {answer === option.id && <div className="w-1.5 h-1.5 bg-white rounded-full"></div>}
                </div>
                <span className="text-sm text-slate-700">{option.label}</span>
              </label>
            ))}
          </div>
        )}

        {question.type === "multiple-choice" && question.options && (
          <div className="space-y-2">
            {question.options.map((option) => {
              const isChecked = Array.isArray(answer) && answer.includes(option.id)
              return (
                <label
                  key={option.id}
                  className="flex items-center gap-2 cursor-pointer group"
                  onClick={() => onMultipleChoice(option.id)}
                >
                  <div
                    className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${
                      isChecked ? "border-[#5A95A8] bg-[#5A95A8]" : "border-slate-300 group-hover:border-slate-400"
                    }`}
                  >
                    {isChecked && (
                      <svg
                        className="w-3 h-3 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="3"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  <span className="text-sm text-slate-700">{option.label}</span>
                </label>
              )
            })}
          </div>
        )}

        {question.type === "text-reply" && (
          <input
            type="text"
            value={(answer as string) || ""}
            onChange={(e) => onTextReply(e.target.value)}
            placeholder={question.placeholder}
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg outline-none transition-all focus:border-[#5A95A8] focus:ring-2 focus:ring-[#5A95A8]/20"
          />
        )}
      </div>
    </div>
  )
}

// 辅助函数：模拟数据源
function getDataSourceForQuestion(questionId: string): string {
  const sources: Record<string, string> = {
    q1: "finance.revenue_records",
    q4: "analytics.user_sessions",
    q6: "finance.fiscal_calendar",
  }
  return sources[questionId] || "data.unknown_table"
}

// 辅助函数：模拟解决值
function getResolvedValueForQuestion(question: PendingQuestion): string {
  if (question.type === "single-choice" && question.options) {
    return question.options[0].id // 模拟选择第一个选项
  }
  if (question.type === "text-reply") {
    if (question.id === "q6") return "2024-12-31"
  }
  return ""
}
