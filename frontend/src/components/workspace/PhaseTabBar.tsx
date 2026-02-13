'use client'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import { Phase, isPhaseAccessible, isPhaseComplete } from '@/types/pipeline'

const PHASES: { key: Phase; label: string; icon: string }[] = [
  { key: 'brief', label: 'Brief', icon: '📋' },
  { key: 'search', label: 'Search', icon: '🔍' },
  { key: 'outreach', label: 'Outreach', icon: '📧' },
  { key: 'compare', label: 'Compare', icon: '📊' },
  { key: 'samples', label: 'Samples', icon: '📦' },
  { key: 'order', label: 'Order', icon: '🛒' },
]

export default function PhaseTabBar() {
  const { activePhase, setActivePhase, highestReachedPhase, status } =
    useWorkspace()

  return (
    <div className="flex items-center gap-1">
      {PHASES.map((phase, i) => {
        const accessible = isPhaseAccessible(
          phase.key,
          highestReachedPhase,
          status
        )
        const complete = isPhaseComplete(phase.key, status)
        const isActive = activePhase === phase.key
        const isCurrentPipelinePhase =
          status &&
          !complete &&
          isActive &&
          status.status !== 'complete' &&
          status.status !== 'failed'

        return (
          <div key={phase.key} className="flex items-center">
            <button
              onClick={() => accessible && setActivePhase(phase.key)}
              disabled={!accessible}
              className={`
                flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all
                ${
                  isActive
                    ? 'bg-teal/10 text-teal border border-teal/30'
                    : complete
                    ? 'text-teal/70 hover:bg-workspace-hover'
                    : accessible
                    ? 'text-workspace-muted hover:bg-workspace-hover hover:text-workspace-text'
                    : 'text-workspace-muted/40 cursor-not-allowed'
                }
              `}
            >
              {complete ? (
                <span className="text-teal text-sm">✓</span>
              ) : isCurrentPipelinePhase ? (
                <span className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse" />
              ) : (
                <span className="text-sm">{phase.icon}</span>
              )}
              <span className="hidden lg:inline">{phase.label}</span>
            </button>

            {/* Connector line */}
            {i < PHASES.length - 1 && (
              <div
                className={`w-4 h-px mx-0.5 ${
                  complete ? 'bg-teal/40' : 'bg-workspace-border'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
