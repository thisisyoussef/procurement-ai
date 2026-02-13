'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { authFetch } from '@/lib/auth'
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
  pollingRef.current = polling

  const pollStatus = useCallback(
    async (id: string) => {
      try {
        const res = await authFetch(`${API_BASE}/api/v1/projects/${id}/status`)
        if (res.status === 401) {
          options?.onUnauthorized?.()
          return
        }
        if (!res.ok) return
        const data: PipelineStatus = await res.json()
        setStatus(data)

        if (data.status === 'complete' || data.status === 'failed') {
          setPolling(false)
          setLoading(false)
        }
        if (data.status === 'clarifying') {
          setPolling(false)
        }
      } catch (err) {
        console.error('Poll error:', err)
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
