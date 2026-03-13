'use client'

import { procurementClient } from '@/lib/api/procurementClient'
import { featureFlags } from '@/lib/featureFlags'

const TRACE_SESSION_KEY = 'procurement_trace_session_id'
const TRACE_PREFIX = '[procurement-trace]'

function truncate(value: string, max = 600): string {
  if (!value) return value
  if (value.length <= max) return value
  return `${value.slice(0, max)}...`
}

function normalizePayload(payload?: Record<string, unknown>): Record<string, unknown> {
  if (!payload) return {}
  const normalized: Record<string, unknown> = {}
  Object.entries(payload).forEach(([key, value]) => {
    if (typeof value === 'string') {
      normalized[key] = truncate(value)
      return
    }
    if (value instanceof Error) {
      normalized[key] = truncate(value.message || String(value))
      return
    }
    normalized[key] = value
  })
  return normalized
}

function nowIso(): string {
  return new Date().toISOString()
}

export function getTraceSessionId(): string | null {
  if (typeof window === 'undefined') return null

  const existing = localStorage.getItem(TRACE_SESSION_KEY)
  if (existing) return existing

  const created = `sess_${Math.random().toString(36).slice(2)}`
  localStorage.setItem(TRACE_SESSION_KEY, created)
  return created
}

export function traceConsole(
  eventName: string,
  payload: Record<string, unknown> = {},
  level: 'info' | 'warn' | 'error' = 'info'
): void {
  if (!featureFlags.procurementClientTracing) return

  const entry = {
    event: eventName,
    at: nowIso(),
    path:
      typeof window !== 'undefined'
        ? `${window.location.pathname}${window.location.search}`
        : undefined,
    payload: normalizePayload(payload),
  }

  if (level === 'warn') {
    console.warn(TRACE_PREFIX, entry)
    return
  }
  if (level === 'error') {
    console.error(TRACE_PREFIX, entry)
    return
  }
  console.info(TRACE_PREFIX, entry)
}

export function trackTraceEvent(
  eventName: string,
  payload: Record<string, unknown> = {},
  options: { path?: string; projectId?: string; level?: 'info' | 'warn' | 'error' } = {}
): void {
  const normalizedPayload = normalizePayload(payload)
  traceConsole(eventName, normalizedPayload, options.level || 'info')

  if (!featureFlags.procurementClientTracing) return

  const path =
    options.path ||
    (typeof window !== 'undefined'
      ? `${window.location.pathname}${window.location.search}`
      : undefined)

  void procurementClient
    .trackEvent({
      event_name: eventName,
      session_id: getTraceSessionId() || undefined,
      path,
      project_id: options.projectId,
      payload: normalizedPayload,
    })
    .catch((err: unknown) => {
      traceConsole(
        'telemetry_dispatch_error',
        { eventName, detail: err instanceof Error ? err.message : String(err) },
        'warn'
      )
    })
}
