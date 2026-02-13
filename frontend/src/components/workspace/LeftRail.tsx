'use client'

import { useMemo, useState } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'

const PIPELINE_STEPS = [
  { stage: 'parsing', label: 'Brief', sub: 'Define what you need' },
  { stage: 'discovering', label: 'Search', sub: 'Finding manufacturers' },
  { stage: 'verifying', label: 'Verify', sub: 'Checking credentials' },
  { stage: 'comparing', label: 'Compare', sub: 'Side-by-side analysis' },
  { stage: 'recommending', label: 'Recommend', sub: 'Final picks' },
  { stage: 'outreaching', label: 'Outreach', sub: 'Contacting suppliers' },
  { stage: 'complete', label: 'Done', sub: 'Results ready' },
]

function getStepState(stepStage: string, currentStage: string, pipelineStatus: string): 'done' | 'active' | 'waiting' {
  const order = PIPELINE_STEPS.map(s => s.stage)
  const currentIdx = order.indexOf(currentStage)
  const stepIdx = order.indexOf(stepStage)

  if (pipelineStatus === 'complete') return 'done'
  if (pipelineStatus === 'failed' || pipelineStatus === 'canceled') {
    return stepStage === 'complete' ? 'waiting' : 'done'
  }
  if (stepIdx < currentIdx) return 'done'
  if (stepIdx === currentIdx) return 'active'
  return 'waiting'
}

