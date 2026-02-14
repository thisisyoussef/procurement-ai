'use client'

import { useState } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import { featureFlags } from '@/lib/featureFlags'
import { trackTraceEvent } from '@/lib/telemetry'
import { m } from '@/lib/motion'
import { staggerContainerFast, cardEntrance } from '@/lib/motion/variants'

const SUGGESTIONS = [
  'Custom enamel pins for my streetwear brand',
  'Organic cotton tote bags, 500 units',
  'Biodegradable food packaging, small batch',
  'Hand-poured soy candles with custom labels',
]

export default function BriefPhase() {
  const {
    projectId,
    status,
    loading,
    errorMessage,
    handleSearch,
    restartCurrentProject,
    handleClarifyingAnswered,
  } = useWorkspace()

  const [input, setInput] = useState('')
  const [restartContext, setRestartContext] = useState('')
  const [restarting, setRestarting] = useState(false)
  const currentStage = status?.current_stage || 'idle'
  const isClarifying = currentStage === 'clarifying'
  const hasClarifyingQuestions = !!(
    status?.clarifying_questions && status.clarifying_questions.length > 0
  )
  const parsed = status?.parsed_requirements

  const onSubmit = (text: string) => {
    if (!text.trim()) return
    handleSearch(text.trim())
    setInput('')
  }

  const onRestartWithContext = async () => {
    const context = restartContext.trim()
    if (!projectId || !context || restarting) return
    setRestarting(true)
    const ok = await restartCurrentProject({
      fromStage: 'parsing',
      additionalContext: context,
    })
    if (ok) setRestartContext('')
    setRestarting(false)
  }

  // ─── State 1: Empty — no project yet ─────────────────
  if (!projectId && !loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-6">
        <h1 className="font-heading text-4xl text-ink text-center mb-3">
          What do you need <em className="text-teal">made</em>?
        </h1>
        <p className="text-[14px] text-ink-3 text-center max-w-lg mb-8">
          Describe your product. Tamkin will find suppliers, verify them,
          compare options, and recommend the best path forward.
        </p>

        {/* Input area */}
        <div className="w-full max-w-xl">
          <div className="card p-1.5">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  onSubmit(input)
                }
              }}
              placeholder="Describe what you want manufactured..."
              rows={3}
              className="w-full resize-none bg-transparent px-4 py-3 text-[14px] text-ink
                         placeholder:text-ink-4 focus:outline-none"
            />
            <div className="flex justify-end px-2 pb-2">
              <m.button
                onClick={() => onSubmit(input)}
                disabled={!input.trim() || loading}
                whileTap={{ scale: 0.97 }}
                className="px-5 py-2 bg-teal text-white rounded-lg text-[13px] font-medium
                           hover:bg-teal-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Start sourcing
              </m.button>
            </div>
          </div>

          {/* Suggestion chips */}
          <m.div
            className="flex flex-wrap gap-2 mt-4 justify-center"
            variants={staggerContainerFast}
            initial="hidden"
            animate="visible"
          >
            {SUGGESTIONS.map((s) => (
              <m.button
                key={s}
                variants={cardEntrance}
                onClick={() => onSubmit(s)}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.97 }}
                className="text-[11px] px-3 py-1.5 rounded-full border border-surface-3
                           text-ink-4 hover:border-teal hover:text-teal transition-colors"
              >
                {s}
              </m.button>
            ))}
          </m.div>
        </div>

        {/* Error */}
        {errorMessage && (
          <div className="mt-6 card border-l-[3px] border-l-red-400 px-5 py-4 max-w-xl w-full">
            <p className="text-[13px] font-semibold text-ink-2">Error</p>
            <p className="text-[11px] text-ink-3 mt-1">{errorMessage}</p>
          </div>
        )}
      </div>
    )
  }

  // ─── State 2: Parsing / waiting ──────────────────────
  if (loading && !parsed && !isClarifying) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] px-6">
        <span className="status-dot bg-teal animate-pulse-dot mb-4" style={{ width: 10, height: 10 }} />
        <p className="text-[14px] text-ink-2 font-medium">
          {currentStage === 'parsing'
            ? 'Analyzing your requirements...'
            : currentStage === 'discovering'
            ? 'Brief parsed. Searching for suppliers...'
            : 'Processing...'}
        </p>
        {status?.progress_events && status.progress_events.length > 0 && (
          <p className="mt-3 text-[12px] text-ink-4">
            {status.progress_events[status.progress_events.length - 1]?.detail}
          </p>
        )}
      </div>
    )
  }

  // ─── State 3: Parsed + optional clarifying questions ──
  return (
    <div className="max-w-2xl mx-auto px-6 py-10 space-y-6">
      {/* Error */}
      {errorMessage && (
        <div className="card border-l-[3px] border-l-red-400 px-5 py-4">
          <p className="text-[13px] font-semibold text-ink-2">Error</p>
          <p className="text-[11px] text-ink-3 mt-1">{errorMessage}</p>
        </div>
      )}

      {/* Clarifying Questions */}
      {isClarifying && hasClarifyingQuestions && projectId && (
        <ClarifyingQuestionsInline
          questions={status!.clarifying_questions!}
          projectId={projectId}
          onAnswered={handleClarifyingAnswered}
        />
      )}

      {/* Parsed Requirements */}
      {parsed && (
        <div className="card p-6">
          <h2 className="font-heading text-lg text-ink mb-4">Parsed Brief</h2>
          <div className="space-y-3">
            {Object.entries(parsed).map(([key, value]) => {
              if (!value || (Array.isArray(value) && value.length === 0)) return null
              const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
              return (
                <div key={key} className="flex items-start gap-4">
                  <span className="text-[11px] text-ink-4 w-32 shrink-0 pt-0.5 text-right">{label}</span>
                  <span className="text-[13px] text-ink-2">
                    {Array.isArray(value) ? value.join(', ') : String(value)}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {projectId && (
        <div className="card p-6 space-y-3">
          <div>
            <h3 className="font-heading text-base text-ink">Add context and restart</h3>
            <p className="text-[11px] text-ink-4 mt-1">
              Add missing details and rerun from the brief without creating a new project.
            </p>
          </div>
          <textarea
            value={restartContext}
            onChange={(e) => setRestartContext(e.target.value)}
            rows={3}
            placeholder="Example: prioritize suppliers with in-house embroidery and sample lead times under 10 days."
            className="w-full resize-none bg-cream/50 border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink placeholder:text-ink-4 focus:outline-none focus:ring-1 focus:ring-teal/30 focus:border-teal/50"
          />
          <div className="flex items-center gap-2">
            <button
              onClick={() => void onRestartWithContext()}
              disabled={!restartContext.trim() || restarting}
              className="px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {restarting ? 'Restarting…' : 'Restart with this context'}
            </button>
            <span className="text-[10px] text-ink-4">
              Tamkin will run parsing and supplier search again.
            </span>
          </div>
        </div>
      )}

      {/* Pipeline error */}
      {status?.error && (
        <div className="card border-l-[3px] border-l-red-400 px-5 py-4">
          <p className="text-[13px] font-semibold text-ink-2">Pipeline Error</p>
          <p className="text-[11px] text-ink-3 mt-1">{status.error}</p>
        </div>
      )}
    </div>
  )
}

// ─── Inline Clarifying Questions Component ──────────────

function ClarifyingQuestionsInline({
  questions,
  projectId,
  onAnswered,
}: {
  questions: {
    field: string
    question: string
    importance: string
    suggestions: string[]
    why_this_question?: string | null
    if_skipped_impact?: string | null
    suggested_default?: string | null
  }[]
  projectId: string
  onAnswered: () => void
}) {
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const { authFetch } = await import('@/lib/auth')
      await authFetch(`${API_BASE}/api/v1/projects/${projectId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers }),
      })
      onAnswered()
    } catch (err) {
      console.error('Clarify error:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const applySuggestedDefault = (question: {
    field: string
    suggested_default?: string | null
  }) => {
    const value = question.suggested_default?.trim()
    if (!value) return
    setAnswers((prev) => ({ ...prev, [question.field]: value }))
    trackTraceEvent(
      'clarification_default_applied',
      { project_id: projectId, field: question.field, source: 'brief_phase_inline' },
      { projectId }
    )
  }

  return (
    <div className="card p-6">
      <h2 className="font-heading text-lg text-ink mb-1">A few quick questions</h2>
      <p className="text-[12px] text-ink-4 mb-5">Help us refine your brief for better results.</p>

      <div className="space-y-5">
        {questions.map((q) => (
          <div key={q.field}>
            <label className="text-[13px] text-ink-2 font-medium block mb-2">{q.question}</label>
            {featureFlags.tamkinFocusCircleSearchV1 &&
            (q.why_this_question || q.if_skipped_impact || q.suggested_default) && (
              <div className="mb-2 space-y-1 rounded-lg border border-surface-3 bg-cream/40 px-3 py-2">
                {q.why_this_question ? (
                  <p className="text-[11px] text-ink-3">
                    <span className="font-medium text-ink-2">Why this matters:</span>{' '}
                    {q.why_this_question}
                  </p>
                ) : null}
                {q.if_skipped_impact ? (
                  <p className="text-[11px] text-ink-3">
                    <span className="font-medium text-ink-2">If skipped:</span>{' '}
                    {q.if_skipped_impact}
                  </p>
                ) : null}
                {q.suggested_default ? (
                  <button
                    onClick={() => applySuggestedDefault(q)}
                    className="text-[11px] font-medium text-teal hover:text-teal-600 transition-colors"
                  >
                    Use suggested default: {q.suggested_default}
                  </button>
                ) : null}
              </div>
            )}
            {q.suggestions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {q.suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => setAnswers((prev) => ({ ...prev, [q.field]: s }))}
                    className={`text-[10px] px-2.5 py-1 rounded-full border transition-colors ${
                      answers[q.field] === s
                        ? 'border-teal bg-teal/5 text-teal'
                        : 'border-surface-3 text-ink-4 hover:border-teal hover:text-teal'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            <input
              type="text"
              value={answers[q.field] || ''}
              onChange={(e) => setAnswers((prev) => ({ ...prev, [q.field]: e.target.value }))}
              placeholder="Type your answer..."
              className="w-full border border-surface-3 rounded-lg px-3 py-2 text-[13px] text-ink
                         placeholder:text-ink-4 focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none bg-cream/50"
            />
          </div>
        ))}
      </div>

      <button
        onClick={handleSubmit}
        disabled={submitting}
        className="mt-5 px-5 py-2.5 bg-teal text-white rounded-lg text-[13px] font-medium
                   hover:bg-teal-600 disabled:opacity-30 transition-colors"
      >
        {submitting ? 'Submitting...' : 'Continue'}
      </button>
      {featureFlags.tamkinFocusCircleSearchV1 ? (
        <p className="mt-2 text-[10px] text-ink-4">
          You can leave answers blank and continue, but recommendations may be less tailored.
        </p>
      ) : null}
    </div>
  )
}
