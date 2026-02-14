'use client'

import { useMemo } from 'react'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import { featureFlags } from '@/lib/featureFlags'
import { AnimatePresence, m } from '@/lib/motion'
import { fadeUp } from '@/lib/motion/variants'
import { DURATION, EASE_OUT_EXPO } from '@/lib/motion/config'

const STAGE_LABELS: Record<string, string> = {
  parsing: 'Understanding your brief',
  clarifying: 'Waiting on your input',
  discovering: 'Searching suppliers',
  verifying: 'Verifying supplier fit',
  comparing: 'Comparing options',
  recommending: 'Preparing recommendations',
  outreaching: 'Running outreach',
  complete: 'Ready for your review',
  failed: 'Run needs attention',
  canceled: 'Run canceled',
}

const DECISION_MILESTONES: Record<string, string> = {
  parsing: 'Shortlist quality improving',
  clarifying: 'Shortlist quality improving',
  discovering: 'Shortlist quality improving',
  verifying: 'Risk confidence established',
  comparing: 'Risk confidence established',
  recommending: 'Ready for outreach decision',
  outreaching: 'Ready for outreach decision',
  complete: 'Ready for outreach decision',
}

function fallbackMessage(stage: string): string {
  switch (stage) {
    case 'parsing':
      return 'Reading your request and building a sourcing plan.'
    case 'clarifying':
      return 'Waiting for your answers so we can continue.'
    case 'discovering':
      return 'Searching across web and supplier memory for matches.'
    case 'verifying':
      return 'Checking supplier credibility and capability.'
    case 'comparing':
      return 'Scoring suppliers on price, quality, and delivery fit.'
    case 'recommending':
      return 'Preparing a clear shortlist and next steps.'
    case 'outreaching':
      return 'Drafting and managing supplier outreach.'
    case 'complete':
      return 'Your shortlist is ready.'
    case 'failed':
      return 'This run failed. You can retry with more context.'
    case 'canceled':
      return 'This run was canceled.'
    default:
      return 'Working on your request.'
  }
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
  const { projectId, status } = useWorkspace()

  const events = status?.progress_events || []
  const latest = events.length > 0 ? events[events.length - 1] : null
  const latestDetail = latest?.detail?.trim() || ''
  const stage = status?.current_stage || 'idle'

  const recent = useMemo(() => {
    return [...events].slice(-4).reverse()
  }, [events])

  if (!projectId || !status) return null

  const title = STAGE_LABELS[stage] || 'Working'
  const message = latestDetail || fallbackMessage(stage)
  const decisionMilestone = DECISION_MILESTONES[stage] || 'Shortlist quality improving'
  const stageStartedAt = useMemo(() => {
    const stageEvents = events.filter((event) => event.stage === stage)
    const started = stageEvents.find((event) => event.substep === 'stage_started')
    return started?.timestamp || stageEvents[0]?.timestamp || latest?.timestamp || null
  }, [events, latest?.timestamp, stage])
  const stageElapsedSec = stageStartedAt ? Math.max(0, Date.now() / 1000 - stageStartedAt) : 0
  const focusCircleEnabled = featureFlags.tamkinFocusCircleSearchV1
  const showExpectation =
    focusCircleEnabled && stageElapsedSec > 45 && !['complete', 'failed', 'canceled'].includes(stage)

  return (
    <div className="mx-6 mt-6 card border border-surface-3 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold tracking-[1.5px] uppercase text-ink-4">
            {focusCircleEnabled ? 'Decision progress' : 'What Tamkin is doing now'}
          </p>
          <p className="text-[13px] font-medium text-ink mt-1">
            {focusCircleEnabled ? decisionMilestone : title}
          </p>
          {focusCircleEnabled ? (
            <p className="text-[11px] text-ink-4 mt-1">
              {title}
              {latest?.timestamp ? ` · ${formatAgo(latest.timestamp)}` : ''}
            </p>
          ) : null}
          <p className="text-[12px] text-ink-3 mt-1">{message}</p>
          {showExpectation ? (
            <p className="text-[11px] text-ink-4 mt-2">
              Still running normally. Expect a recommendation-quality update next.
            </p>
          ) : null}
        </div>
        <span className="status-dot bg-teal animate-pulse-dot mt-1 shrink-0" />
      </div>

      {recent.length > 1 && (
        <div className="mt-3 space-y-1.5 border-t border-surface-3 pt-3">
          <AnimatePresence>
            {recent.slice(1).map((event, index) => (
              <m.p
                key={`${event.stage}-${event.substep}-${event.timestamp}-${index}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: DURATION.fast, ease: EASE_OUT_EXPO }}
                className="text-[11px] text-ink-4"
              >
                {event.detail || fallbackMessage(event.stage)} · {formatAgo(event.timestamp)}
              </m.p>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}
