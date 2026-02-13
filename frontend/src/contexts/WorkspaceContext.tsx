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
import { useSearchParams } from 'next/navigation'
import {
  AuthUser,
  authFetch,
  clearAuthSession,
  getStoredAccessToken,
} from '@/lib/auth'
import {
  Phase,
  PipelineStatus,
  stageToPhase,
  phaseIndex,
} from '@/types/pipeline'
import { usePipelinePolling } from '@/hooks/usePipelinePolling'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

// ─── Context Type ───────────────────────────────────────

interface WorkspaceContextValue {
  // Auth
  authUser: AuthUser
  handleSignOut: () => void

  // Project
  projectId: string | null
  setProjectId: (id: string | null) => void

  // Pipeline
  status: PipelineStatus | null
  loading: boolean
  polling: boolean

  // Phase navigation
  activePhase: Phase
  setActivePhase: (phase: Phase) => void
  highestReachedPhase: Phase

  // Backend health
  backendOk: boolean | null

  // Error
  errorMessage: string | null
  setErrorMessage: (msg: string | null) => void

  // Actions
  handleSearch: (description: string) => Promise<void>
  handleClarifyingAnswered: () => void
  refreshStatus: () => void
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null)

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) throw new Error('useWorkspace must be used within WorkspaceProvider')
  return ctx
}

// ─── Provider ───────────────────────────────────────────

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
  const searchParams = useSearchParams()

  const [projectId, setProjectId] = useState<string | null>(null)
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

  const { status, loading, polling, startPolling, refreshStatus, pollStatus } =
    pipeline

  // Pick up projectId from URL params
  useEffect(() => {
    const initialProjectId = searchParams.get('projectId')
    if (initialProjectId) {
      setProjectId(initialProjectId)
      pipeline.setLoading(true)
      pipeline.setPolling(true)
    }
  }, [searchParams])

  // Backend health check
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

  // Phase auto-advance: only advance forward, never backward
  useEffect(() => {
    if (!status || userOverridePhase) return
    const autoPhase = stageToPhase(status.current_stage)
    const autoIdx = phaseIndex(autoPhase)
    const currentHighestIdx = phaseIndex(highestReachedPhase)

    if (autoIdx > currentHighestIdx) {
      setHighestReachedPhase(autoPhase)
    }
    // Auto-advance the active phase to match pipeline
    if (autoIdx >= phaseIndex(activePhase)) {
      setActivePhase(autoPhase)
    }
  }, [status?.current_stage])

  // Reset user override when pipeline stage changes
  useEffect(() => {
    setUserOverridePhase(false)
  }, [status?.current_stage])

  const handleSetActivePhase = useCallback(
    (phase: Phase) => {
      setActivePhase(phase)
      setUserOverridePhase(true)
    },
    []
  )

  const handleSearch = useCallback(
    async (description: string) => {
      pipeline.setLoading(true)
      pipeline.setStatus(null)
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
        pipeline.setPolling(true)
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
        pipeline.setLoading(false)
      }
    },
    [handleUnauthorized]
  )

  const handleClarifyingAnswered = useCallback(() => {
    pipeline.setPolling(true)
  }, [])

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
      handleClarifyingAnswered,
      refreshStatus,
    }),
    [
      authUser,
      handleSignOut,
      projectId,
      status,
      loading,
      polling,
      activePhase,
      handleSetActivePhase,
      highestReachedPhase,
      backendOk,
      errorMessage,
      handleSearch,
      handleClarifyingAnswered,
      refreshStatus,
    ]
  )

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  )
}
