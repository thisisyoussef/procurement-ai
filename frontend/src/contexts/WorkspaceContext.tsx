'use client'

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  ReactNode,
} from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { AuthUser, authFetch, clearAuthSession } from '@/lib/auth'
import { trackTraceEvent } from '@/lib/telemetry'
import { Phase, PipelineStatus, stageToPhase, phaseIndex } from '@/types/pipeline'
import { usePipelinePolling } from '@/hooks/usePipelinePolling'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

export interface WorkspaceProjectSummary {
  id: string
  title: string
  status: string
  current_stage: string
}

interface WorkspaceContextValue {
  authUser: AuthUser
  handleSignOut: () => void

  projectId: string | null
  setProjectId: (id: string | null) => void
  projectList: WorkspaceProjectSummary[]
  projectListLoading: boolean

  status: PipelineStatus | null
  loading: boolean
  polling: boolean

  activePhase: Phase
  setActivePhase: (phase: Phase) => void
  highestReachedPhase: Phase

  backendOk: boolean | null

  errorMessage: string | null
  setErrorMessage: (msg: string | null) => void

  handleSearch: (description: string) => Promise<void>
  startNewProject: () => void
  openProject: (id: string) => void
  cancelCurrentProject: () => Promise<boolean>
  handleClarifyingAnswered: () => void
  refreshStatus: () => void
  refreshProjectList: () => Promise<void>
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null)

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) throw new Error('useWorkspace must be used within WorkspaceProvider')
  return ctx
}

interface WorkspaceProviderProps {
  authUser: AuthUser
  onSignOut: () => void
  children: ReactNode
}

