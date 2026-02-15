'use client'

import { useSearchParams } from 'next/navigation'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import BriefPhase from './phases/BriefPhase'
import SearchPhase from './phases/SearchPhase'
import OutreachPhase from './phases/OutreachPhase'
import ComparePhase from './phases/ComparePhase'
import SamplesPhase from './phases/SamplesPhase'
import OrderPhase from './phases/OrderPhase'
import LiveProgressFeed from './LiveProgressFeed'
import DebugConsoleFeed from './DebugConsoleFeed'
import CheckpointBanner from './CheckpointBanner'
import StageTransitionToast from './StageTransitionToast'
import SupplierProfileView from './supplier-profile/SupplierProfileView'
import { AnimatePresence, m } from '@/lib/motion'
import { phaseTransition } from '@/lib/motion/variants'

const PHASE_COMPONENTS: Record<string, React.ComponentType> = {
  brief: BriefPhase,
  search: SearchPhase,
  outreach: OutreachPhase,
  compare: ComparePhase,
  samples: SamplesPhase,
  order: OrderPhase,
}

export default function CenterStage() {
  const { activePhase, backendOk } = useWorkspace()
  const searchParams = useSearchParams()
  const supplierIndex = searchParams.get('supplierIndex')
  const supplierName = searchParams.get('supplierName')
  const showProfile = supplierIndex != null || supplierName != null

  const PhaseComponent = PHASE_COMPONENTS[activePhase]

  return (
    <>
      <StageTransitionToast />

      {/* Backend offline warning */}
      {backendOk === false && (
        <div className="mx-6 mt-6 card border-l-[3px] border-l-red-400 px-5 py-4">
          <p className="text-[13px] font-semibold text-ink-2">Backend API is not reachable</p>
          <p className="text-[11px] text-ink-4 mt-1">
            Start the backend with <code className="text-ink-3 font-mono text-[10px]">uvicorn app.main:app --reload --port 8000</code>
          </p>
        </div>
      )}

      {/* Supplier profile view (when supplierIndex or supplierName is in URL) */}
      {showProfile ? (
        <SupplierProfileView
          supplierIndex={supplierIndex != null ? parseInt(supplierIndex, 10) : undefined}
          supplierName={supplierName || undefined}
        />
      ) : (
        <>
          <CheckpointBanner />
          <LiveProgressFeed />
          <DebugConsoleFeed />
          <AnimatePresence mode="wait">
            <m.div
              key={activePhase}
              variants={phaseTransition}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              {PhaseComponent && <PhaseComponent />}
            </m.div>
          </AnimatePresence>
        </>
      )}
    </>
  )
}
