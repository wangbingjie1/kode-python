"use client"

import { useState } from "react"

interface Question {
  id: number
  type: "boolean" | "multiple-choice" | "text"
  question: string
  options?: string[]
  skipped: boolean
  answer?: string | boolean
}

interface ETLQuestionnaireProps {
  onComplete: () => void
}

export function ETLQuestionnaire({ onComplete }: ETLQuestionnaireProps) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [questions, setQuestions] = useState<Question[]>([
    {
      id: 1,
      type: "boolean",
      question: "Does your dataset contain personally identifiable information (PII)?",
      skipped: false,
    },
    {
      id: 2,
      type: "multiple-choice",
      question: "What is the primary purpose of this data analysis?",
      options: ["Business Intelligence", "Machine Learning", "Compliance Reporting", "Data Exploration"],
      skipped: false,
    },
    {
      id: 3,
      type: "boolean",
      question: "Should missing values be imputed or removed?",
      skipped: false,
    },
    {
      id: 4,
      type: "multiple-choice",
      question: "What is the expected data refresh frequency?",
      options: ["Real-time", "Daily", "Weekly", "Monthly"],
      skipped: false,
    },
    {
      id: 5,
      type: "text",
      question: "Are there any specific business rules or constraints we should apply to the data?",
      skipped: false,
    },
  ])

  const [textAnswer, setTextAnswer] = useState("")
  const currentQuestion = questions[currentQuestionIndex]
  const skippedQuestions = questions.filter((q) => q.skipped)
  const isLastQuestion = currentQuestionIndex === questions.length - 1
  const allAnswered = currentQuestionIndex === questions.length

  const handleAnswer = (answer: string | boolean) => {
    const updatedQuestions = [...questions]
    updatedQuestions[currentQuestionIndex].answer = answer
    updatedQuestions[currentQuestionIndex].skipped = false
    setQuestions(updatedQuestions)
    setTextAnswer("")

    if (!isLastQuestion) {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
    } else {
      setCurrentQuestionIndex(questions.length)
    }
  }

  const handleSkip = () => {
    const updatedQuestions = [...questions]
    updatedQuestions[currentQuestionIndex].skipped = true
    setQuestions(updatedQuestions)

    if (!isLastQuestion) {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
    } else {
      setCurrentQuestionIndex(questions.length)
    }
  }

  const handleConfirm = () => {
    onComplete()
  }

  if (allAnswered) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 overflow-y-auto px-5 py-6">
          <div className="flex flex-col gap-4">
            <div className="px-3.5 py-3 rounded-lg bg-white shadow-sm">
              <div className="flex justify-between mb-1.5 text-xs text-slate-500 font-medium">
                <span>🤖 AI</span>
                <span>{new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}</span>
              </div>
              <div className="text-sm leading-relaxed text-slate-800">
                Thank you for answering the questions! I've collected all the information needed to build your ontology.
                {skippedQuestions.length > 0 && (
                  <>
                    <br />
                    <br />
                    <span className="text-amber-600">
                      Note: You skipped {skippedQuestions.length} question(s). This may affect the completeness of the
                      ontology.
                    </span>
                  </>
                )}
              </div>
            </div>

            {skippedQuestions.length > 0 && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <h5 className="text-sm font-semibold text-amber-800 mb-2">Skipped Questions</h5>
                <ul className="text-sm text-amber-700 space-y-1">
                  {skippedQuestions.map((q) => (
                    <li key={q.id} className="flex items-start gap-2">
                      <span className="text-amber-500">•</span>
                      <span>{q.question}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <div className="shrink-0 px-5 py-4 bg-slate-100/80 border-t border-slate-200">
          <div className="flex gap-3 mb-3">
            <button
              onClick={() => setCurrentQuestionIndex(0)}
              className="flex-1 px-4 py-2.5 bg-white border border-slate-300 text-slate-600 rounded-lg font-medium transition-all hover:bg-slate-50"
            >
              Review Questions
            </button>
            <button
              onClick={handleConfirm}
              className="flex-1 px-4 py-2.5 bg-[#5A95A8] text-white rounded-lg font-medium transition-all hover:bg-[#7AB8CC]"
            >
              Confirm
            </button>
          </div>
          <div className="relative flex flex-wrap items-end bg-white rounded-lg px-3 py-2.5 gap-1.5 transition-all min-h-[80px] shadow-md">
            <textarea
              disabled
              className="flex-1 min-w-[200px] min-h-[60px] bg-transparent border-0 text-slate-400 text-sm leading-normal resize-none outline-none max-h-[120px]"
              placeholder="Questions completed..."
              rows={3}
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-200 bg-white">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-800">Data Governance Questions</h3>
            <p className="text-sm text-slate-500 mt-0.5">
              Question {currentQuestionIndex + 1} of {questions.length}
            </p>
          </div>
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-sm font-semibold text-slate-600">
            {currentQuestionIndex + 1}/{questions.length}
          </div>
        </div>
        {/* Progress Bar */}
        <div className="mt-3">
          <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#5A95A8] transition-all duration-300"
              style={{ width: `${((currentQuestionIndex + 1) / questions.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Question Content */}
      <div className="flex-1 overflow-y-auto px-5 py-6">
        <div className="px-3.5 py-3 rounded-lg bg-white shadow-sm">
          <div className="flex justify-between mb-1.5 text-xs text-slate-500 font-medium">
            <span>🤖 AI</span>
            <span>{new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}</span>
          </div>
          <div className="text-sm leading-relaxed text-slate-800 font-medium mb-4">{currentQuestion.question}</div>

          {/* Boolean Question */}
          {currentQuestion.type === "boolean" && (
            <div className="flex gap-3">
              <button
                onClick={() => handleAnswer(true)}
                className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 font-medium transition-all hover:border-[#5A95A8] hover:bg-[#5A95A8]/10"
              >
                Yes
              </button>
              <button
                onClick={() => handleAnswer(false)}
                className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 font-medium transition-all hover:border-[#5A95A8] hover:bg-[#5A95A8]/10"
              >
                No
              </button>
            </div>
          )}

          {/* Multiple Choice Question */}
          {currentQuestion.type === "multiple-choice" && (
            <div className="space-y-2">
              {currentQuestion.options?.map((option, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAnswer(option)}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-left text-slate-700 font-medium transition-all hover:border-[#5A95A8] hover:bg-[#5A95A8]/10"
                >
                  {option}
                </button>
              ))}
            </div>
          )}

          {/* Text Question - shown in input area below */}
        </div>

        {/* Skipped Questions Panel */}
        {skippedQuestions.length > 0 && (
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <h5 className="text-sm font-semibold text-amber-800 mb-2">Skipped Questions ({skippedQuestions.length})</h5>
            <ul className="text-sm text-amber-700 space-y-1">
              {skippedQuestions.map((q) => (
                <li key={q.id} className="flex items-start gap-2">
                  <span className="text-amber-500">•</span>
                  <span className="line-clamp-1">{q.question}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="shrink-0 px-5 py-4 bg-slate-100/80 border-t border-slate-200">
        <div className="flex gap-3 mb-3">
          <button
            onClick={handleSkip}
            className="flex-1 px-4 py-2 bg-white border border-slate-300 text-slate-600 rounded-lg text-sm font-medium transition-all hover:bg-slate-50"
          >
            Skip
          </button>
          {currentQuestion.type === "text" && (
            <button
              onClick={() => {
                if (textAnswer.trim()) {
                  handleAnswer(textAnswer)
                }
              }}
              disabled={!textAnswer.trim()}
              className="flex-1 px-4 py-2 bg-[#5A95A8] text-white rounded-lg text-sm font-medium transition-all hover:bg-[#7AB8CC] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Submit Answer
            </button>
          )}
        </div>

        {/* Text input for open-ended questions */}
        {currentQuestion.type === "text" && (
          <div className="relative flex flex-wrap items-end bg-white rounded-lg px-3 py-2.5 gap-1.5 transition-all min-h-[80px] shadow-md focus-within:shadow-lg focus-within:ring-2 focus-within:ring-blue-400/50">
            <textarea
              value={textAnswer}
              onChange={(e) => setTextAnswer(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  if (textAnswer.trim()) {
                    handleAnswer(textAnswer)
                  }
                }
              }}
              className="flex-1 min-w-[200px] min-h-[60px] bg-transparent border-0 text-slate-800 text-sm leading-normal resize-none outline-none max-h-[120px]"
              placeholder="Type your answer here..."
              rows={3}
            />
            <button
              onClick={() => {
                if (textAnswer.trim()) {
                  handleAnswer(textAnswer)
                }
              }}
              disabled={!textAnswer.trim()}
              className="w-8 h-8 p-0 bg-[#5A95A8] rounded-md text-white text-base cursor-pointer flex items-center justify-center transition-all flex-shrink-0 hover:bg-[#7AB8CC] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              →
            </button>
          </div>
        )}

        {/* Placeholder for non-text questions */}
        {currentQuestion.type !== "text" && (
          <div className="relative flex flex-wrap items-end bg-white rounded-lg px-3 py-2.5 gap-1.5 transition-all min-h-[80px] shadow-md opacity-50">
            <textarea
              disabled
              className="flex-1 min-w-[200px] min-h-[60px] bg-transparent border-0 text-slate-400 text-sm leading-normal resize-none outline-none max-h-[120px]"
              placeholder="Select an option above to continue..."
              rows={3}
            />
          </div>
        )}
      </div>
    </div>
  )
}