export function WorkspaceProvider({
  authUser,
  onSignOut,
  children,
}: WorkspaceProviderProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [projectId, setProjectId] = useState<string | null>(null)
  const [projectList, setProjectList] = useState<WorkspaceProjectSummary[]>([])
  const [projectListLoading, setProjectListLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [backendOk, setBackendOk] = useState<boolean | null>(null)
  const [activePhase, setActivePhase] = useState<Phase>('brief')
  const [highestReachedPhase, setHighestReachedPhase] = useState<Phase>('brief')
  const [userOverridePhase, setUserOverridePhase] = useState(false)
  const backendHealthRef = useRef<boolean | null>(null)

  const handleUnauthorized = useCallback(() => {
    clearAuthSession()
    onSignOut()
  }, [onSignOut])

  const pipeline = usePipelinePolling(projectId, {
    onUnauthorized: handleUnauthorized,
  })

  const {
    status,
    loading,
    polling,
    refreshStatus,
    setStatus,
    setLoading,
    setPolling,
    stopPolling,
  } = pipeline

  const resetWorkspace = useCallback(() => {
    setProjectId(null)
    setStatus(null)
    setErrorMessage(null)
    setActivePhase('brief')
    setHighestReachedPhase('brief')
    setUserOverridePhase(false)
    stopPolling()
  }, [setStatus, stopPolling])

  const refreshProjectList = useCallback(async () => {
    setProjectListLoading(true)
    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects`)
      if (res.status === 401) {
        handleUnauthorized()
        return
      }
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data = (await res.json()) as WorkspaceProjectSummary[]
      setProjectList(data)
      trackTraceEvent('workspace_project_list_loaded', { count: data.length })
    } catch (err) {
      console.error('Project list error:', err)
      trackTraceEvent(
        'workspace_project_list_error',
        { detail: err instanceof Error ? err.message : String(err) },
        { level: 'warn' }
      )
    } finally {
      setProjectListLoading(false)
    }
  }, [handleUnauthorized])

  const openProject = useCallback(
    (id: string) => {
      if (!id || id === projectId) return
      trackTraceEvent('workspace_project_open_click', {
        current_project_id: projectId,
        target_project_id: id,
      }, { projectId: id })
      setProjectId(id)
      setStatus(null)
      setErrorMessage(null)
      setActivePhase('brief')
      setHighestReachedPhase('brief')
      setUserOverridePhase(false)
      setLoading(true)
      setPolling(true)
    },
    [projectId, setLoading, setPolling, setStatus]
  )

  const startNewProject = useCallback(() => {
    trackTraceEvent('workspace_project_new_click', {
      previous_project_id: projectId,
    })
    resetWorkspace()
  }, [projectId, resetWorkspace])

  const cancelCurrentProject = useCallback(async (): Promise<boolean> => {
    if (!projectId) return false
    trackTraceEvent('workspace_cancel_attempt', { project_id: projectId }, { projectId })
    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/cancel`, {
        method: 'POST',
      })
      if (res.status === 401) {
        handleUnauthorized()
        return false
      }
      if (!res.ok) {
        let detail = `HTTP ${res.status}`
        try {
          const payload = await res.json()
          detail = payload.detail || JSON.stringify(payload)
        } catch {
          // Ignore payload parse failures and keep HTTP detail.
        }
        throw new Error(detail)
      }

      setStatus((prev) =>
        prev
          ? {
              ...prev,
              status: 'canceled',
              current_stage: 'canceled',
              error: prev.error || 'Canceled by user',
            }
          : prev
      )
      setLoading(false)
      setPolling(false)
      setErrorMessage(null)
      await refreshProjectList()
      trackTraceEvent('workspace_cancel_success', { project_id: projectId }, { projectId })
      return true
    } catch (err: any) {
      const msg = err?.message || 'Could not cancel this run.'
      setErrorMessage(msg)
      trackTraceEvent(
        'workspace_cancel_error',
        { project_id: projectId, detail: msg },
        { projectId, level: 'warn' }
      )
      return false
    }
  }, [
    projectId,
    handleUnauthorized,
    setStatus,
    setLoading,
    setPolling,
    refreshProjectList,
  ])

  useEffect(() => {
    const urlProjectId = searchParams.get('projectId')?.trim() || null
    if (urlProjectId && urlProjectId !== projectId) {
      trackTraceEvent(
        'workspace_project_loaded_from_url',
        { project_id: urlProjectId },
        { projectId: urlProjectId }
      )
      setProjectId(urlProjectId)
      setStatus(null)
      setErrorMessage(null)
      setLoading(true)
      setPolling(true)
      return
    }
  }, [
    projectId,
    searchParams,
    setLoading,
    setPolling,
    setStatus,
  ])

  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString())
    const currentParamId = params.get('projectId')
    if (projectId) {
      if (currentParamId === projectId) return
      params.set('projectId', projectId)
    } else {
      if (!currentParamId) return
      params.delete('projectId')
    }
    const query = params.toString()
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
  }, [pathname, projectId, router, searchParams])

  useEffect(() => {
    void refreshProjectList()
  }, [refreshProjectList])

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, {
          signal: AbortSignal.timeout(3000),
        })
        setBackendOk(res.ok)
      } catch {
        setBackendOk(false)
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (backendOk == null) return
    if (backendHealthRef.current == null) {
      trackTraceEvent('backend_health_initial', { ok: backendOk })
    } else if (backendHealthRef.current !== backendOk) {
      trackTraceEvent(
        'backend_health_changed',
        { from: backendHealthRef.current, to: backendOk },
        { level: backendOk ? 'info' : 'warn' }
      )
    }
    backendHealthRef.current = backendOk
  }, [backendOk])

  useEffect(() => {
    if (!status || userOverridePhase) return
    if (projectId && status.project_id && status.project_id !== projectId) return
    const autoPhase = stageToPhase(status.current_stage)
    const autoIdx = phaseIndex(autoPhase)
    const currentHighestIdx = phaseIndex(highestReachedPhase)

    if (autoIdx > currentHighestIdx) {
      setHighestReachedPhase(autoPhase)
    }
    if (autoIdx >= phaseIndex(activePhase)) {
      setActivePhase(autoPhase)
    }
  }, [activePhase, highestReachedPhase, status, userOverridePhase])

  useEffect(() => {
    if (projectId && status?.project_id && status.project_id !== projectId) return
    setUserOverridePhase(false)
  }, [projectId, status?.current_stage, status?.project_id])

  const handleSetActivePhase = useCallback((phase: Phase) => {
    trackTraceEvent(
      'workspace_phase_changed',
      { from: activePhase, to: phase, project_id: projectId },
      { projectId: projectId || undefined }
    )
    setActivePhase(phase)
    setUserOverridePhase(true)
  }, [activePhase, projectId])

  const handleSearch = useCallback(
    async (description: string) => {
      trackTraceEvent('workspace_search_submit', {
        description_length: description.length,
        description_preview: description.slice(0, 120),
      })
      setLoading(true)
      setStatus(null)
      setErrorMessage(null)
      setActivePhase('brief')
      setHighestReachedPhase('brief')
      setUserOverridePhase(false)

      try {
        const res = await authFetch(`${API_BASE}/api/v1/projects`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: description.slice(0, 80),
            product_description: description,
          }),
        })

        if (res.status === 401) {
          handleUnauthorized()
          return
        }

        if (!res.ok) {
          let detail = `HTTP ${res.status}`
          try {
            const errBody = await res.json()
            detail = errBody.detail || JSON.stringify(errBody)
          } catch {
            detail += ` - ${res.statusText || 'Unknown error'}`
          }
          throw new Error(detail)
        }

        const data = await res.json()
        setProjectId(data.project_id)
        setPolling(true)
        trackTraceEvent(
          'workspace_search_started',
          { project_id: data.project_id },
          { projectId: data.project_id }
        )
        void refreshProjectList()
      } catch (err: any) {
        const msg = err?.message || 'Unknown error'
        console.error('Search error:', msg)
        trackTraceEvent('workspace_search_error', { detail: msg }, { level: 'warn' })
        setErrorMessage(
          msg.includes('fetch') ||
            msg.includes('NetworkError') ||
            msg.includes('Failed to fetch')
            ? `Cannot reach the backend API at ${API_BASE || 'this origin'}.`
            : msg
        )
        setLoading(false)
      }
    },
    [handleUnauthorized, refreshProjectList, setLoading, setPolling, setStatus]
  )

  const handleClarifyingAnswered = useCallback(() => {
    trackTraceEvent(
      'workspace_clarifying_answered',
      { project_id: projectId },
      { projectId: projectId || undefined }
    )
    setPolling(true)
  }, [projectId, setPolling])

  const handleSignOut = useCallback(() => {
    clearAuthSession()
    onSignOut()
  }, [onSignOut])

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      authUser,
      handleSignOut,
      projectId,
      setProjectId,
      projectList,
      projectListLoading,
      status,
      loading,
      polling,
      activePhase,
      setActivePhase: handleSetActivePhase,
      highestReachedPhase,
      backendOk,
      errorMessage,
      setErrorMessage,
      handleSearch,
      startNewProject,
      openProject,
      cancelCurrentProject,
      handleClarifyingAnswered,
      refreshStatus,
      refreshProjectList,
    }),
    [
      authUser,
      handleSignOut,
      projectId,
      projectList,
      projectListLoading,
      status,
      loading,
      polling,
      activePhase,
      handleSetActivePhase,
      highestReachedPhase,
      backendOk,
      errorMessage,
      handleSearch,
      startNewProject,
      openProject,
      cancelCurrentProject,
      handleClarifyingAnswered,
      refreshStatus,
      refreshProjectList,
    ]
  )

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  )
}
