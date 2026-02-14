'use client'

import { useState } from 'react'

import { authFetch } from '@/lib/auth'
import { featureFlags } from '@/lib/featureFlags'
import { trackTraceEvent } from '@/lib/telemetry'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface ClarifyingQuestion {
  field: string
  question: string
  importance: string
  suggestions: string[]
  why_this_question?: string | null
  if_skipped_impact?: string | null
  suggested_default?: string | null
}

interface ClarifyingQuestionsProps {
  projectId: string
  questions: ClarifyingQuestion[]
  onAnswered: () => void
}

const IMPORTANCE_STYLES: Record<string, { badge: string; border: string }> = {
  critical: {
    badge: 'bg-red-100 text-red-700',
    border: 'border-red-200',
  },
  recommended: {
    badge: 'bg-blue-100 text-blue-700',
    border: 'border-blue-200',
  },
  optional: {
    badge: 'bg-slate-100 text-slate-600',
    border: 'border-slate-200',
  },
}

export default function ClarifyingQuestions({
  projectId,
  questions,
  onAnswered,
}: ClarifyingQuestionsProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSuggestionClick = (field: string, suggestion: string) => {
    setAnswers((prev) => ({ ...prev, [field]: suggestion }))
  }

  const handleInputChange = (field: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [field]: value }))
  }

  const applySuggestedDefault = (question: ClarifyingQuestion) => {
    const fallback = question.suggested_default?.trim()
    if (!fallback) return
    setAnswers((prev) => ({ ...prev, [question.field]: fallback }))
    trackTraceEvent(
      'clarification_default_applied',
      { project_id: projectId, field: question.field, source: 'clarifying_questions_component' },
      { projectId }
    )
  }

  const handleSubmit = async () => {
    // Filter out empty answers
    const filledAnswers = Object.fromEntries(
      Object.entries(answers).filter(([, v]) => v.trim())
    )

    if (Object.keys(filledAnswers).length === 0) {
      // If no answers provided, skip instead
      await handleSkip()
      return
    }

    setLoading(true)
    setError(null)

    try {
      const res = await authFetch(
        `${API_BASE}/api/v1/projects/${projectId}/answer`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ answers: filledAnswers }),
        }
      )

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: 'Failed to submit answers' }))
        throw new Error(errData.detail || 'Failed to submit answers')
      }

      onAnswered()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSkip = async () => {
    setLoading(true)
    setError(null)

    try {
      const res = await authFetch(
        `${API_BASE}/api/v1/projects/${projectId}/skip-questions`,
        { method: 'POST' }
      )

      if (!res.ok) {
        throw new Error('Failed to skip questions')
      }

      onAnswered()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const answeredCount = Object.values(answers).filter((v) => v.trim()).length

  return (
    <div className="max-w-3xl mx-auto mt-6">
      <div className="bg-white border border-amber-200 rounded-xl shadow-sm overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-amber-100 bg-amber-50">
          <div className="flex items-center gap-2">
            <span className="text-lg">&#x2753;</span>
            <h2 className="text-base font-semibold text-slate-900">
              A few quick questions
            </h2>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Help us find better suppliers by answering these optional questions.
            You can skip any or all of them.
          </p>
        </div>

        {/* Questions */}
        <div className="p-6 space-y-5">
          {questions.map((q) => {
            const styles = IMPORTANCE_STYLES[q.importance] || IMPORTANCE_STYLES.optional

            return (
              <div key={q.field} className={`border ${styles.border} rounded-lg p-4`}>
                <div className="flex items-start justify-between mb-2">
                  <label className="text-sm font-medium text-slate-900 flex-1">
                    {q.question}
                  </label>
                  <span
                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full ml-2 whitespace-nowrap ${styles.badge}`}
                  >
                    {q.importance}
                  </span>
                </div>

                {featureFlags.tamkinFocusCircleSearchV1 &&
                (q.why_this_question || q.if_skipped_impact || q.suggested_default) && (
                  <div className="mb-3 space-y-1 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                    {q.why_this_question ? (
                      <p className="text-[11px] text-slate-700">
                        <span className="font-medium text-slate-900">Why this matters:</span>{' '}
                        {q.why_this_question}
                      </p>
                    ) : null}
                    {q.if_skipped_impact ? (
                      <p className="text-[11px] text-slate-700">
                        <span className="font-medium text-slate-900">If skipped:</span>{' '}
                        {q.if_skipped_impact}
                      </p>
                    ) : null}
                    {q.suggested_default ? (
                      <button
                        onClick={() => applySuggestedDefault(q)}
                        className="text-[11px] font-medium text-blue-700 hover:text-blue-800 transition-colors"
                      >
                        Use suggested default: {q.suggested_default}
                      </button>
                    ) : null}
                  </div>
                )}

                {/* Suggestion chips */}
                {q.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {q.suggestions.map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => handleSuggestionClick(q.field, suggestion)}
                        className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                          answers[q.field] === suggestion
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400 hover:text-blue-600'
                        }`}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}

                {/* Text input for custom answer */}
                <input
                  type="text"
                  value={answers[q.field] || ''}
                  onChange={(e) => handleInputChange(q.field, e.target.value)}
                  placeholder="Type a custom answer..."
                  className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm
                             text-slate-900 placeholder:text-slate-400
                             focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            )
          })}
        </div>

        {/* Error */}
        {error && (
          <div className="mx-6 mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
          <div>
            <button
              onClick={handleSkip}
              disabled={loading}
              className="text-sm text-slate-500 hover:text-slate-700 disabled:opacity-50 transition-colors"
            >
              Skip all &rarr;
            </button>
            {featureFlags.tamkinFocusCircleSearchV1 ? (
              <p className="text-[10px] text-slate-500 mt-1">
                Skipping is allowed, but recommendation confidence may be lower.
              </p>
            ) : null}
          </div>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                       hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading
              ? 'Processing...'
              : answeredCount > 0
              ? `Continue with ${answeredCount} answer${answeredCount > 1 ? 's' : ''}`
              : 'Continue without answers'}
          </button>
        </div>
      </div>
    </div>
  )
}
