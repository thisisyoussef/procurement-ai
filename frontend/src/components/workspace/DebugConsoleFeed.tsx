'use client'

import { useEffect, useMemo, useRef } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import { featureFlags } from '@/lib/featureFlags'

function formatTime(timestamp?: number): string {
  if (!timestamp) return '--:--:--'
  const date = new Date(timestamp * 1000)
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

export default function DebugConsoleFeed() {
  const { projectId, status } = useWorkspace()
  const endRef = useRef<HTMLDivElement | null>(null)

  const events = status?.progress_events || []
  const visibleEvents = useMemo(() => events.slice(-250), [events])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [visibleEvents.length])

  if (!featureFlags.tamkinDebugConsoleFeed || !projectId || !status) return null

  return (
    <div className="mx-6 mt-3 rounded-xl border border-surface-3 overflow-hidden">
      <div className="px-3 py-2 bg-ink text-white flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-[1px] font-mono">Live Console (Debug)</p>
        <p className="text-[10px] font-mono text-white/80">{visibleEvents.length} events</p>
      </div>

      <div className="max-h-56 overflow-y-auto bg-[#0f172a] px-3 py-2 font-mono text-[11px] leading-5">
        {visibleEvents.length === 0 ? (
          <p className="text-slate-400">Waiting for pipeline events...</p>
        ) : (
          visibleEvents.map((event, index) => (
            <p
              key={`${event.stage}-${event.substep}-${event.timestamp}-${index}`}
              className="text-slate-300 whitespace-pre-wrap break-words"
            >
              <span className="text-cyan-300">{formatTime(event.timestamp)}</span>{' '}
              <span className="text-emerald-300">[{event.stage}/{event.substep}]</span>{' '}
              {event.detail || '(no detail)'}
              {event.progress_pct !== null && event.progress_pct !== undefined
                ? ` (${Math.round(event.progress_pct)}%)`
                : ''}
            </p>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  )
}
