'use client'

import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
} from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

import { AuthUser, authFetch, clearAuthSession } from '@/lib/auth'
import { trackTraceEvent } from '@/lib/telemetry'
import { Phase, PHASE_ORDER, PipelineStatus, phaseIndex, stageToPhase } from '@/types/pipeline'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')
const POLL_INTERVAL_MS = 1200
const TERMINAL_STATUSES = new Set<string>(['complete', 'failed', 'canceled'])

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
  restartCurrentProject: (opts?: {
    fromStage?: 'parsing' | 'discovering'
    additionalContext?: string
  }) => Promise<boolean>
  handleClarifyingAnswered: () => void
  refreshStatus: () => void
  refreshProjectList: () => Promise<void>
}

interface WorkspaceState {
  projectId: string | null
  projectList: WorkspaceProjectSummary[]
  projectListLoading: boolean
  status: PipelineStatus | null
  loading: boolean
  polling: boolean
  activePhase: Phase
  highestReachedPhase: Phase
  userOverridePhase: boolean
  backendOk: boolean | null
  errorMessage: string | null
}

type WorkspaceAction =
  | { type: 'RESET_ACTIVE_PROJECT' }
  | { type: 'SELECT_PROJECT'; projectId: string }
  | { type: 'SET_PROJECT_LIST_LOADING'; value: boolean }
  | { type: 'SET_PROJECT_LIST'; projectList: WorkspaceProjectSummary[] }
  | { type: 'SET_BACKEND_OK'; value: boolean | null }
  | { type: 'SET_ERROR'; value: string | null }
  | { type: 'SET_LOADING'; value: boolean }
  | { type: 'SET_POLLING'; value: boolean }
  | { type: 'SET_STATUS'; projectId: string; status: PipelineStatus }
  | { type: 'SET_ACTIVE_PHASE'; phase: Phase; userDriven: boolean }

const initialState: WorkspaceState = {
  projectId: null,
  projectList: [],
  projectListLoading: false,
  status: null,
  loading: false,
  polling: false,
  activePhase: 'brief',
  highestReachedPhase: 'brief',
  userOverridePhase: false,
  backendOk: null,
  errorMessage: null,
}

function normalizeProjectId(value: string | null | undefined): string | null {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

function shouldContinuePolling(status: PipelineStatus): boolean {
  if (TERMINAL_STATUSES.has(status.status)) return false
  return status.status !== 'clarifying'
}

function applyStatus(state: WorkspaceState, status: PipelineStatus): WorkspaceState {
  const next: WorkspaceState = { ...state, status }

  const statusPhase = stageToPhase(status.current_stage)
  const statusPhaseIndex = phaseIndex(statusPhase)
  const highestPhaseIndex = phaseIndex(state.highestReachedPhase)
  const activePhaseIndex = phaseIndex(state.activePhase)

  if (statusPhaseIndex > highestPhaseIndex) {
    next.highestReachedPhase = statusPhase
  }

  // Keep phase stable after the user explicitly picks a tab.
  if (!state.userOverridePhase) {
    const firstStatusForProject = state.status == null
    if (firstStatusForProject || statusPhaseIndex > activePhaseIndex) {
      next.activePhase = statusPhase
    }
  }

  if (!shouldContinuePolling(status)) {
    next.loading = false
    next.polling = false
  }

  return next
}

function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    case 'RESET_ACTIVE_PROJECT':
      return {
        ...state,
        projectId: null,
        status: null,
        loading: false,
        polling: false,
        activePhase: 'brief',
        highestReachedPhase: 'brief',
        userOverridePhase: false,
        errorMessage: null,
      }

    case 'SELECT_PROJECT':
      return {
        ...state,
        projectId: action.projectId,
        status: null,
        loading: true,
        polling: false,
        activePhase: 'brief',
        highestReachedPhase: 'brief',
        userOverridePhase: false,
        errorMessage: null,
      }

    case 'SET_PROJECT_LIST_LOADING':
      return { ...state, projectListLoading: action.value }

    case 'SET_PROJECT_LIST':
      return { ...state, projectList: action.projectList }

    case 'SET_BACKEND_OK':
      return { ...state, backendOk: action.value }

    case 'SET_ERROR':
      return { ...state, errorMessage: action.value }

    case 'SET_LOADING':
      return { ...state, loading: action.value }

    case 'SET_POLLING':
      return { ...state, polling: action.value }

    case 'SET_ACTIVE_PHASE':
      return {
        ...state,
        activePhase: action.phase,
        highestReachedPhase:
          phaseIndex(action.phase) > phaseIndex(state.highestReachedPhase)
            ? action.phase
            : state.highestReachedPhase,
        userOverridePhase: action.userDriven || state.userOverridePhase,
      }

    case 'SET_STATUS':
      if (state.projectId !== action.projectId) return state
      return applyStatus(state, action.status)

    default:
      return state
  }
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

