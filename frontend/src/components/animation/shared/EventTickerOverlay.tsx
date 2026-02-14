'use client'

import { useMemo } from 'react'
import { AnimatePresence, m } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO } from '@/lib/motion/config'

interface ProgressEvent {
  stage: string
  substep: string
  detail: string
  timestamp: number
}

interface EventTickerOverlayProps {
  events: ProgressEvent[]
  maxVisible?: number
  className?: string
}

export default function EventTickerOverlay({
  events,
  maxVisible = 3,
  className = '',
}: EventTickerOverlayProps) {
  const recent = useMemo(
    () => [...events].slice(-maxVisible).reverse(),
    [events, maxVisible],
  )

  if (recent.length === 0) return null

  return (
    <div className={`space-y-1.5 ${className}`}>
      <AnimatePresence mode="popLayout">
        {recent.map((event, i) => (
          <m.p
            key={`${event.substep}-${event.timestamp}`}
            initial={{ opacity: 0, y: 10, filter: 'blur(4px)' }}
            animate={{
              opacity: i === 0 ? 1 : 0.5,
              y: 0,
              filter: 'blur(0px)',
            }}
            exit={{ opacity: 0, y: -8, filter: 'blur(4px)' }}
            transition={{ duration: DURATION.fast, ease: EASE_OUT_EXPO }}
            className="text-[11px] text-ink-3 truncate"
          >
            {event.detail}
          </m.p>
        ))}
      </AnimatePresence>
    </div>
  )
}
