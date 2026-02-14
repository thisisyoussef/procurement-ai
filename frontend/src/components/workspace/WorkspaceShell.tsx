'use client'

import PhaseTabBar from './PhaseTabBar'
import CenterStage from './CenterStage'

export default function WorkspaceShell() {
  return (
    <div className="h-screen flex flex-col bg-cream overflow-hidden">
      <PhaseTabBar />

      <main className="flex-1 overflow-y-auto overflow-x-hidden">
        <CenterStage />
      </main>
    </div>
  )
}
