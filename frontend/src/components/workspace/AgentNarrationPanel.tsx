'use client'

import { useMemo, useState } from 'react'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import { CheckpointResponse, ProgressEvent } from '@/types/pipeline'
import CheckpointCard from '@/components/workspace/CheckpointCard'
import ErrorRecoveryCard from '@/components/workspace/ErrorRecoveryCard'

const STAGE_FLOW = [
  { key: 'parsing', label: 'Parse' },
  { key: 'discovering', label: 'Discover' },
  { key: 'verifying', label: 'Verify' },
  { key: 'comparing', label: 'Compare' },
  { key: 'recommending', label: 'Recommend' },
] as const

const STAGE_FALLBACKS: Record<string, string> = {
  parsing: 'I am understanding your request and extracting constraints.',
  clarifying: 'I need a few details before discovery starts.',
  steering: 'Checkpoint ready. I can continue with defaults, or you can steer this step.',
  discovering: 'I am searching across multiple sources and deduplicating candidates.',
  verifying: 'I am verifying supplier credibility, contactability, and fit.',
  comparing: 'I am comparing viable suppliers across cost, quality, and speed.',
  recommending: 'I am preparing a recommendation with decision lanes and caveats.',
  complete: 'Your shortlist is ready for review and outreach approval.',
  failed: 'The run stopped unexpectedly.',
  canceled: 'This run was canceled.',
}

function stageIndex(stage: string): number {
  if (stage === 'clarifying' || stage === 'steering') return 0
  if (stage === 'outreaching' || stage === 'complete') return STAGE_FLOW.length - 1
  const idx = STAGE_FLOW.findIndex((item) => item.key === stage)
  return idx >= 0 ? idx : 0
}

