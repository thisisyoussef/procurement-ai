'use client'

import { m, AnimatePresence } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO, SPRING_GENTLE, STAGGER } from '@/lib/motion/config'
import { useStageProgress } from '../shared/useStageProgress'
import EventTickerOverlay from '../shared/EventTickerOverlay'
import ProgressRing from '../shared/ProgressRing'

/**
 * Comparing Animation — "Weighing Scales"
 *
 * Shows supplier card silhouettes with animated comparison bars
 * oscillating between them. Now data-driven: progress events control
 * the substep labels, progress ring, and winner badges at completion.
 */
export default function ComparingAnimation() {
  const {
    events,
    supplierCount,
    latestSubstep,
    latestDetail,
    progressPct,
    bestValue,
    bestQuality,
    isComplete,
  } = useStageProgress('comparing')
  const displayCount = Math.min(supplierCount || 4, 4)

  // Comparison criteria
  const criteria = ['Price', 'Quality', 'Delivery', 'Reliability']

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-4">
      {/* Progress ring + substep label */}
      <m.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: DURATION.normal, ease: EASE_OUT_EXPO }}
        className="flex flex-col items-center mb-6"
      >
        <ProgressRing
          progress={progressPct ?? (isComplete ? 100 : 10)}
          size={56}
          strokeWidth={3}
        />
        <m.p
          key={latestSubstep || 'default'}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: DURATION.fast }}
          className="text-[13px] text-ink-3 mt-3"
        >
          {isComplete
            ? 'Comparison complete'
            : latestSubstep === 'relevance_gate'
              ? 'Filtering for relevance...'
              : latestSubstep === 'building_profiles'
                ? 'Building supplier profiles...'
                : latestSubstep === 'scoring'
                  ? 'Scoring suppliers...'
                  : latestSubstep === 'parsing_scores'
                    ? 'Applying sanity checks...'
                    : 'Comparing suppliers across key criteria...'}
        </m.p>
      </m.div>

      {/* Supplier columns with animated bars */}
      <div className="w-full max-w-[440px] space-y-5">
        {criteria.map((criterion, ci) => (
          <m.div
            key={criterion}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              duration: DURATION.normal,
              delay: ci * STAGGER.slow,
              ease: EASE_OUT_EXPO,
            }}
          >
            <p className="text-[10px] font-semibold tracking-[1px] uppercase text-ink-4 mb-2">
              {criterion}
            </p>
            <div className="space-y-1.5">
              {Array.from({ length: displayCount }).map((_, si) => {
                // Deterministic but varied widths based on criterion + supplier index
                const baseWidth = 45 + ((ci * 17 + si * 23) % 45)
                return (
                  <div key={si} className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-surface-3 shrink-0" />
                    <div className="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
                      <m.div
                        className="h-full rounded-full bg-teal"
                        initial={{ width: '0%' }}
                        animate={{ width: `${baseWidth}%` }}
                        transition={{
                          ...SPRING_GENTLE,
                          delay: 0.5 + ci * 0.15 + si * 0.08,
                        }}
                      />
                    </div>
                    <m.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: DURATION.fast, delay: 1 + ci * 0.15 + si * 0.08 }}
                      className="text-[10px] text-ink-3 tabular-nums w-7 text-right"
                    >
                      {baseWidth}%
                    </m.span>
                  </div>
                )
              })}
            </div>
          </m.div>
        ))}
      </div>

      {/* Winner badges — shown after completion */}
      <AnimatePresence>
        {isComplete && (bestValue || bestQuality) && (
          <m.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: DURATION.normal, delay: 0.3, ease: EASE_OUT_EXPO }}
            className="mt-6 flex flex-wrap justify-center gap-3"
          >
            {bestValue && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="text-emerald-500">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                </svg>
                <span className="text-[11px] font-medium text-emerald-600">Best Value: {bestValue}</span>
              </div>
            )}
            {bestQuality && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-full">
                <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="text-blue-500">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                </svg>
                <span className="text-[11px] font-medium text-blue-600">Best Quality: {bestQuality}</span>
              </div>
            )}
          </m.div>
        )}
      </AnimatePresence>

      {/* Event ticker + scanning indicator */}
      <m.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: DURATION.normal, delay: 1.5 }}
        className="mt-6 w-full max-w-[400px]"
      >
        <EventTickerOverlay events={events} maxVisible={3} className="text-center" />
      </m.div>

      {!isComplete && (
        <m.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: DURATION.normal, delay: 2 }}
          className="mt-3 flex items-center gap-2"
        >
          <span className="status-dot bg-teal animate-pulse-dot" />
          <p className="text-[11px] text-ink-4">Analyzing trade-offs...</p>
        </m.div>
      )}
    </div>
  )
}