export default function LeftRail() {
  const {
    status,
    authUser,
    handleSignOut,
    backendOk,
    loading,
    projectId,
    projectList,
    projectListLoading,
    startNewProject,
    openProject,
    cancelCurrentProject,
  } = useWorkspace()
  const [canceling, setCanceling] = useState(false)

  const parsed = status?.parsed_requirements
  const currentStage = status?.current_stage || 'idle'
  const pipelineStatus = status?.status || 'idle'
  const projectName = parsed?.product_type || (projectId ? 'Sourcing project' : null)
  const activeStatuses = useMemo(
    () =>
      new Set([
        'parsing',
        'clarifying',
        'discovering',
        'verifying',
        'comparing',
        'recommending',
        'outreaching',
      ]),
    []
  )
  const canCancel = Boolean(projectId && activeStatuses.has(pipelineStatus) && !canceling)

  const runCancel = async () => {
    if (!canCancel) return
    setCanceling(true)
    await cancelCurrentProject()
    setCanceling(false)
  }

  const statusDotClass = (value: string) => {
    if (value === 'complete') return 'bg-ink-4'
    if (value === 'failed' || value === 'canceled') return 'bg-red-400'
    if (activeStatuses.has(value)) return 'bg-teal animate-pulse-dot'
    return 'bg-ink-4/30'
  }

  const statusLabel = (value: string) =>
    value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 flex items-center justify-between">
        <div className="font-body font-extrabold text-[15px] text-ink-2 tracking-tight">
          tam<span className="text-teal">kin</span>
        </div>
        <button
          onClick={startNewProject}
          className="w-6 h-6 rounded-full bg-surface-2 text-ink-4 text-sm flex items-center justify-center hover:bg-teal/10 hover:text-teal transition-colors"
          title="Start a new project"
          aria-label="Start a new project"
        >
          +
        </button>
      </div>

      {/* Projects */}
      <div className="px-5 pb-2">
        <p className="text-[9px] font-bold text-ink-4 tracking-[2px] uppercase mb-2">Projects</p>
        <div className="flex gap-2">
          <button
            onClick={startNewProject}
            className="text-[10px] px-2.5 py-1 rounded-md border border-surface-3 text-ink-4 hover:text-teal hover:border-teal transition-colors"
          >
            New
          </button>
          <button
            onClick={runCancel}
            disabled={!canCancel}
            className="text-[10px] px-2.5 py-1 rounded-md border border-surface-3 text-ink-4 hover:text-red-400 hover:border-red-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title={canCancel ? 'Cancel this run' : 'No active run to cancel'}
          >
            {canceling ? 'Canceling…' : 'Cancel run'}
          </button>
        </div>
      </div>
      <div className="px-3 pb-2">
        {projectName ? (
          <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-teal/[0.04]">
            <span className={`status-dot ${statusDotClass(pipelineStatus)}`} />
            <div className="min-w-0">
              <p className="text-[12px] font-medium text-teal truncate">{projectName}</p>
              {parsed?.quantity && (
                <p className="text-[10px] text-ink-4 truncate">Qty: {parsed.quantity}</p>
              )}
            </div>
          </div>
        ) : (
          <p className="px-3 text-[11px] text-ink-4 italic">
            {loading ? 'Starting...' : 'No active project'}
          </p>
        )}
      </div>
      <div className="px-3 pb-3 space-y-1.5">
        {projectListLoading && projectList.length === 0 && (
          <p className="px-3 text-[10px] text-ink-4">Loading projects…</p>
        )}
        {projectList.map((project) => {
          const isActive = project.id === projectId
          return (
            <button
              key={project.id}
              onClick={() => openProject(project.id)}
              className={`w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
                isActive ? 'bg-teal/[0.04]' : 'hover:bg-surface-2'
              }`}
            >
              <span className={`status-dot ${statusDotClass(project.status)}`} />
              <div className="min-w-0 flex-1">
                <p className={`text-[11px] truncate ${isActive ? 'text-teal font-medium' : 'text-ink-3'}`}>
                  {project.title || 'Untitled project'}
                </p>
                <p className="text-[9.5px] text-ink-4 truncate">
                  {statusLabel(project.status)}
                </p>
              </div>
            </button>
          )
        })}
      </div>

      <div className="h-px bg-surface-3 mx-5 my-2" />

      {/* Timeline */}
      <div className="px-5 pb-2">
        <p className="text-[9px] font-bold text-ink-4 tracking-[2px] uppercase mb-3">This project</p>
      </div>
      <div className="flex-1 overflow-y-auto px-3">
        {PIPELINE_STEPS.map((step, i) => {
          const state = projectId
            ? getStepState(step.stage, currentStage, pipelineStatus)
            : 'waiting'

          return (
            <div key={step.stage} className="flex gap-0 px-3 py-1.5">
              <div className="flex flex-col items-center mr-3 shrink-0" style={{ width: 7 }}>
                <span
                  className={`w-[7px] h-[7px] rounded-full shrink-0 ${
                    state === 'done' ? 'bg-teal/30'
                    : state === 'active' ? 'bg-teal shadow-[0_0_8px_rgba(0,201,167,0.3)] animate-pulse-dot'
                    : 'bg-ink-4/30'
                  }`}
                />
                {i < PIPELINE_STEPS.length - 1 && (
                  <div className={`w-px flex-1 min-h-[20px] ${state === 'done' ? 'bg-teal/15' : 'bg-surface-3'}`} />
                )}
              </div>
              <div className="pb-3">
                <p className={`text-[11px] font-semibold ${
                  state === 'active' ? 'text-ink-2' : state === 'done' ? 'text-ink-3' : 'text-ink-4'
                }`}>{step.label}</p>
                <p className="text-[9.5px] text-ink-4">{step.sub}</p>
              </div>
            </div>
          )
        })}
      </div>

      {/* User footer */}
      <div className="mt-auto px-5 py-4 border-t border-surface-3 flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-full bg-ink text-white flex items-center justify-center text-[10px] font-bold shrink-0">
          {authUser.full_name?.[0]?.toUpperCase() || authUser.email[0].toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold text-ink-2 truncate">
            {authUser.full_name || authUser.email.split('@')[0]}
          </p>
          <button onClick={handleSignOut} className="text-[9.5px] text-ink-4 hover:text-teal transition-colors">
            Sign out
          </button>
        </div>
        <span className={`status-dot shrink-0 ${
          backendOk === true ? 'bg-teal' : backendOk === false ? 'bg-red-400' : 'bg-ink-4/30'
        }`} />
      </div>
    </div>
  )
}
