'use client'

import { Fragment, useMemo, useState } from 'react'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import { featureFlags } from '@/lib/featureFlags'
import { AnimatePresence, m } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO } from '@/lib/motion/config'

/* ────────────────────────────────────────────────────────
 * LiveProgressFeed — upgraded with narrative + stage bar.
 *
 * Shows:
 *  1. Stage progress bar (5 segments)
 *  2. Current narrative (what the agent is finding)
 *  3. Recent log events (collapsed)
 *  4. Retry button on failure
 * ──────────────────────────────────────────────────────── */

const PIPELINE_STAGES = [
  { key: 'parsing', label: 'Brief' },
  { key: 'discovering', label: 'Search' },
  { key: 'verifying', label: 'Verify' },
  { key: 'comparing', label: 'Compare' },
  { key: 'recommending', label: 'Recommend' },
] as const

const STAGE_ORDER = PIPELINE_STAGES.map((s) => s.key)

function stageIndex(stage: string): number {
  const idx = STAGE_ORDER.indexOf(stage as (typeof STAGE_ORDER)[number])
  // Map sub-states to their parent
  if (stage === 'clarifying' || stage === 'steering') return 0
  if (stage === 'outreaching' || stage === 'complete') return 4
  return idx >= 0 ? idx : -1
}

const STAGE_NARRATIVES: Record<string, string> = {
  parsing: 'Reading your request and building a sourcing plan.',
  clarifying: 'Waiting for your answers so I can continue.',
  steering: 'Paused for your input — I\u2019ll continue automatically.',
  discovering: 'Searching across multiple databases for supplier matches.',
  verifying: 'Checking each supplier\u2019s credibility and capability.',
  comparing: 'Scoring suppliers on price, quality, and delivery fit.',
  recommending: 'Preparing a clear shortlist with my reasoning.',
  outreaching: 'Drafting and sending supplier outreach on your behalf.',
  complete: 'All done \u2014 your shortlist is ready.',
  failed: 'Something went wrong during this run.',
  canceled: 'This run was canceled.',
}

