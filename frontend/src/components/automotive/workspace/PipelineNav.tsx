'use client'

import { m, AnimatePresence } from '@/lib/motion'
import type { PipelineStage } from '@/types/automotive'
import Tooltip from '@/components/automotive/shared/Tooltip'

interface PipelineNavProps {
  stages: PipelineStage[]
  labels: Record<PipelineStage, string>
  currentStage: PipelineStage
  activeTab: PipelineStage
  onTabChange: (stage: PipelineStage) => void
  completedUpTo: number
  processingStage?: PipelineStage | null
}

const STAGE_DESCRIPTIONS: Record<PipelineStage, string> = {
  parse: 'Extract structured requirements from your procurement request',
  discover: 'Search supplier databases, trade registries, and the open web',
  qualify: 'Verify certifications, financials, and corporate standing',
  compare: 'Score and rank suppliers across 6 dimensions',
  report: 'Generate detailed intelligence briefs on each supplier',
  rfq: 'Draft and send Request for Quote packages to suppliers',
  quote_ingest: 'Parse and compare incoming supplier quotes',
  complete: 'Review final recommendations and next steps',
}

export default function PipelineNav({
  stages,
  labels,
  currentStage,
  activeTab,
  onTabChange,
  completedUpTo,
  processingStage,
}: PipelineNavProps) {
  return (
    <div className="flex items-center gap-0.5 overflow-x-auto pb-2">
      {stages.map((stage, idx) => {
        const isComplete = idx < completedUpTo
        const isCurrent = stage === currentStage
        const isActive = stage === activeTab
        const isAccessible = idx <= completedUpTo
        const isProcessing = stage === processingStage

        const button = (
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
            {/* Step indicator — animated morph between number and checkmark */}
            <span className={`
              relative w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold
              ${isComplete
                ? 'bg-emerald-500/20 text-emerald-400'
                : isProcessing
                  ? 'bg-amber-500/20 text-amber-400'
                  : isCurrent
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'bg-zinc-800 text-zinc-600'
              }
            `}>
              {isProcessing && (
                <m.span
                  className="absolute inset-0 rounded-full border-2 border-amber-500/40"
                  animate={{
                    scale: [1, 1.4, 1],
                    opacity: [0.5, 0, 0.5],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                />
              )}
              <AnimatePresence mode="wait">
                {isComplete ? (
                  <m.span
                    key="check"
                    initial={{ scale: 0, rotate: -90 }}
                    animate={{ scale: 1, rotate: 0 }}
                    exit={{ scale: 0 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                  >
                    ✓
                  </m.span>
                ) : (
                  <m.span
                    key="num"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                  >
                    {idx + 1}
                  </m.span>
                )}
              </AnimatePresence>
            </span>
            {labels[stage]}
          </button>
        )

        return (
          <div key={stage} className="flex items-center">
            {/* Chevron connector */}
            {idx > 0 && (
              <span className={`mx-0.5 text-xs ${idx <= completedUpTo ? 'text-emerald-500/60' : 'text-zinc-700'}`}>
                →
              </span>
            )}
            {/* Wrap in tooltip for future/inaccessible stages */}
            {!isAccessible ? (
              <Tooltip content={STAGE_DESCRIPTIONS[stage]} side="bottom">
                {button}
              </Tooltip>
            ) : (
              button
            )}
          </div>
        )
      })}
    </div>
  )
}
