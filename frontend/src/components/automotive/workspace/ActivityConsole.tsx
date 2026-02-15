'use client'

import { useEffect, useRef, useState } from 'react'
import { automotiveClient } from '@/lib/automotive/client'

interface ActivityEvent {
  ts: number
  time: string
  stage: string
  action: string
  detail: string
  meta?: Record<string, unknown>
}

const ACTION_COLORS: Record<string, string> = {
  start: 'text-emerald-400',
  approved: 'text-amber-400',
  resuming: 'text-blue-400',
  paused: 'text-amber-300',
  error: 'text-red-400',
}

interface Props {
  projectId: string
}

export default function ActivityConsole({ projectId }: Props) {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const url = automotiveClient.getEventStreamUrl(projectId)
    const es = new EventSource(url)

    es.onopen = () => setConnected(true)

    es.onmessage = (e) => {
      try {
        const event: ActivityEvent = JSON.parse(e.data)
        setEvents((prev) => [...prev.slice(-200), event])
      } catch {
        // skip malformed events
      }
    }

    es.onerror = () => {
      setConnected(false)
    }

    return () => {
      es.close()
      setConnected(false)
    }
  }, [projectId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events])

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full px-4 py-2.5 flex items-center justify-between bg-zinc-900/80 hover:bg-zinc-900 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
          <span className="text-xs font-mono text-zinc-400">Activity Console</span>
          {events.length > 0 && (
            <span className="text-[10px] text-zinc-600 font-mono">{events.length} events</span>
          )}
        </div>
        <span className="text-zinc-600 text-xs">{collapsed ? '▶' : '▼'}</span>
      </button>

      {/* Log output */}
      {!collapsed && (
        <div
          ref={scrollRef}
          className="h-48 overflow-y-auto px-4 py-2 font-mono text-xs leading-relaxed"
        >
          {events.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <span className="text-zinc-600">Waiting for activity...</span>
            </div>
          )}
          {events.map((e, i) => (
            <div key={`${e.ts}-${i}`} className="flex gap-2 py-0.5">
              <span className="text-zinc-600 shrink-0">{e.time}</span>
              <span className="text-zinc-500 shrink-0">[{e.stage}]</span>
              <span className={ACTION_COLORS[e.action] || 'text-zinc-400'}>{e.detail}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
