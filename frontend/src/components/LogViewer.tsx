'use client'

import { useState, useEffect, useRef } from 'react'

import { withAccessTokenQuery } from '@/lib/auth'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface LogEntry {
  ts: number
  time: string
  level: string
  logger: string
  message: string
}

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: 'text-gray-400',
  INFO: 'text-green-400',
  WARNING: 'text-yellow-400',
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-500 font-bold',
}

const LEVEL_BADGES: Record<string, string> = {
  DEBUG: 'bg-gray-700 text-gray-300',
  INFO: 'bg-green-900 text-green-300',
  WARNING: 'bg-yellow-900 text-yellow-300',
  ERROR: 'bg-red-900 text-red-300',
  CRITICAL: 'bg-red-800 text-red-200',
}

export default function LogViewer({
  projectId,
  isActive,
}: {
  projectId: string | null
  isActive: boolean
}) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isOpen, setIsOpen] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const [filter, setFilter] = useState<string>('ALL')
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Connect to SSE when projectId is set
  useEffect(() => {
    if (!projectId) return

    setLogs([]) // Clear on new project

    const eventSource = new EventSource(
      withAccessTokenQuery(`${API_BASE}/api/v1/projects/${projectId}/logs/stream`)
    )

    eventSource.onmessage = (event) => {
      try {
        const entry: LogEntry = JSON.parse(event.data)
        setLogs((prev) => [...prev, entry])
      } catch {
        // Ignore parse errors
      }
    }

    eventSource.onerror = () => {
      // SSE will auto-reconnect; no action needed
    }

    return () => {
      eventSource.close()
    }
  }, [projectId])

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  // Detect manual scroll
  const handleScroll = () => {
    if (!containerRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
    setAutoScroll(isAtBottom)
  }

  const filteredLogs =
    filter === 'ALL' ? logs : logs.filter((l) => l.level === filter)

  if (!projectId) return null

  return (
    <div className="mt-6 rounded-lg border border-slate-700 bg-slate-900 overflow-hidden shadow-lg">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
        >
          <span
            className={`transition-transform ${isOpen ? 'rotate-90' : ''}`}
          >
            ▶
          </span>
          Live Logs
          <span className="text-xs bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">
            {logs.length}
          </span>
          {isActive && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
          )}
        </button>

        <div className="flex items-center gap-2">
          {/* Level filter */}
          <div className="flex gap-1">
            {['ALL', 'INFO', 'WARNING', 'ERROR'].map((level) => (
              <button
                key={level}
                onClick={() => setFilter(level)}
                className={`text-xs px-2 py-0.5 rounded transition-colors ${
                  filter === level
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                }`}
              >
                {level}
              </button>
            ))}
          </div>

          {/* Clear */}
          <button
            onClick={() => setLogs([])}
            className="text-xs text-slate-500 hover:text-slate-300 px-2 py-0.5"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Log content */}
      {isOpen && (
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="max-h-80 overflow-y-auto font-mono text-xs leading-relaxed"
        >
          {filteredLogs.length === 0 ? (
            <div className="px-4 py-8 text-center text-slate-500">
              {isActive
                ? 'Waiting for pipeline logs...'
                : 'No logs yet. Start a search to see live pipeline output.'}
            </div>
          ) : (
            <table className="w-full">
              <tbody>
                {filteredLogs.map((entry, i) => (
                  <tr
                    key={i}
                    className="hover:bg-slate-800/50 border-b border-slate-800/30"
                  >
                    <td className="px-3 py-1 text-slate-500 whitespace-nowrap align-top w-16">
                      {entry.time}
                    </td>
                    <td className="px-1 py-1 whitespace-nowrap align-top w-16">
                      <span
                        className={`inline-block text-center px-1.5 py-0 rounded text-[10px] font-medium ${
                          LEVEL_BADGES[entry.level] || 'bg-slate-700 text-slate-400'
                        }`}
                      >
                        {entry.level}
                      </span>
                    </td>
                    <td className="px-1 py-1 text-blue-400 whitespace-nowrap align-top w-40 truncate max-w-[160px]">
                      {entry.logger}
                    </td>
                    <td
                      className={`px-2 py-1 ${
                        LEVEL_COLORS[entry.level] || 'text-slate-300'
                      } break-words`}
                    >
                      {entry.message}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
