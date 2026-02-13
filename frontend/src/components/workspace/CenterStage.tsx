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
        <div className="mb-6 p-4 glass-card border-red-500/30">
          <p className="text-red-400 font-medium text-sm">Backend API is not reachable</p>
          <p className="text-workspace-muted text-xs mt-1">
            Start the backend: <code className="text-red-300">uvicorn app.main:app --reload --port 8000</code>
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
