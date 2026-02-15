'use client'

import type { PipelineStage } from '@/types/automotive'

interface PipelineNavProps {
  stages: PipelineStage[]
  labels: Record<PipelineStage, string>
  currentStage: PipelineStage
  activeTab: PipelineStage
  onTabChange: (stage: PipelineStage) => void
  completedUpTo: number
}

export default function PipelineNav({
  stages,
  labels,
  currentStage,
  activeTab,
  onTabChange,
  completedUpTo,
}: PipelineNavProps) {
  return (
    <div className="flex gap-1 overflow-x-auto pb-2">
      {stages.map((stage, idx) => {
        const isComplete = idx < completedUpTo
        const isCurrent = stage === currentStage
        const isActive = stage === activeTab
        const isAccessible = idx <= completedUpTo

        return (
          <button
            key={stage}
            onClick={() => isAccessible && onTabChange(stage)}
            disabled={!isAccessible}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap
              ${isActive
                ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                : isComplete
                  ? 'bg-zinc-800/50 text-zinc-300 hover:bg-zinc-800 border border-transparent'
                  : isCurrent
                    ? 'bg-zinc-800 text-zinc-200 border border-zinc-700'
                    : 'text-zinc-600 border border-transparent cursor-not-allowed'
              }
            `}
          >
            {/* Step indicator */}
            <span className={`
              w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold
              ${isComplete
                ? 'bg-emerald-500/20 text-emerald-400'
                : isCurrent
                  ? 'bg-amber-500/20 text-amber-400'
                  : 'bg-zinc-800 text-zinc-600'
              }
            `}>
              {isComplete ? '✓' : idx + 1}
            </span>
            {labels[stage]}
          </button>
        )
      })}
    </div>
  )
}
