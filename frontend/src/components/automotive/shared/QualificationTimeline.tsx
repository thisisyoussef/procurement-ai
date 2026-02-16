'use client'

import { useState } from 'react'
import { m, AnimatePresence, expandCollapse } from '@/lib/motion'
import type { QualificationEvent } from '@/types/automotive'

interface Props {
  events: QualificationEvent[]
  defaultOpen?: boolean
}

const EVENT_ICONS: Record<string, { icon: string; color: string }> = {
  auto_checks_complete: { icon: '🔍', color: 'text-blue-400' },
  data_gaps_identified: { icon: '📋', color: 'text-amber-400' },
  email_sent: { icon: '✉️', color: 'text-blue-400' },
  email_delivered: { icon: '📬', color: 'text-emerald-400' },
  email_opened: { icon: '👁', color: 'text-emerald-400' },
  email_bounced: { icon: '❌', color: 'text-red-400' },
  email_failed: { icon: '⚠️', color: 'text-red-400' },
  email_skipped: { icon: '⏭', color: 'text-zinc-500' },
  reply_received: { icon: '💬', color: 'text-emerald-400' },
  response_parsed: { icon: '✅', color: 'text-emerald-400' },
  status_upgraded: { icon: '⬆️', color: 'text-emerald-400' },
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ts
  }
}

export default function QualificationTimeline({ events, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen)

  if (!events || events.length === 0) return null

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <m.span
          animate={{ rotate: open ? 90 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-[10px]"
        >
          ▶
        </m.span>
        Timeline ({events.length} event{events.length !== 1 ? 's' : ''})
      </button>

      <AnimatePresence>
        {open && (
          <m.div
            variants={expandCollapse}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="overflow-hidden"
          >
            <div className="mt-2 ml-1 border-l border-zinc-800 pl-3 space-y-2">
              {events.map((evt, i) => {
                const meta = EVENT_ICONS[evt.event] || { icon: '·', color: 'text-zinc-500' }
                return (
                  <div key={`${evt.timestamp}-${i}`} className="flex items-start gap-2">
                    <span className={`text-xs flex-shrink-0 ${meta.color}`}>{meta.icon}</span>
                    <div className="min-w-0">
                      <p className="text-xs text-zinc-400 leading-relaxed">{evt.detail}</p>
                      <span className="text-[10px] text-zinc-600">{formatTimestamp(evt.timestamp)}</span>
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
