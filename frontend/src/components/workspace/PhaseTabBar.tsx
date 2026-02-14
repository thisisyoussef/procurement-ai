'use client'

import { useRouter } from 'next/navigation'
import { useState, useRef, useEffect } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import { Phase, phaseIndex, stageToPhase } from '@/types/pipeline'
import { m } from '@/lib/motion'

const PHASES: { key: Phase; label: string }[] = [
  { key: 'brief', label: 'Brief' },
  { key: 'search', label: 'Search' },
  { key: 'compare', label: 'Compare' },
  { key: 'outreach', label: 'Outreach' },
  { key: 'samples', label: 'Samples' },
  { key: 'order', label: 'Order' },
]

const RUNNING_STATUSES = new Set<string>([
  'parsing',
  'clarifying',
  'discovering',
  'verifying',
  'comparing',
  'recommending',
  'outreaching',
])

export default function PhaseTabBar() {
  const router = useRouter()
  const {
    activePhase,
    setActivePhase,
    highestReachedPhase,
    status,
    projectId,
    authUser,
    handleSignOut,
    backendOk,
  } = useWorkspace()

  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const pipelinePhase = status ? stageToPhase(status.current_stage) : null
  const pipelineRunning = status ? RUNNING_STATUSES.has(status.status) : false
  const projectName = status?.parsed_requirements?.product_type

  // close menu on outside click
  useEffect(() => {
    if (!menuOpen) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  const firstLetter = (authUser.full_name?.[0] || authUser.email[0]).toUpperCase()

  return (
    <div className="flex items-center border-b border-surface-3 bg-white shrink-0 px-5 gap-4">
      {/* Logo — links to dashboard */}
      <button
        onClick={() => router.push('/dashboard')}
        className="font-body font-extrabold text-[15px] text-ink-2 tracking-tight shrink-0 hover:opacity-70 transition-opacity mr-1"
      >
        tam<span className="text-teal">kin</span>
      </button>

      {/* Divider */}
      <div className="w-px h-5 bg-surface-3 shrink-0" />

      {/* Project name + status (if active) */}
      {projectName && (
        <div className="flex items-center gap-2 shrink-0 mr-1">
          <span
            className={`w-[6px] h-[6px] rounded-full shrink-0 ${
              pipelineRunning
                ? 'bg-teal animate-pulse-dot'
                : status?.status === 'complete'
                ? 'bg-ink-4'
                : status?.status === 'failed' || status?.status === 'canceled'
                ? 'bg-red-400'
                : 'bg-ink-4/30'
            }`}
          />
          <span className="text-[11px] font-medium text-ink-3 max-w-[140px] truncate">
            {projectName}
          </span>
        </div>
      )}

      {/* Phase tabs */}
      <div className="flex gap-0 flex-1 min-w-0">
        {PHASES.map((phase) => {
          const reached = phaseIndex(phase.key) <= phaseIndex(highestReachedPhase)
          const isActive = activePhase === phase.key
          const disabled = !projectId && phase.key !== 'brief'
          const isPipelinePhase = pipelineRunning && pipelinePhase === phase.key

          return (
            <button
              key={phase.key}
              onClick={() => !disabled && setActivePhase(phase.key)}
              disabled={disabled}
              className={`
                relative px-4 py-4 text-[11px] font-medium tracking-[0.3px] transition-all whitespace-nowrap
                ${isActive
                  ? 'text-ink'
                  : reached
                  ? 'text-ink-3 hover:text-ink-2'
                  : disabled
                  ? 'text-ink-4/40 cursor-not-allowed'
                  : 'text-ink-4 hover:text-ink-3'
                }
              `}
            >
              <span className="flex items-center gap-2">
                {isPipelinePhase && (
                  <span className="status-dot bg-teal animate-pulse-dot" />
                )}
                {phase.label}
              </span>
              {isActive && (
                <m.span
                  layoutId="phase-indicator"
                  className="absolute bottom-0 left-4 right-4 h-[1.5px] bg-teal rounded-full"
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
            </button>
          )
        })}
      </div>

      {/* User avatar + dropdown */}
      <div className="relative shrink-0" ref={menuRef}>
        <button
          onClick={() => setMenuOpen((prev) => !prev)}
          className="w-7 h-7 rounded-full bg-ink text-white flex items-center justify-center text-[10px] font-bold hover:opacity-80 transition-opacity"
          title={authUser.full_name || authUser.email}
        >
          {firstLetter}
        </button>

        {menuOpen && (
          <div className="absolute right-0 top-full mt-2 w-52 bg-white rounded-lg shadow-lg border border-surface-3 py-2 z-50">
            <div className="px-4 py-2 border-b border-surface-3">
              <p className="text-[12px] font-semibold text-ink-2 truncate">
                {authUser.full_name || authUser.email.split('@')[0]}
              </p>
              <p className="text-[10px] text-ink-4 truncate">{authUser.email}</p>
            </div>

            <button
              onClick={() => {
                setMenuOpen(false)
                router.push('/dashboard')
              }}
              className="w-full text-left px-4 py-2 text-[11px] text-ink-3 hover:bg-surface-2 hover:text-ink-2 transition-colors"
            >
              Dashboard
            </button>

            <button
              onClick={() => {
                setMenuOpen(false)
                handleSignOut()
              }}
              className="w-full text-left px-4 py-2 text-[11px] text-ink-3 hover:bg-surface-2 hover:text-red-500 transition-colors"
            >
              Sign out
            </button>

            {backendOk !== null && (
              <div className="px-4 py-2 border-t border-surface-3 flex items-center gap-2">
                <span
                  className={`w-[5px] h-[5px] rounded-full ${
                    backendOk ? 'bg-teal' : 'bg-red-400'
                  }`}
                />
                <span className="text-[10px] text-ink-4">
                  {backendOk ? 'Backend connected' : 'Backend offline'}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
