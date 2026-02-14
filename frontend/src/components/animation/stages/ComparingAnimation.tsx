'use client'

import { m } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO, SPRING_GENTLE, STAGGER } from '@/lib/motion/config'
import { useStageProgress } from '../shared/useStageProgress'

/**
 * Comparing Animation — "Weighing Scales"
 *
 * Shows supplier card silhouettes with animated comparison bars
 * oscillating between them. No granular progress events for this stage,
 * so the animation is purely visual.
 */
export default function ComparingAnimation() {
  const { supplierCount } = useStageProgress('comparing')
  const displayCount = Math.min(supplierCount || 4, 4)

  // Simulated comparison criteria
  const criteria = ['Price', 'Quality', 'Delivery', 'Reliability']

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-4">
      {/* Title */}
      <m.p
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: DURATION.normal, ease: EASE_OUT_EXPO }}
        className="text-[13px] text-ink-3 mb-8"
      >
        Comparing {displayCount} suppliers across key criteria...
      </m.p>

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

      {/* Scanning indicator */}
      <m.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: DURATION.normal, delay: 1.5 }}
        className="mt-8 flex items-center gap-2"
      >
        <span className="status-dot bg-teal animate-pulse-dot" />
        <p className="text-[11px] text-ink-4">Analyzing trade-offs...</p>
      </m.div>
    </div>
  )
}
