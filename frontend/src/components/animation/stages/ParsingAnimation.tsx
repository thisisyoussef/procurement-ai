'use client'

import { useMemo } from 'react'
import { m, AnimatePresence } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO, STAGGER } from '@/lib/motion/config'
import { useStageProgress } from '../shared/useStageProgress'
import EventTickerOverlay from '../shared/EventTickerOverlay'

/**
 * Parsing Animation — "Document Deconstruction"
 *
 * Shows the user's brief being analyzed: key phrases lift out into
 * structured rows, region names appear as teal pills.
 */
export default function ParsingAnimation() {
  const { events, regions, latestDetail } = useStageProgress('parsing')

  const extractedPhrases = useMemo(() => {
    const phrases: string[] = []
    for (const event of events) {
      // "Identified product type: industrial valves"
      const productMatch = event.detail.match(/product type: (.+)/i)
      if (productMatch) phrases.push(productMatch[1])

      // "Identified quantity: 5000 units"
      const qtyMatch = event.detail.match(/quantity: (.+)/i)
      if (qtyMatch) phrases.push(qtyMatch[1])

      // "Quality requirements: ISO 9001"
      const qualityMatch = event.detail.match(/requirements?: (.+)/i)
      if (qualityMatch) phrases.push(qualityMatch[1])
    }
    return phrases.slice(0, 4) // Max 4 phrases
  }, [events])

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-6">
      {/* Central pulsing orb */}
      <m.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: DURATION.slow, ease: EASE_OUT_EXPO }}
        className="relative w-24 h-24 mb-8"
      >
        {/* Radial gradient pulse */}
        <m.div
          className="absolute inset-0 rounded-full bg-teal/10"
          animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0.1, 0.3] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
        />
        <m.div
          className="absolute inset-2 rounded-full bg-teal/15"
          animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0.2, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
        />
        {/* Center icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <m.svg
            width={32}
            height={32}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            strokeLinecap="round"
            className="text-teal"
            initial={{ opacity: 0, rotate: -10 }}
            animate={{ opacity: 1, rotate: 0 }}
            transition={{ duration: DURATION.normal, delay: 0.3 }}
          >
            <path d="M9 12h6M9 16h6M13 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V11l-8-8z" />
            <path d="M13 3v8h8" />
          </m.svg>
        </div>
      </m.div>

      {/* Extracted phrases float out */}
      <div className="space-y-2 mb-6 min-h-[80px]">
        <AnimatePresence>
          {extractedPhrases.map((phrase, i) => (
            <m.div
              key={phrase}
              initial={{ opacity: 0, x: -20, filter: 'blur(4px)' }}
              animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
              transition={{
                duration: DURATION.normal,
                delay: i * STAGGER.slow,
                ease: EASE_OUT_EXPO,
              }}
              className="flex items-center gap-2"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0" />
              <span className="text-[13px] text-ink-2 font-medium">{phrase}</span>
            </m.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Region pills */}
      {regions.length > 0 && (
        <m.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: DURATION.normal, delay: 0.6, ease: EASE_OUT_EXPO }}
          className="flex flex-wrap justify-center gap-2 mb-6"
        >
          {regions.map((region, i) => (
            <m.span
              key={region}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                duration: DURATION.fast,
                delay: 0.8 + i * STAGGER.normal,
                ease: EASE_OUT_EXPO,
              }}
              className="px-2.5 py-1 text-[11px] font-medium text-teal bg-teal/10 rounded-full"
            >
              {region}
            </m.span>
          ))}
        </m.div>
      )}

      {/* Status text */}
      <m.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: DURATION.normal, delay: 0.4 }}
        className="text-[13px] text-ink-3 text-center mb-3"
      >
        {latestDetail || 'Analyzing your requirements...'}
      </m.p>

      {/* Event ticker */}
      <EventTickerOverlay events={events} maxVisible={2} className="text-center max-w-[360px]" />
    </div>
  )
}
