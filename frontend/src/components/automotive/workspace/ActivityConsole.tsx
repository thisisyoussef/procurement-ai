'use client'

import { useEffect, useRef, useState } from 'react'
import { m, AnimatePresence, expandCollapse } from '@/lib/motion'
import { automotiveClient } from '@/lib/automotive/client'

interface ActivityEvent {
  ts: number
  time: string
  stage: string
  action: string
  detail: string
  meta?: Record<string, unknown>
}

type FilterType = 'all' | 'approvals' | 'agents' | 'errors'

const ACTION_COLORS: Record<string, string> = {
  start: 'text-emerald-400',
  approved: 'text-amber-400',
  resuming: 'text-blue-400',
  paused: 'text-amber-300',
  error: 'text-red-400',
  complete: 'text-emerald-400',
  warning: 'text-amber-400',
}

const ACTION_ICONS: Record<string, string> = {
  start: '▶',
  approved: '✓',
  resuming: '↻',
  paused: '⏸',
  error: '✕',
  complete: '★',
  warning: '⚠',
}

const FILTER_RULES: Record<FilterType, (e: ActivityEvent) => boolean> = {
  all: () => true,
  approvals: (e) => e.action === 'approved' || e.action === 'paused',
  agents: (e) => e.action === 'start' || e.action === 'resuming' || e.action === 'complete',
  errors: (e) => e.action === 'error' || e.action === 'warning',
}

interface Props {
  projectId: string
}

export default function ActivityConsole({ projectId }: Props) {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [filter, setFilter] = useState<FilterType>('all')
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

  const filteredEvents = events.filter(FILTER_RULES[filter])
  const errorCount = events.filter(e => e.action === 'error').length

  const filters: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'approvals', label: 'Approvals' },
    { key: 'agents', label: 'Agents' },
    { key: 'errors', label: 'Errors' },
  ]

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full px-4 py-2.5 flex items-center justify-between bg-zinc-900/80 hover:bg-zinc-900 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-600'}`} />
          <span className="text-xs font-medium text-zinc-400">Pipeline Activity</span>
          {events.length > 0 && (
            <span className="text-[10px] text-zinc-600">{events.length} events</span>
          )}
          {errorCount > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-400">
              {errorCount} error{errorCount > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <m.span
          className="text-zinc-600 text-xs"
          animate={{ rotate: collapsed ? -90 : 0 }}
          transition={{ duration: 0.2 }}
        >
          ▼
        </m.span>
      </button>

      {/* Content — animated collapse */}
      <AnimatePresence>
        {!collapsed && (
          <m.div
            variants={expandCollapse}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="overflow-hidden"
          >
            {/* Filter chips */}
            <div className="px-4 py-2 border-t border-zinc-800/50 flex gap-1.5">
              {filters.map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setFilter(key)}
                  className={`px-2.5 py-1 text-[10px] rounded-full transition-colors ${
                    filter === key
                      ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                      : 'text-zinc-600 hover:text-zinc-400 border border-transparent'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Event list */}
            <div
              ref={scrollRef}
              className="h-48 overflow-y-auto px-4 py-2"
            >
              {filteredEvents.length === 0 && (
                <div className="flex items-center justify-center h-full">
                  <span className="text-zinc-600 text-xs">
                    {events.length === 0 ? 'Waiting for activity...' : `No ${filter} events`}
                  </span>
                </div>
              )}
              {filteredEvents.map((e, i) => {
                const icon = ACTION_ICONS[e.action] || '·'
                const colorClass = ACTION_COLORS[e.action] || 'text-zinc-400'

                return (
                  <div key={`${e.ts}-${i}`} className="flex items-start gap-2.5 py-1.5 group">
                    {/* Icon */}
                    <span className={`w-4 h-4 flex items-center justify-center text-[10px] rounded ${colorClass} bg-zinc-800/50 flex-shrink-0 mt-0.5`}>
                      {icon}
                    </span>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-zinc-300 leading-relaxed">{e.detail}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-zinc-600">{e.time}</span>
                        <span className="text-[10px] px-1.5 py-0 rounded bg-zinc-800/80 text-zinc-600">{e.stage}</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  )
}
