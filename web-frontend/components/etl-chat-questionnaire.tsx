"use client"

import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from "react"

interface Question {
  id: number
  type: "boolean" | "multiple-choice" | "text"
  question: string
  options?: string[]
}

interface ETLChatQuestionnaireProps {
  onAddMessage: (role: "user" | "assistant", content: string) => void
  onComplete: () => void
  isActive: boolean
  onGetCurrentQuestion: (question: Question | null) => void
}

const QUESTIONS: Question[] = [
  {
    id: 1,
    type: "boolean",
    question: "Does your dataset contain personally identifiable information (PII)?",
  },
  {
    id: 2,
    type: "multiple-choice",
    question: "What is the primary purpose of this data analysis?",
    options: ["Business Intelligence", "Machine Learning", "Compliance Reporting", "Data Exploration"],
  },
  {
    id: 3,
    type: "boolean",
    question: "Should missing values be imputed or removed?",
  },
  {
    id: 4,
    type: "multiple-choice",
    question: "What is the expected data refresh frequency?",
    options: ["Real-time", "Daily", "Weekly", "Monthly"],
  },
  {
    id: 5,
    type: "text",
    question: "Are there any specific business rules or constraints we should apply to the data?",
  },
]

export const ETLChatQuestionnaire = forwardRef<any, ETLChatQuestionnaireProps>(
  function ETLChatQuestionnaire({ onAddMessage, onComplete, isActive, onGetCurrentQuestion }, ref) {
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
    const [hasStarted, setHasStarted] = useState(false)
    const questionShownRef = useRef<Set<number>>(new Set())

    useEffect(() => {
      if (isActive && !hasStarted) {
        setHasStarted(true)
        setTimeout(() => {
          showQuestion(0)
        }, 500)
      }
    }, [isActive, hasStarted])

    useEffect(() => {
      if (isActive && currentQuestionIndex < QUESTIONS.length) {
        onGetCurrentQuestion(QUESTIONS[currentQuestionIndex])
      } else {
        onGetCurrentQuestion(null)
      }
    }, [currentQuestionIndex, isActive])

    const showQuestion = (index: number) => {
      if (index >= QUESTIONS.length) {
        onAddMessage("assistant", "Thank you for answering all the questions! I've collected all the information needed.")
        setTimeout(() => {
          onComplete()
        }, 1000)
        return
      }

      // 检查是否已经显示过这个问题
      if (questionShownRef.current.has(index)) {
        return
      }

      const question = QUESTIONS[index]
      questionShownRef.current.add(index)
      onAddMessage("assistant", question.question)
    }

    const handleAnswer = (answer: string) => {
      // Add user message
      onAddMessage("user", answer)
      
      // Move to next question
      const nextIndex = currentQuestionIndex + 1
      setCurrentQuestionIndex(nextIndex)
      
      setTimeout(() => {
        showQuestion(nextIndex)
      }, 500)
    }

    useImperativeHandle(ref, () => ({
      handleAnswer,
      currentQuestion: currentQuestionIndex < QUESTIONS.length ? QUESTIONS[currentQuestionIndex] : null,
    }))

    // 渲染快速交互按钮
    const currentQuestion = currentQuestionIndex < QUESTIONS.length ? QUESTIONS[currentQuestionIndex] : null

    if (!currentQuestion || !isActive) {
      return null
    }

    return (
      <div className="px-5 pb-4">
        {/* Boolean Question */}
        {currentQuestion.type === "boolean" && (
          <div className="flex gap-3">
            <button
              onClick={() => handleAnswer("Yes")}
              className="flex-1 px-4 py-3 bg-white border-2 border-slate-200 rounded-lg text-slate-700 font-medium transition-all hover:border-[#5A95A8] hover:bg-[#5A95A8]/10 shadow-sm hover:shadow-md"
            >
              Yes
            </button>
            <button
              onClick={() => handleAnswer("No")}
              className="flex-1 px-4 py-3 bg-white border-2 border-slate-200 rounded-lg text-slate-700 font-medium transition-all hover:border-[#5A95A8] hover:bg-[#5A95A8]/10 shadow-sm hover:shadow-md"
            >
              No
            </button>
          </div>
        )}

        {/* Multiple Choice Question */}
        {currentQuestion.type === "multiple-choice" && currentQuestion.options && (
          <div className="space-y-2">
            {currentQuestion.options.map((option, idx) => (
              <button
                key={idx}
                onClick={() => handleAnswer(option)}
                className="w-full px-4 py-3 bg-white border-2 border-slate-200 rounded-lg text-left text-slate-700 font-medium transition-all hover:border-[#5A95A8] hover:bg-[#5A95A8]/10 shadow-sm hover:shadow-md"
              >
                {option}
              </button>
            ))}
          </div>
        )}

        {/* Text Question - No buttons, use input box only */}
        {currentQuestion.type === "text" && null}
      </div>
    )
  }
)
