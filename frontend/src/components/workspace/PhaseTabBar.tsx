'use client'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import { Phase, isPhaseAccessible, isPhaseComplete } from '@/types/pipeline'

const PHASES: { key: Phase; label: string }[] = [
  { key: 'brief', label: 'Brief' },
  { key: 'search', label: 'Search' },
  { key: 'outreach', label: 'Outreach' },
  { key: 'compare', label: 'Compare' },
  { key: 'samples', label: 'Samples' },
  { key: 'order', label: 'Order' },
]

export default function PhaseTabBar() {
  const { activePhase, setActivePhase, highestReachedPhase, status } = useWorkspace()

  return (
    <div className="flex gap-0 border-b border-surface-3 bg-white shrink-0 px-12">
      {PHASES.map((phase) => {
        const accessible = isPhaseAccessible(phase.key, highestReachedPhase, status)
        const complete = isPhaseComplete(phase.key, status)
        const isActive = activePhase === phase.key
        const isPipelinePhase =
          status && !complete && isActive && status.status !== 'complete' && status.status !== 'failed'

        return (
          <button
            key={phase.key}
            onClick={() => accessible && setActivePhase(phase.key)}
            disabled={!accessible}
            className={`
              relative px-5 py-4 text-[11px] font-medium tracking-[0.3px] transition-all
              ${isActive
                ? 'text-ink'
                : complete
                ? 'text-ink-3 hover:text-ink-2'
                : accessible
                ? 'text-ink-4 hover:text-ink-3'
                : 'text-ink-4/40 cursor-not-allowed'
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
