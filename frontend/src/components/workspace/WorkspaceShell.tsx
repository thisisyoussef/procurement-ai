'use client'

import PhaseTabBar from './PhaseTabBar'
import LeftRail from './LeftRail'
import CenterStage from './CenterStage'

export default function WorkspaceShell() {
  return (
    <div className="h-screen flex bg-cream overflow-hidden">
      {/* Left Rail */}
      <aside className="w-60 border-r border-surface-3 bg-white shrink-0 hidden md:flex flex-col">
        <LeftRail />
      </aside>

      {/* Main: tabs + stage */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <PhaseTabBar />

        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <CenterStage />
        </main>
      </div>
    </div>
  )
}
