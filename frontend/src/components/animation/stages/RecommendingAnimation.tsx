'use client'

import { m, AnimatePresence } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO, SPRING_BOUNCY, STAGGER } from '@/lib/motion/config'
import { useStageProgress } from '../shared/useStageProgress'
import EventTickerOverlay from '../shared/EventTickerOverlay'
import ProgressRing from '../shared/ProgressRing'

/**
 * Recommending Animation — "Podium Reveal"
 *
 * Three podium slots at center with staggered heights.
 * Cards drop into #1, #2, #3 positions with bouncy spring physics.
 * Now data-driven: progress events control substep labels, progress ring,
 * and top pick is revealed upon completion.
 */
export default function RecommendingAnimation() {
  const {
    events,
    supplierCount,
    latestSubstep,
    latestDetail,
    progressPct,
    topPick,
    recommendationCount,
    isComplete,
  } = useStageProgress('recommending')

  const podiums = [
    { rank: 2, height: 64, delay: 0.4 },
    { rank: 1, height: 88, delay: 0.2 },
    { rank: 3, height: 48, delay: 0.6 },
  ]

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
          size={48}
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
            ? `${recommendationCount} recommendations ready`
            : latestSubstep === 'synthesizing'
              ? 'Synthesizing supplier data...'
              : latestSubstep === 'ranking'
                ? 'Ranking suppliers...'
                : latestSubstep === 'lane_assignment'
                  ? 'Assigning decision lanes...'
                  : 'Preparing your recommendations...'}
        </m.p>
      </m.div>

      {/* Podiums */}
      <div className="flex items-end justify-center gap-4 mb-8">
        {podiums.map((podium) => (
          <m.div
            key={podium.rank}
            initial={{ opacity: 0, y: 40, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{
              ...SPRING_BOUNCY,
              delay: podium.delay,
            }}
            className="flex flex-col items-center"
          >
            {/* Card placeholder */}
            <m.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                ...SPRING_BOUNCY,
                delay: podium.delay + 0.4,
              }}
              className="w-[100px] bg-surface-2 border border-surface-3 rounded-lg p-3 mb-2"
            >
              <div className="w-8 h-8 rounded-full bg-surface-3 mx-auto mb-2" />
              <div className="h-2 bg-surface-3 rounded w-full mb-1.5" />
              <div className="h-2 bg-surface-3 rounded w-3/4 mx-auto" />
            </m.div>

            {/* Podium bar */}
            <m.div
              initial={{ height: 0 }}
              animate={{ height: podium.height }}
              transition={{
                duration: DURATION.slow,
                delay: podium.delay,
                ease: EASE_OUT_EXPO,
              }}
              className={`w-[100px] rounded-t-lg flex items-start justify-center pt-2 ${
                podium.rank === 1
                  ? 'bg-teal/20 border border-teal/30'
                  : 'bg-surface-3 border border-surface-3'
              }`}
            >
              <m.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: podium.delay + 0.6 }}
                className={`text-[16px] font-bold ${
                  podium.rank === 1 ? 'text-teal' : 'text-ink-4'
                }`}
              >
                #{podium.rank}
              </m.span>
            </m.div>
          </m.div>
        ))}
      </div>

      {/* Top pick badge — shown when complete */}
      <AnimatePresence>
        {isComplete && topPick && (
          <m.div
            initial={{ opacity: 0, scale: 0.9, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: DURATION.normal, ease: EASE_OUT_EXPO }}
            className="mb-6 flex items-center gap-2 px-4 py-2 bg-teal/10 border border-teal/20 rounded-full"
          >
            <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="text-teal">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <path d="M22 4L12 14.01l-3-3" />
            </svg>
            <span className="text-[12px] font-medium text-teal">Top Pick: {topPick}</span>
          </m.div>
        )}
      </AnimatePresence>

      {/* Confidence scores animating in */}
      <m.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: DURATION.normal, delay: 1.2, ease: EASE_OUT_EXPO }}
        className="flex gap-6"
      >
        {['Confidence', 'Fit Score', 'Value'].map((label, i) => (
          <m.div
            key={label}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{
              duration: DURATION.fast,
              delay: 1.4 + i * STAGGER.slow,
              ease: EASE_OUT_EXPO,
            }}
            className="text-center"
          >
            <div className="w-10 h-1 bg-teal/30 rounded-full mx-auto mb-1">
              <m.div
                className="h-full bg-teal rounded-full"
                initial={{ width: '0%' }}
                animate={{ width: '100%' }}
                transition={{ duration: DURATION.slow, delay: 1.6 + i * 0.15, ease: EASE_OUT_EXPO }}
              />
            </div>
            <p className="text-[9px] text-ink-4 uppercase tracking-wider">{label}</p>
          </m.div>
        ))}
      </m.div>

      {/* Event ticker */}
      <m.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: DURATION.normal, delay: 1.8 }}
        className="mt-6 w-full max-w-[400px]"
      >
        <EventTickerOverlay events={events} maxVisible={3} className="text-center" />
      </m.div>

      {/* Bottom status */}
      {!isComplete && (
        <m.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: DURATION.normal, delay: 2 }}
          className="mt-3 flex items-center gap-2"
        >
          <span className="status-dot bg-teal animate-pulse-dot" />
          <p className="text-[11px] text-ink-4">Finalizing rankings...</p>
        </m.div>
      )}
    </div>
  )
}
