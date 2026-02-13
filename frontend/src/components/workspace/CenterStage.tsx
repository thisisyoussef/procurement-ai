'use client'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import BriefPhase from './phases/BriefPhase'
import SearchPhase from './phases/SearchPhase'
import OutreachPhase from './phases/OutreachPhase'
import ComparePhase from './phases/ComparePhase'
import SamplesPhase from './phases/SamplesPhase'
import OrderPhase from './phases/OrderPhase'

export default function CenterStage() {
  const { activePhase, backendOk } = useWorkspace()

  return (
    <>
      {/* Backend offline warning */}
      {backendOk === false && (
        <div className="mx-6 mt-6 card border-l-[3px] border-l-red-400 px-5 py-4">
          <p className="text-[13px] font-semibold text-ink-2">Backend API is not reachable</p>
          <p className="text-[11px] text-ink-4 mt-1">
            Start the backend with <code className="text-ink-3 font-mono text-[10px]">uvicorn app.main:app --reload --port 8000</code>
          </p>
        </div>
      )}

      {/* Phase content */}
      {activePhase === 'brief' && <BriefPhase />}
      {activePhase === 'search' && <SearchPhase />}
      {activePhase === 'outreach' && <OutreachPhase />}
      {activePhase === 'compare' && <ComparePhase />}
      {activePhase === 'samples' && <SamplesPhase />}
      {activePhase === 'order' && <OrderPhase />}
    </>
  )
}
