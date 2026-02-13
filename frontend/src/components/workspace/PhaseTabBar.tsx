'use client'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import { Phase, phaseIndex, stageToPhase } from '@/types/pipeline'

const PHASES: { key: Phase; label: string }[] = [
  { key: 'brief', label: 'Brief' },
  { key: 'search', label: 'Search' },
  { key: 'compare', label: 'Compare' },
  { key: 'outreach', label: 'Outreach' },
  { key: 'samples', label: 'Samples' },
  { key: 'order', label: 'Order' },
]

const RUNNING_STATUSES = new Set<string>([
  'parsing',
  'clarifying',
  'discovering',
  'verifying',
  'comparing',
  'recommending',
  'outreaching',
])

export default function PhaseTabBar() {
  const { activePhase, setActivePhase, highestReachedPhase, status, projectId } = useWorkspace()

  const pipelinePhase = status ? stageToPhase(status.current_stage) : null
  const pipelineRunning = status ? RUNNING_STATUSES.has(status.status) : false

  return (
    <div className="flex gap-0 border-b border-surface-3 bg-white shrink-0 px-12">
      {PHASES.map((phase) => {
        const reached = phaseIndex(phase.key) <= phaseIndex(highestReachedPhase)
        const isActive = activePhase === phase.key
        const disabled = !projectId && phase.key !== 'brief'
        const isPipelinePhase = pipelineRunning && pipelinePhase === phase.key

        return (
          <button
            key={phase.key}
            onClick={() => !disabled && setActivePhase(phase.key)}
            disabled={disabled}
            className={`
              relative px-5 py-4 text-[11px] font-medium tracking-[0.3px] transition-all
              ${isActive
                ? 'text-ink'
                : reached
                ? 'text-ink-3 hover:text-ink-2'
                : disabled
                ? 'text-ink-4/40 cursor-not-allowed'
                : 'text-ink-4 hover:text-ink-3'
              }
            `}
          >
            <span className="flex items-center gap-2">
              {isPipelinePhase && (
                <span className="status-dot bg-teal animate-pulse-dot" />
              )}
              {phase.label}
            </span>
            {isActive && (
              <span className="absolute bottom-0 left-5 right-5 h-[1.5px] bg-teal rounded-full" />
            )}
          </button>
        )
      })}
    </div>
  )
}
