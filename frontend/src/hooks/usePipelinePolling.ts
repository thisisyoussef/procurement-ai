'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { authFetch } from '@/lib/auth'
import { trackTraceEvent } from '@/lib/telemetry'
import { PipelineStatus } from '@/types/pipeline'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface UsePipelinePollingOptions {
  onUnauthorized?: () => void
}

export function usePipelinePolling(
  projectId: string | null,
  options?: UsePipelinePollingOptions
) {
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [polling, setPolling] = useState(false)
  const [loading, setLoading] = useState(false)
  const pollingRef = useRef(polling)
  const activeProjectIdRef = useRef<string | null>(projectId)
  const requestSeqRef = useRef(0)
  const appliedSeqRef = useRef(0)
  pollingRef.current = polling
  activeProjectIdRef.current = projectId

  const pollStatus = useCallback(
    async (id: string) => {
      const seq = ++requestSeqRef.current
      try {
        const res = await authFetch(`${API_BASE}/api/v1/projects/${id}/status`)
        if (res.status === 401) {
          options?.onUnauthorized?.()
          return
        }
        if (!res.ok) return
        const data: PipelineStatus = await res.json()

        // Ignore stale responses from a previously selected project.
        if (activeProjectIdRef.current !== id) {
          trackTraceEvent(
            'poll_status_ignored_stale_project',
            {
              requested_project_id: id,
              active_project_id: activeProjectIdRef.current,
              seq,
            },
            { projectId: activeProjectIdRef.current || undefined }
          )
          return
        }

        // Ignore out-of-order responses where a newer poll already applied.
        if (seq < appliedSeqRef.current) {
          trackTraceEvent(
            'poll_status_ignored_out_of_order',
            {
              project_id: id,
              seq,
              applied_seq: appliedSeqRef.current,
            },
            { projectId: id }
          )
          return
        }

        appliedSeqRef.current = seq
        setStatus(data)

        if (
          data.status === 'complete' ||
          data.status === 'failed' ||
          data.status === 'canceled'
        ) {
          setPolling(false)
          setLoading(false)
        }
        if (data.status === 'clarifying') {
          setPolling(false)
        }
      } catch (err) {
        console.error('Poll error:', err)
        trackTraceEvent(
          'poll_status_error',
          {
            project_id: id,
            detail: err instanceof Error ? err.message : String(err),
          },
          { projectId: id, level: 'warn' }
        )
      }
    },
    [options?.onUnauthorized]
  )

  const refreshStatus = useCallback(() => {
    if (projectId) pollStatus(projectId)
  }, [projectId, pollStatus])

  const startPolling = useCallback(() => {
    setPolling(true)
    setLoading(true)
  }, [])

  const stopPolling = useCallback(() => {
    setPolling(false)
    setLoading(false)
  }, [])

  useEffect(() => {
    // Reset sequencing when switching projects to avoid cross-project race behavior.
    requestSeqRef.current = 0
    appliedSeqRef.current = 0
  }, [projectId])

  useEffect(() => {
    if (!polling || !projectId) return
    // Immediate first poll
    pollStatus(projectId)
    const interval = setInterval(() => {
      if (pollingRef.current) pollStatus(projectId)
    }, 1000)
    return () => clearInterval(interval)
  }, [polling, projectId, pollStatus])

  return {
    status,
    setStatus,
    loading,
    setLoading,
    polling,
    setPolling,
    startPolling,
    stopPolling,
    refreshStatus,
    pollStatus,
  }
}