function formatAgo(timestamp?: number): string {
  if (!timestamp) return 'now'
  const diffMs = Math.max(0, Date.now() - timestamp * 1000)
  const seconds = Math.floor(diffMs / 1000)
  if (seconds < 30) return 'now'
  const mins = Math.floor(seconds / 60)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function extractCurrentSupplier(events: ProgressEvent[]): string | null {
  const patterns = [
    /currently checking:\s*([^.\n]+)/i,
    /checking\s+([^.\n]+?)\s+for/i,
    /resolving manufacturer behind[^:]*:\s*([^.\n]+)/i,
    /verifying\s+([^.\n]+?)\s*(?:\(|$)/i,
  ]

  for (const event of [...events].reverse()) {
    const text = event.detail || ''
    for (const pattern of patterns) {
      const match = text.match(pattern)
      if (match?.[1]) return match[1].trim()
    }
  }

  return null
}

export default function AgentNarrationPanel() {
  const {
    projectId,
    status,
    restartCurrentProject,
    setActivePhase,
    respondToCheckpoint,
  } = useWorkspace()
  const [showEarlier, setShowEarlier] = useState(false)
  const [retrying, setRetrying] = useState(false)

  if (!projectId || !status) return null

  const stage = status.current_stage || 'parsing'
  const events = status.progress_events || []
  const latestEvent = events.length > 0 ? events[events.length - 1] : null
  const activeCheckpoint = status.active_checkpoint || null
  const isTerminal = ['complete', 'failed', 'canceled'].includes(stage)

  const narrativeEvents = events.filter(
    (event) =>
      event.narrative === true ||
      event.substep === 'narrative_update' ||
      event.substep === 'stage_summary'
  )

  const stageNarrative = useMemo(() => {
    const recentNarrative = narrativeEvents[narrativeEvents.length - 1]?.detail
    if (recentNarrative) return recentNarrative
    if (stage === 'discovering' && status.discovery_results?.discovery_briefing) {
      return status.discovery_results.discovery_briefing
    }
    if (stage === 'recommending' && status.recommendation?.executive_summary) {
      return status.recommendation.executive_summary
    }
    return latestEvent?.detail || STAGE_FALLBACKS[stage] || 'Working on your project.'
  }, [
    latestEvent?.detail,
    narrativeEvents,
    stage,
    status.discovery_results?.discovery_briefing,
    status.recommendation?.executive_summary,
  ])

  const currentActivity = useMemo(() => {
    const nonNarrative = [...events]
      .reverse()
      .find((event) => !(event.narrative || event.substep === 'narrative_update' || event.substep === 'stage_summary'))
    return nonNarrative?.detail || null
  }, [events])

  const earlierEvents = useMemo(() => {
    return [...events].slice(-10).reverse()
  }, [events])

  const currentSupplier = useMemo(() => extractCurrentSupplier(events), [events])
  const currentStageIndex = stageIndex(stage)

  const retryFromStage = stage === 'failed' && (status.error || '').toLowerCase().includes('parsing')
    ? 'parsing'
    : 'discovering'

  const handleRetry = async () => {
    setRetrying(true)
    try {
      await restartCurrentProject({ fromStage: retryFromStage as 'parsing' | 'discovering' })
    } finally {
      setRetrying(false)
    }
  }

  const handleCheckpointResponse = async (response: CheckpointResponse): Promise<boolean> => {
    return respondToCheckpoint(response)
  }

  return (
    <div className="mx-6 mt-6 card border border-surface-3 px-5 py-4">
      <p className="text-[10px] font-semibold uppercase tracking-[1.5px] text-ink-4">Agent activity</p>

      <div className="mt-2 flex items-center gap-1.5">
        {STAGE_FLOW.map((item, idx) => {
          const done = idx < currentStageIndex || stage === 'complete'
          const active = idx === currentStageIndex && !isTerminal
          return (
            <div key={item.key} className="flex flex-1 items-center gap-1.5">
              <div
                className={`h-[4px] flex-1 rounded-full transition-colors ${
                  done ? 'bg-teal' : active ? 'bg-teal/50' : 'bg-surface-3'
                }`}
              />
              <span
                className={`text-[9px] ${
                  done || active ? 'text-ink-3' : 'text-ink-4/60'
                }`}
              >
                {item.label}
              </span>
            </div>
          )
        })}
      </div>

      <p className="mt-3 text-[14px] text-ink-2 leading-relaxed">{stageNarrative}</p>

      {currentSupplier && (
        <p className="mt-2 text-[11px] text-ink-4">
          Currently checking: <span className="text-ink-3 font-medium">{currentSupplier}</span>
        </p>
      )}

      {!currentSupplier && currentActivity && currentActivity !== stageNarrative && (
        <p className="mt-2 text-[11px] text-ink-4">{currentActivity}</p>
      )}

      {activeCheckpoint && (
        <CheckpointCard checkpoint={activeCheckpoint} onRespond={handleCheckpointResponse} />
      )}

      {stage === 'failed' && status.error && (
        <div className="mt-3">
          <ErrorRecoveryCard
            error={status.error}
            stage={stage}
            retrying={retrying}
            onRetry={handleRetry}
            onEditBrief={() => setActivePhase('brief')}
          />
        </div>
      )}

      {earlierEvents.length > 1 && (
        <div className="mt-3 border-t border-surface-3 pt-2">
          <button
            type="button"
            onClick={() => setShowEarlier((prev) => !prev)}
            className="text-[10px] text-ink-4 hover:text-ink-3 transition-colors"
          >
            {showEarlier ? 'Hide activity log' : `Show activity log (${earlierEvents.length})`}
          </button>
          {showEarlier && (
            <div className="mt-2 space-y-1">
              {earlierEvents.map((event, idx) => (
                <p key={`${event.stage}:${event.substep}:${event.timestamp}:${idx}`} className="text-[11px] text-ink-4">
                  {event.detail || STAGE_FALLBACKS[event.stage] || 'Working...'} · {formatAgo(event.timestamp)}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
