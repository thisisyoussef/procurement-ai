'use client'

import { lazy, Suspense } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import { useReducedMotion } from '@/lib/motion/useReducedMotion'
import { AnimatePresence, m } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO } from '@/lib/motion/config'

const ParsingAnimation = lazy(() => import('./stages/ParsingAnimation'))
const DiscoveryGlobe = lazy(() => import('./stages/DiscoveryGlobe'))
const VerificationAnimation = lazy(() => import('./stages/VerificationAnimation'))
const ComparingAnimation = lazy(() => import('./stages/ComparingAnimation'))
const RecommendingAnimation = lazy(() => import('./stages/RecommendingAnimation'))

const STAGE_MAP: Record<string, React.LazyExoticComponent<React.ComponentType>> = {
  parsing: ParsingAnimation,
  discovering: DiscoveryGlobe,
  verifying: VerificationAnimation,
  comparing: ComparingAnimation,
  recommending: RecommendingAnimation,
}

const STAGE_LABELS: Record<string, string> = {
  parsing: 'Analyzing your requirements...',
  discovering: 'Searching for suppliers worldwide...',
  verifying: 'Verifying supplier credentials...',
  comparing: 'Comparing options side by side...',
  recommending: 'Preparing your recommendations...',
}

function FallbackLoader({ stage }: { stage: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-6">
      <span
        className="status-dot bg-teal animate-pulse-dot mb-4"
        style={{ width: 10, height: 10 }}
      />
      <p className="text-[14px] text-ink-2 font-medium">
        {STAGE_LABELS[stage] || 'Processing...'}
      </p>
    </div>
  )
}

export default function StageAnimationRouter() {
  const { status, loading } = useWorkspace()
  const reduced = useReducedMotion()
  const stage = status?.current_stage || 'idle'

  if (!loading && !['discovering', 'verifying', 'comparing', 'recommending', 'parsing'].includes(stage)) {
    return null
  }

  if (reduced) return <FallbackLoader stage={stage} />

  const StageComponent = STAGE_MAP[stage]
  if (!StageComponent) return <FallbackLoader stage={stage} />

  return (
    <AnimatePresence mode="wait">
      <m.div
        key={stage}
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 1.02 }}
        transition={{ duration: DURATION.slow, ease: EASE_OUT_EXPO }}
        className="min-h-[50vh]"
      >
        <Suspense fallback={<FallbackLoader stage={stage} />}>
          <StageComponent />
        </Suspense>
      </m.div>
    </AnimatePresence>
  )
}