const DECISION_MILESTONES: Record<string, string> = {
  parsing: 'Shortlist quality improving',
  clarifying: 'Shortlist quality improving',
  steering: 'Shortlist quality improving',
  discovering: 'Shortlist quality improving',
  verifying: 'Risk confidence established',
  comparing: 'Risk confidence established',
  recommending: 'Ready for outreach decision',
  outreaching: 'Ready for outreach decision',
  complete: 'Ready for outreach decision',
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

export default function LiveProgressFeed() {
  const { projectId, status, restartCurrentProject } = useWorkspace()
  const [restarting, setRestarting] = useState(false)
  const [showLog, setShowLog] = useState(false)

  const events = status?.progress_events || []
  const latest = events.length > 0 ? events[events.length - 1] : null
  const latestDetail = latest?.detail?.trim() || ''
  const stage = status?.current_stage || 'idle'
  const isTerminal = ['complete', 'failed', 'canceled'].includes(stage)

  // Find narrative events (agent-generated summaries) for richer display
  const narrativeEvents = useMemo(() => {
    return events.filter(
      (e) => e.substep === 'narrative_update' || e.substep === 'stage_summary'
    )
  }, [events])

  const latestNarrative =
    narrativeEvents.length > 0 ? narrativeEvents[narrativeEvents.length - 1].detail : null

  const recent = useMemo(() => {
    return [...events].slice(-5).reverse()
  }, [events])

  const stageStartedAt = useMemo(() => {
    const stageEvents = events.filter((event) => event.stage === stage)
    const started = stageEvents.find((event) => event.substep === 'stage_started')
    return started?.timestamp || stageEvents[0]?.timestamp || latest?.timestamp || null
  }, [events, latest?.timestamp, stage])

  const currentStageIdx = stageIndex(stage)
  const focusCircleEnabled = featureFlags.tamkinFocusCircleSearchV1
  const stageElapsedSec = stageStartedAt
    ? Math.max(0, Date.now() / 1000 - stageStartedAt)
    : 0
  const showExpectation = focusCircleEnabled && stageElapsedSec > 45 && !isTerminal

  if (!projectId || !status) return null

  const errorMessage = stage === 'failed' && status?.error ? status.error : null
  const decisionMilestone = DECISION_MILESTONES[stage] || 'Shortlist quality improving'

  // Primary display text: prefer narrative, fall back to latest event, then static text
  const primaryText =
    latestNarrative || latestDetail || STAGE_NARRATIVES[stage] || 'Working on your request.'
  const displayText = errorMessage || primaryText

  return (
    <div className="mx-6 mt-6 card border border-surface-3 px-4 py-3">
      {/* ── Stage progress bar ──────────────────── */}
      <div className="flex items-center gap-1 mb-3">
        {PIPELINE_STAGES.map((s, i) => {
          const completed = currentStageIdx > i
          const active = currentStageIdx === i && !isTerminal
          const failed = stage === 'failed' && currentStageIdx === i

          return (
            <Fragment key={s.key}>
              <div className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={`h-[3px] w-full rounded-full transition-colors duration-500 ${
                    failed
                      ? 'bg-red-400'
                      : completed || stage === 'complete'
                        ? 'bg-teal'
                        : active
                          ? 'bg-teal/50'
                          : 'bg-surface-3'
                  }`}
                >
                  {active && !isTerminal && (
                    <m.div
                      className="h-full bg-teal rounded-full"
                      initial={{ width: '30%' }}
                      animate={{ width: '80%' }}
                      transition={{ duration: 20, ease: 'linear' }}
                    />
                  )}
                </div>
                <span
                  className={`text-[9px] transition-colors ${
                    completed || active || stage === 'complete'
                      ? 'text-ink-3 font-medium'
                      : 'text-ink-4/50'
                  }`}
                >
                  {s.label}
                </span>
              </div>
            </Fragment>
          )
        })}
      </div>

      {/* ── Main content ────────────────────────── */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {focusCircleEnabled ? (
            <>
              <p className="text-[10px] font-semibold tracking-[1.5px] uppercase text-ink-4">
                Decision progress
              </p>
              <p className="text-[13px] font-medium text-ink mt-1">{decisionMilestone}</p>
              <p className="text-[11px] text-ink-4 mt-0.5">
                {(STAGE_NARRATIVES[stage] || 'Working').split('.')[0]}
                {latest?.timestamp ? ` \u00b7 ${formatAgo(latest.timestamp)}` : ''}
              </p>
            </>
          ) : (
            <p className="text-[10px] font-semibold tracking-[1.5px] uppercase text-ink-4">
              {isTerminal ? 'Status' : "What I'm doing now"}
            </p>
          )}

          <p className="text-[12px] text-ink-2 mt-1.5 leading-relaxed">{displayText}</p>

          {showExpectation && (
            <p className="text-[11px] text-ink-4 mt-2">
              Still running normally. Expect a recommendation-quality update next.
            </p>
          )}

          {stage === 'failed' && (
            <button
              disabled={restarting}
              onClick={async () => {
                setRestarting(true)
                try {
                  await restartCurrentProject()
                } finally {
                  setRestarting(false)
                }
              }}
              className="mt-2 text-[12px] font-medium text-teal hover:text-teal/80 transition-colors disabled:opacity-50"
            >
              {restarting ? 'Restarting\u2026' : 'Retry this run'}
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {!isTerminal && <span className="status-dot bg-teal animate-pulse-dot" />}
          {stage === 'failed' && <span className="status-dot bg-red-400" />}
        </div>
      </div>

      {/* ── Recent events log (collapsible) ──────── */}
      {recent.length > 1 && (
        <div className="mt-3 border-t border-surface-3 pt-2">
          <button
            onClick={() => setShowLog(!showLog)}
            className="text-[10px] text-ink-4 hover:text-ink-3 transition-colors"
          >
            {showLog ? 'Hide activity log' : `Show activity log (${recent.length})`}
          </button>

          {showLog && (
            <div className="mt-2 space-y-1.5">
              <AnimatePresence>
                {recent.map((event, index) => (
                  <m.p
                    key={`${event.stage}-${event.substep}-${event.timestamp}-${index}`}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: DURATION.fast, ease: EASE_OUT_EXPO }}
                    className="text-[11px] text-ink-4"
                  >
                    {event.detail || STAGE_NARRATIVES[event.stage] || 'Working...'} \u00b7{' '}
                    {formatAgo(event.timestamp)}
                  </m.p>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
