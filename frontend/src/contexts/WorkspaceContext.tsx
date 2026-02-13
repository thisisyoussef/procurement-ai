'use client'

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  ReactNode,
} from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { AuthUser, authFetch, clearAuthSession } from '@/lib/auth'
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
    } catch (err) {
      console.error('Project list error:', err)
    } finally {
      setProjectListLoading(false)
    }
  }, [handleUnauthorized])

  const openProject = useCallback(
    (id: string) => {
      if (!id || id === projectId) return
      setProjectId(id)
      setStatus(null)
      setErrorMessage(null)
      setLoading(true)
      setPolling(true)
    },
    [projectId, setLoading, setPolling, setStatus]
  )

  const startNewProject = useCallback(() => {
    resetWorkspace()
  }, [resetWorkspace])

  const cancelCurrentProject = useCallback(async (): Promise<boolean> => {
    if (!projectId) return false
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
      return true
    } catch (err: any) {
      const msg = err?.message || 'Could not cancel this run.'
      setErrorMessage(msg)
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
    if (!status || userOverridePhase) return
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
    setUserOverridePhase(false)
  }, [status?.current_stage])

  const handleSetActivePhase = useCallback((phase: Phase) => {
    setActivePhase(phase)
    setUserOverridePhase(true)
  }, [])

  const handleSearch = useCallback(
    async (description: string) => {
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
        void refreshProjectList()
      } catch (err: any) {
        const msg = err?.message || 'Unknown error'
        console.error('Search error:', msg)
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
    setPolling(true)
  }, [setPolling])

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