export function WorkspaceProvider({ authUser, onSignOut, children }: WorkspaceProviderProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [state, dispatch] = useReducer(workspaceReducer, initialState)

  const activeProjectRef = useRef<string | null>(state.projectId)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollAbortRef = useRef<AbortController | null>(null)
  const pollInFlightRef = useRef(false)
  const pollSessionRef = useRef(0)
  const backendHealthRef = useRef<boolean | null>(null)
  const lastHandledUrlProjectRef = useRef<string | null>(null)

  activeProjectRef.current = state.projectId

  const handleUnauthorized = useCallback(() => {
    clearAuthSession()
    onSignOut()
  }, [onSignOut])

  const invalidatePollingSession = useCallback(() => {
    pollSessionRef.current += 1
  }, [])

  const clearPollingResources = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
    if (pollAbortRef.current) {
      pollAbortRef.current.abort()
      pollAbortRef.current = null
    }
    pollInFlightRef.current = false
  }, [])

  const stopPollingUi = useCallback(() => {
    dispatch({ type: 'SET_POLLING', value: false })
    dispatch({ type: 'SET_LOADING', value: false })
  }, [])

  const syncProjectIdToUrl = useCallback(
    (projectId: string | null) => {
      const normalized = normalizeProjectId(projectId)
      const params = new URLSearchParams(searchParams.toString())
      const current = normalizeProjectId(params.get('projectId'))

      if (normalized) {
        params.set('projectId', normalized)
        params.delete('new')
      } else {
        params.delete('projectId')
        params.set('new', '1')
      }

      lastHandledUrlProjectRef.current = normalized

      if (current === normalized) return

      const query = params.toString()
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
    },
    [pathname, router, searchParams]
  )

  const fetchProjectStatus = useCallback(
    async (projectId: string, session: number, reason: string): Promise<PipelineStatus | null> => {
      if (pollInFlightRef.current) return null
      pollInFlightRef.current = true

      const controller = new AbortController()
      pollAbortRef.current = controller

      try {
        const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/status`, {
          signal: controller.signal,
        })

        if (res.status === 401) {
          handleUnauthorized()
          return null
        }

        if (!res.ok) {
          trackTraceEvent(
            'workspace_status_poll_http_error',
            { project_id: projectId, status_code: res.status, reason, session },
            { projectId, level: 'warn' }
          )
          return null
        }

        const status = (await res.json()) as PipelineStatus

        if (session !== pollSessionRef.current || activeProjectRef.current !== projectId) {
          trackTraceEvent(
            'workspace_status_poll_ignored_stale',
            {
              requested_project_id: projectId,
              active_project_id: activeProjectRef.current,
              reason,
              session,
            },
            { projectId: activeProjectRef.current || undefined }
          )
          return null
        }

        dispatch({ type: 'SET_STATUS', projectId, status })
        return status
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          trackTraceEvent(
            'workspace_status_poll_error',
            {
              project_id: projectId,
              reason,
              session,
              detail: err instanceof Error ? err.message : String(err),
            },
            { projectId, level: 'warn' }
          )
        }
        return null
      } finally {
        if (session === pollSessionRef.current) {
          pollInFlightRef.current = false
        }
      }
    },
    [handleUnauthorized]
  )

  const startPollingForProject = useCallback(
    (projectId: string, trigger: string) => {
      invalidatePollingSession()
      clearPollingResources()

      const session = pollSessionRef.current

      dispatch({ type: 'SET_POLLING', value: true })
      dispatch({ type: 'SET_LOADING', value: true })

      const runPoll = async (reason: string) => {
        const status = await fetchProjectStatus(projectId, session, reason)

        if (session !== pollSessionRef.current || activeProjectRef.current !== projectId) return

        if (!status) {
          pollTimerRef.current = setTimeout(() => {
            void runPoll('retry')
          }, POLL_INTERVAL_MS)
          return
        }

        if (shouldContinuePolling(status)) {
          pollTimerRef.current = setTimeout(() => {
            void runPoll('interval')
          }, POLL_INTERVAL_MS)
          return
        }

        stopPollingUi()
      }

      void runPoll(`${trigger}_initial`)
    },
    [clearPollingResources, fetchProjectStatus, invalidatePollingSession, stopPollingUi]
  )

  const activateProject = useCallback(
    (
      projectId: string,
      options: { source: 'user' | 'url' | 'search'; syncUrl: boolean }
    ) => {
      if (!projectId || projectId === activeProjectRef.current) return

      activeProjectRef.current = projectId
      dispatch({ type: 'SELECT_PROJECT', projectId })

      if (options.syncUrl) {
        syncProjectIdToUrl(projectId)
      }

      startPollingForProject(projectId, options.source)
    },
    [startPollingForProject, syncProjectIdToUrl]
  )

  const refreshStatus = useCallback(() => {
    if (!state.projectId) return
    const session = pollSessionRef.current
    void fetchProjectStatus(state.projectId, session, 'manual_refresh')
  }, [fetchProjectStatus, state.projectId])

  const refreshProjectList = useCallback(async () => {
    dispatch({ type: 'SET_PROJECT_LIST_LOADING', value: true })
    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects`)
      if (res.status === 401) {
        handleUnauthorized()
        return
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const data = (await res.json()) as WorkspaceProjectSummary[]
      dispatch({ type: 'SET_PROJECT_LIST', projectList: data })
      trackTraceEvent('workspace_project_list_loaded', { count: data.length })
    } catch (err) {
      trackTraceEvent(
        'workspace_project_list_error',
        { detail: err instanceof Error ? err.message : String(err) },
        { level: 'warn' }
      )
    } finally {
      dispatch({ type: 'SET_PROJECT_LIST_LOADING', value: false })
    }
  }, [handleUnauthorized])

  const openProject = useCallback(
    (id: string) => {
      const projectId = normalizeProjectId(id)
      if (!projectId || projectId === activeProjectRef.current) return

      trackTraceEvent(
        'workspace_project_open_click',
        {
          current_project_id: activeProjectRef.current,
          target_project_id: projectId,
        },
        { projectId }
      )

      activateProject(projectId, { source: 'user', syncUrl: true })
    },
    [activateProject]
  )

  const startNewProject = useCallback(() => {
    trackTraceEvent('workspace_project_new_click', {
      previous_project_id: activeProjectRef.current,
    })

    activeProjectRef.current = null
    invalidatePollingSession()
    clearPollingResources()
    dispatch({ type: 'RESET_ACTIVE_PROJECT' })
    syncProjectIdToUrl(null)
  }, [clearPollingResources, invalidatePollingSession, syncProjectIdToUrl])

  const setProjectId = useCallback(
    (id: string | null) => {
      const normalized = normalizeProjectId(id)
      if (!normalized) {
        startNewProject()
        return
      }
      openProject(normalized)
    },
    [openProject, startNewProject]
  )

  const cancelCurrentProject = useCallback(async (): Promise<boolean> => {
    if (!state.projectId) return false

    const projectId = state.projectId
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
          const payload = (await res.json()) as { detail?: string }
          detail = payload.detail || detail
        } catch {
          // Keep HTTP detail.
        }
        throw new Error(detail)
      }

      dispatch({ type: 'SET_ERROR', value: null })
      invalidatePollingSession()
      clearPollingResources()
      stopPollingUi()

      const session = pollSessionRef.current
      await fetchProjectStatus(projectId, session, 'post_cancel')
      await refreshProjectList()

      trackTraceEvent('workspace_cancel_success', { project_id: projectId }, { projectId })
      return true
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      dispatch({ type: 'SET_ERROR', value: detail || 'Could not cancel this run.' })
      trackTraceEvent(
        'workspace_cancel_error',
        { project_id: projectId, detail },
        { projectId, level: 'warn' }
      )
      return false
    }
  }, [
    clearPollingResources,
    fetchProjectStatus,
    handleUnauthorized,
    invalidatePollingSession,
    refreshProjectList,
    state.projectId,
    stopPollingUi,
  ])

  const restartCurrentProject = useCallback(
    async (opts?: { fromStage?: 'parsing' | 'discovering'; additionalContext?: string }): Promise<boolean> => {
      if (!state.projectId) return false
      const projectId = state.projectId
      const fromStage = opts?.fromStage || 'discovering'
      const additionalContext = opts?.additionalContext?.trim() || undefined

      trackTraceEvent(
        'workspace_restart_attempt',
        {
          project_id: projectId,
          from_stage: fromStage,
          has_additional_context: Boolean(additionalContext),
        },
        { projectId }
      )

      dispatch({ type: 'SET_ERROR', value: null })
      dispatch({ type: 'SET_LOADING', value: true })

      try {
        const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/restart`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            from_stage: fromStage,
            additional_context: additionalContext,
          }),
        })

        if (res.status === 401) {
          handleUnauthorized()
          return false
        }

        if (!res.ok) {
          let detail = `HTTP ${res.status}`
          try {
            const payload = (await res.json()) as { detail?: string }
            detail = payload.detail || detail
          } catch {
            // Keep HTTP detail.
          }
          throw new Error(detail)
        }

        const payload = (await res.json()) as { from_stage?: string; message?: string }
        dispatch({ type: 'SET_ERROR', value: null })
        startPollingForProject(projectId, 'restart')
        await refreshProjectList()
        trackTraceEvent(
          'workspace_restart_success',
          {
            project_id: projectId,
            from_stage: payload.from_stage || fromStage,
          },
          { projectId }
        )
        return true
      } catch (err) {
        const detail = err instanceof Error ? err.message : String(err)
        dispatch({
          type: 'SET_ERROR',
          value: detail || 'Could not restart this run.',
        })
        dispatch({ type: 'SET_LOADING', value: false })
        dispatch({ type: 'SET_POLLING', value: false })
        trackTraceEvent(
          'workspace_restart_error',
          { project_id: projectId, detail },
          { projectId, level: 'warn' }
        )
        return false
      }
    },
    [handleUnauthorized, refreshProjectList, startPollingForProject, state.projectId]
  )

  const handleSetActivePhase = useCallback(
    (phase: Phase) => {
      if (phase === state.activePhase) return
      dispatch({ type: 'SET_ACTIVE_PHASE', phase, userDriven: true })
      trackTraceEvent(
        'workspace_phase_changed',
        { from: state.activePhase, to: phase, project_id: state.projectId },
        { projectId: state.projectId || undefined }
      )
    },
    [state.activePhase, state.projectId]
  )

  const setErrorMessage = useCallback((msg: string | null) => {
    dispatch({ type: 'SET_ERROR', value: msg })
  }, [])

  const handleSearch = useCallback(
    async (description: string) => {
      const trimmed = description.trim()
      if (!trimmed) return

      trackTraceEvent('workspace_search_submit', {
        description_length: trimmed.length,
        description_preview: trimmed.slice(0, 120),
      })

      dispatch({ type: 'SET_ERROR', value: null })
      dispatch({ type: 'SET_LOADING', value: true })

      try {
        const res = await authFetch(`${API_BASE}/api/v1/projects`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: trimmed.slice(0, 80),
            product_description: trimmed,
          }),
        })

        if (res.status === 401) {
          handleUnauthorized()
          return
        }

        if (!res.ok) {
          let detail = `HTTP ${res.status}`
          try {
            const payload = (await res.json()) as { detail?: string }
            detail = payload.detail || detail
          } catch {
            // Keep HTTP detail.
          }
          throw new Error(detail)
        }

        const data = (await res.json()) as { project_id: string }

        trackTraceEvent('workspace_search_started', { project_id: data.project_id }, { projectId: data.project_id })

        activateProject(data.project_id, { source: 'search', syncUrl: true })
        void refreshProjectList()
      } catch (err) {
        const detail = err instanceof Error ? err.message : String(err)
        dispatch({
          type: 'SET_ERROR',
          value:
            detail.includes('fetch') ||
            detail.includes('NetworkError') ||
            detail.includes('Failed to fetch')
              ? `Cannot reach the backend API at ${API_BASE || 'this origin'}.`
              : detail,
        })
        dispatch({ type: 'SET_LOADING', value: false })
        trackTraceEvent('workspace_search_error', { detail }, { level: 'warn' })
      }
    },
    [activateProject, handleUnauthorized, refreshProjectList]
  )

  const handleClarifyingAnswered = useCallback(() => {
    if (!state.projectId) return
    trackTraceEvent(
      'workspace_clarifying_answered',
      { project_id: state.projectId },
      { projectId: state.projectId }
    )
    startPollingForProject(state.projectId, 'clarifying_answered')
  }, [startPollingForProject, state.projectId])

  const handleSignOut = useCallback(() => {
    clearAuthSession()
    onSignOut()
  }, [onSignOut])

  // URL -> state sync (supports browser back/forward and direct links).
  useEffect(() => {
    const urlProjectId = normalizeProjectId(searchParams.get('projectId'))
    const urlPhase = searchParams.get('phase') as Phase | null

    if (urlProjectId === lastHandledUrlProjectRef.current) return
    lastHandledUrlProjectRef.current = urlProjectId

    if (!urlProjectId) {
      if (!activeProjectRef.current) return
      activeProjectRef.current = null
      invalidatePollingSession()
      clearPollingResources()
      dispatch({ type: 'RESET_ACTIVE_PROJECT' })
      return
    }

    if (urlProjectId === activeProjectRef.current) return

    trackTraceEvent(
      'workspace_project_loaded_from_url',
      {
        current_project_id: activeProjectRef.current,
        target_project_id: urlProjectId,
        target_phase: urlPhase,
      },
      { projectId: urlProjectId }
    )

    activateProject(urlProjectId, { source: 'url', syncUrl: false })

    // Apply phase from URL (e.g. dashboard "Review outreach →" link)
    if (urlPhase && PHASE_ORDER.includes(urlPhase)) {
      dispatch({ type: 'SET_ACTIVE_PHASE', phase: urlPhase, userDriven: true })
    }
  }, [activateProject, clearPollingResources, invalidatePollingSession, searchParams])

  useEffect(() => {
    void refreshProjectList()
  }, [refreshProjectList])

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, {
          signal: AbortSignal.timeout(3000),
        })
        dispatch({ type: 'SET_BACKEND_OK', value: res.ok })
      } catch {
        dispatch({ type: 'SET_BACKEND_OK', value: false })
      }
    }

    void checkHealth()
    const interval = setInterval(() => {
      void checkHealth()
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (state.backendOk == null) return

    if (backendHealthRef.current == null) {
      trackTraceEvent('backend_health_initial', { ok: state.backendOk })
    } else if (backendHealthRef.current !== state.backendOk) {
      trackTraceEvent(
        'backend_health_changed',
        { from: backendHealthRef.current, to: state.backendOk },
        { level: state.backendOk ? 'info' : 'warn' }
      )
    }

    backendHealthRef.current = state.backendOk
  }, [state.backendOk])

  useEffect(() => {
    return () => {
      invalidatePollingSession()
      clearPollingResources()
    }
  }, [clearPollingResources, invalidatePollingSession])

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      authUser,
      handleSignOut,
      projectId: state.projectId,
      setProjectId,
      projectList: state.projectList,
      projectListLoading: state.projectListLoading,
      status: state.status,
      loading: state.loading,
      polling: state.polling,
      activePhase: state.activePhase,
      setActivePhase: handleSetActivePhase,
      highestReachedPhase: state.highestReachedPhase,
      backendOk: state.backendOk,
      errorMessage: state.errorMessage,
      setErrorMessage,
      handleSearch,
      startNewProject,
      openProject,
      cancelCurrentProject,
      restartCurrentProject,
      handleClarifyingAnswered,
      refreshStatus,
      refreshProjectList,
    }),
    [
      authUser,
      cancelCurrentProject,
      handleSearch,
      handleSetActivePhase,
      handleSignOut,
      handleClarifyingAnswered,
      openProject,
      restartCurrentProject,
      refreshProjectList,
      refreshStatus,
      setErrorMessage,
      setProjectId,
      startNewProject,
      state.activePhase,
      state.backendOk,
      state.errorMessage,
      state.highestReachedPhase,
      state.loading,
      state.polling,
      state.projectId,
      state.projectList,
      state.projectListLoading,
      state.status,
    ]
  )

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}
