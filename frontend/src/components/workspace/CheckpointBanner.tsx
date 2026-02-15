'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { authFetch } from '@/lib/auth'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import { CheckpointEvent } from '@/types/pipeline'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

function normalizeChoice(value: string): unknown {
  if (value === 'true') return true
  if (value === 'false') return false
  const asNum = Number(value)
  if (!Number.isNaN(asNum) && value.trim() !== '') return asNum
  return value
}

export default function CheckpointBanner() {
  const { projectId, status, refreshStatus } = useWorkspace()
  const checkpoint = (status?.active_checkpoint || null) as CheckpointEvent | null

  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [paused, setPaused] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const initialSeconds = checkpoint?.auto_continue_seconds ?? 0
  const [secondsLeft, setSecondsLeft] = useState(initialSeconds)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    setAnswers({})
    setPaused(false)
    setError(null)
    setSecondsLeft(checkpoint?.auto_continue_seconds ?? 0)
  }, [checkpoint?.checkpoint_type, checkpoint?.timestamp, checkpoint?.auto_continue_seconds])

  const submitCheckpoint = useCallback(
    async (payloadAnswers: Record<string, string> = {}) => {
      if (!projectId || !checkpoint || submitting) return
      setSubmitting(true)
      setError(null)

      try {
        const normalizedAnswers: Record<string, unknown> = {}
        Object.entries(payloadAnswers).forEach(([field, value]) => {
          if (!value || !value.trim()) return
          normalizedAnswers[field] = normalizeChoice(value)
        })

        const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/checkpoint`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            checkpoint_type: checkpoint.checkpoint_type,
            answers: normalizedAnswers,
            parameter_overrides: {},
            action: 'continue',
          }),
        })

        if (!res.ok) {
          let detail = `HTTP ${res.status}`
          try {
            const body = await res.json()
            detail = body?.detail || detail
          } catch {
            // keep fallback detail
          }
          throw new Error(detail)
        }

        refreshStatus()
      } catch (err: any) {
        setError(err?.message || 'Failed to submit checkpoint response')
      } finally {
        setSubmitting(false)
      }
    },
    [checkpoint, projectId, refreshStatus, submitting]
  )

  useEffect(() => {
    if (!checkpoint || paused || submitting) return

    if (secondsLeft <= 0) {
      void submitCheckpoint(answers)
      return
    }

    intervalRef.current = setInterval(() => {
      setSecondsLeft((prev) => Math.max(0, prev - 1))
    }, 1000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [answers, checkpoint, paused, secondsLeft, submitCheckpoint, submitting])

  const answerCount = useMemo(
    () => Object.values(answers).filter((value) => value?.trim()).length,
    [answers]
  )

  if (!checkpoint) return null

  return (
    <div className="mx-6 mt-6 card border border-[#f0e7d9] bg-[#fffaf1] px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.16em] text-[#9b7a3f]">Checkpoint</p>
          <h3 className="mt-1 font-heading text-lg text-ink">{checkpoint.summary}</h3>
          <p className="mt-1 text-[12px] text-ink-3">{checkpoint.next_stage_preview}</p>
        </div>
        {!paused && checkpoint.auto_continue_seconds > 0 && (
          <div className="text-right">
            <p className="text-[11px] text-ink-4">Auto-continue in</p>
            <p className="font-mono text-xl text-ink">{secondsLeft}s</p>
          </div>
        )}
      </div>

      {checkpoint.context_questions?.length > 0 && (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {checkpoint.context_questions.map((question) => (
            <label key={question.field} className="flex flex-col gap-1 rounded-xl border border-[#f1e7d3] bg-white px-3 py-2">
              <span className="text-[12px] font-semibold text-ink">{question.question}</span>
              <span className="text-[11px] text-ink-4">{question.context}</span>
              {question.options && question.options.length > 0 ? (
                <select
                  className="mt-1 rounded-md border border-[#ead9bf] px-2 py-1 text-[12px] text-ink"
                  value={answers[question.field] ?? ''}
                  onChange={(event) =>
                    setAnswers((prev) => ({
                      ...prev,
                      [question.field]: event.target.value,
                    }))
                  }
                >
                  <option value="">No answer</option>
                  {question.options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="mt-1 rounded-md border border-[#ead9bf] px-2 py-1 text-[12px] text-ink"
                  placeholder={question.default || 'Type your answer'}
                  value={answers[question.field] ?? ''}
                  onChange={(event) =>
                    setAnswers((prev) => ({
                      ...prev,
                      [question.field]: event.target.value,
                    }))
                  }
                />
              )}
            </label>
          ))}
        </div>
      )}

      {error && <p className="mt-3 text-[12px] text-red-600">{error}</p>}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="rounded-full bg-ink px-4 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50"
          onClick={() => void submitCheckpoint(answers)}
          disabled={submitting}
        >
          {submitting ? 'Submitting...' : answerCount ? 'Apply & Continue' : 'Continue'}
        </button>
        <button
          type="button"
          className="rounded-full border border-ink/20 bg-white px-4 py-1.5 text-[12px] text-ink"
          onClick={() => setPaused((prev) => !prev)}
          disabled={submitting}
        >
          {paused ? 'Resume timer' : 'Let me adjust'}
        </button>
      </div>
    </div>
  )
}
