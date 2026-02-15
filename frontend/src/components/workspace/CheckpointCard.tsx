'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

import { CheckpointEvent, CheckpointResponse } from '@/types/pipeline'
import CheckpointQuestion from '@/components/workspace/CheckpointQuestion'
import WeightSliders from '@/components/workspace/WeightSliders'

interface CheckpointCardProps {
  checkpoint: CheckpointEvent
  onRespond: (response: CheckpointResponse) => Promise<boolean>
}

function parseNumeric(value: unknown): number | null {
  const asNum = Number(value)
  if (Number.isNaN(asNum)) return null
  return asNum
}

export default function CheckpointCard({ checkpoint, onRespond }: CheckpointCardProps) {
  const [secondsLeft, setSecondsLeft] = useState(checkpoint.auto_continue_seconds || 0)
  const [paused, setPaused] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [answers, setAnswers] = useState<Record<string, unknown>>({})
  const [overrides, setOverrides] = useState<Record<string, unknown>>({})
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showWeightControls = checkpoint.checkpoint_type === 'adjust_weights'
  const existingWeights = useMemo(() => {
    const raw = checkpoint.adjustable_parameters?.weights
    if (!raw || typeof raw !== 'object') return {}
    return raw as Record<string, number>
  }, [checkpoint.adjustable_parameters])

  useEffect(() => {
    setSecondsLeft(checkpoint.auto_continue_seconds || 0)
    setPaused(false)
    setSubmitting(false)
    setError(null)
    setAnswers({})
    setOverrides({})
  }, [checkpoint.checkpoint_type, checkpoint.timestamp, checkpoint.auto_continue_seconds])

  const submit = async (
    action: CheckpointResponse['action'] = 'continue',
    payloadAnswers: Record<string, unknown> = answers,
    payloadOverrides: Record<string, unknown> = overrides
  ) => {
    if (submitting) return
    setSubmitting(true)
    setError(null)
    const ok = await onRespond({
      checkpoint_type: checkpoint.checkpoint_type,
      answers: payloadAnswers,
      parameter_overrides: payloadOverrides,
      action,
    })
    if (!ok) {
      setError('Could not submit checkpoint response. Try again.')
      setSubmitting(false)
      return
    }
    setSubmitting(false)
  }

  useEffect(() => {
    if (checkpoint.requires_explicit_approval) return
    if (paused || submitting) return
    if (secondsLeft <= 0) {
      void submit('continue')
      return
    }
    timerRef.current = setTimeout(() => {
      setSecondsLeft((prev) => Math.max(0, prev - 1))
    }, 1000)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [checkpoint.requires_explicit_approval, paused, secondsLeft, submitting])

  const setConfidenceGate = (value: number) => {
    setOverrides((prev) => ({
      ...prev,
      confidence_gate_threshold: value,
    }))
  }

  const confidenceGateCurrent =
    parseNumeric(overrides.confidence_gate_threshold) ??
    parseNumeric(checkpoint.adjustable_parameters?.confidence_gate_threshold) ??
    30

  return (
    <div className="mt-3 rounded-xl border border-[#f0e7d9] bg-[#fffaf1] px-4 py-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[1.4px] text-[#9b7a3f]">Checkpoint</p>
          <p className="mt-1 text-[13px] font-medium text-ink">{checkpoint.summary}</p>
          <p className="mt-1 text-[11px] text-ink-4">{checkpoint.next_stage_preview}</p>
        </div>
        {!checkpoint.requires_explicit_approval && (
          <p className="text-[10px] text-ink-4 whitespace-nowrap">
            Auto-continuing in <span className="font-mono text-ink">{secondsLeft}s</span>
          </p>
        )}
      </div>

      {checkpoint.context_questions?.length > 0 && (
        <div className="mt-3 grid gap-2.5 md:grid-cols-2">
          {checkpoint.context_questions.map((question) => (
            <CheckpointQuestion
              key={question.field}
              question={question}
              value={answers[question.field]}
              onChange={(value) => {
                setPaused(true)
                setAnswers((prev) => ({ ...prev, [question.field]: value }))
              }}
            />
          ))}
        </div>
      )}

      {showWeightControls && (
        <div className="mt-3">
          <WeightSliders
            weights={(overrides.weights as Record<string, number>) || existingWeights}
            onChange={(weights) => {
              setPaused(true)
              setOverrides((prev) => ({ ...prev, weights }))
            }}
          />
        </div>
      )}

      {checkpoint.checkpoint_type === 'set_confidence_gate' && (
        <div className="mt-3 rounded-xl border border-surface-3 bg-white px-3 py-3">
          <p className="text-[12px] font-semibold text-ink">Confidence gate</p>
          <p className="mt-1 text-[11px] text-ink-4">
            Only compare suppliers with verification score above this threshold.
          </p>
          <div className="mt-2 flex items-center gap-3">
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={confidenceGateCurrent}
              onChange={(event) => {
                setPaused(true)
                setConfidenceGate(Number(event.target.value))
              }}
              className="w-full accent-teal"
            />
            <span className="text-[11px] font-medium text-ink-2">{Math.round(confidenceGateCurrent)}</span>
          </div>
        </div>
      )}

      {error && <p className="mt-2 text-[11px] text-red-500">{error}</p>}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => void submit('continue')}
          disabled={submitting}
          className="rounded-full bg-ink px-4 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50"
        >
          {submitting ? 'Submitting...' : 'Apply & continue'}
        </button>
        {!checkpoint.requires_explicit_approval && (
          <button
            type="button"
            onClick={() => setPaused((prev) => !prev)}
            disabled={submitting}
            className="rounded-full border border-ink/20 bg-white px-4 py-1.5 text-[12px] text-ink"
          >
            {paused ? 'Resume timer' : 'Let me adjust'}
          </button>
        )}
      </div>
    </div>
  )
}
