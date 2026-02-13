'use client'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import PhaseTabBar from './PhaseTabBar'
import LeftRail from './LeftRail'
import CenterStage from './CenterStage'
import InputBar from './InputBar'

export default function WorkspaceShell() {
  const { authUser, handleSignOut, backendOk } = useWorkspace()

  return (
    <div className="h-screen flex flex-col bg-workspace-bg overflow-hidden">
      {/* ── Top Bar ────────────────────────────────────── */}
      <header className="h-14 border-b border-workspace-border bg-workspace-surface/80 backdrop-blur-sm flex items-center px-4 shrink-0 z-50">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mr-6">
          <div className="w-8 h-8 rounded-lg bg-teal flex items-center justify-center">
            <span className="text-workspace-bg font-bold text-sm">T</span>
          </div>
          <span className="font-heading text-lg text-workspace-text">Tamkin</span>
        </div>

        {/* Phase Tabs (centered) */}
        <div className="flex-1">
          <PhaseTabBar />
        </div>

        {/* Right: user info + health */}
        <div className="flex items-center gap-3 ml-4">
          {backendOk === true && (
            <span className="inline-flex items-center gap-1 text-[10px] text-teal bg-teal/10 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-teal" />
              API
            </span>
          )}
          {backendOk === false && (
            <span className="inline-flex items-center gap-1 text-[10px] text-red-400 bg-red-400/10 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              Offline
            </span>
          )}
          <span className="text-xs text-workspace-muted hidden sm:inline truncate max-w-32">
            {authUser.email}
          </span>
          <button
            onClick={handleSignOut}
            className="text-xs px-3 py-1.5 rounded-full border border-workspace-border text-workspace-muted hover:text-workspace-text hover:border-workspace-text/30 transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Main Content ───────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Rail */}
        <aside className="w-60 border-r border-workspace-border bg-workspace-surface overflow-y-auto shrink-0 hidden md:block">
          <LeftRail />
        </aside>

        {/* Center Stage */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto px-6 py-6">
            <CenterStage />
          </div>
        </main>
      </div>

      {/* ── Bottom Input Bar ───────────────────────────── */}
      <div className="border-t border-workspace-border bg-workspace-surface/90 backdrop-blur-sm shrink-0">
        <InputBar />
      </div>
    </div>
  )
}
