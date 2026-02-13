'use client'

import { usePathname } from 'next/navigation'
import { useEffect, useRef } from 'react'

import { trackTraceEvent } from '@/lib/telemetry'

function formatReason(reason: unknown): string {
  if (reason instanceof Error) return reason.message
  if (typeof reason === 'string') return reason
  try {
    return JSON.stringify(reason)
  } catch {
    return String(reason)
  }
}

export default function RouteTrace() {
  const pathname = usePathname()
  const previousPathRef = useRef<string | null>(null)

  useEffect(() => {
    const query = typeof window !== 'undefined' ? window.location.search.replace(/^\?/, '') : ''
    const current = query ? `${pathname}?${query}` : pathname
    const previous = previousPathRef.current

    if (!previous) {
      trackTraceEvent('page_view', { to: current }, { path: current })
    } else if (previous !== current) {
      trackTraceEvent(
        'page_change',
        { from: previous, to: current },
        { path: current }
      )
    }

    previousPathRef.current = current
  }, [pathname])

  useEffect(() => {
    const onError = (event: ErrorEvent) => {
      trackTraceEvent(
        'client_error',
        {
          message: event.message,
          source: event.filename,
          line: event.lineno,
          column: event.colno,
          stack: event.error?.stack || undefined,
        },
        { level: 'error' }
      )
    }

    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      trackTraceEvent(
        'client_unhandled_rejection',
        { reason: formatReason(event.reason) },
        { level: 'error' }
      )
    }

    window.addEventListener('error', onError)
    window.addEventListener('unhandledrejection', onUnhandledRejection)
    return () => {
      window.removeEventListener('error', onError)
      window.removeEventListener('unhandledrejection', onUnhandledRejection)
    }
  }, [])

  return null
}
