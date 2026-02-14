'use client'

import { m, AnimatePresence } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO, STAGGER } from '@/lib/motion/config'
import { useStageProgress } from '../shared/useStageProgress'
import EventTickerOverlay from '../shared/EventTickerOverlay'
import ProgressRing from '../shared/ProgressRing'

/**
 * Parsing Animation — "Document Deconstruction"
 *
 * Shows the user's brief being analyzed: key phrases lift out into
 * structured rows, region names appear as teal pills.
 * Driven by real-time progress events from the parsing agent.
 */
export default function ParsingAnimation() {
  const {
    events,
    regions,
    latestDetail,
    latestSubstep,
    progressPct,
    productType,
    quantity,
    searchQueryCount,
    isComplete,
  } = useStageProgress('parsing')

  // Build structured data pills from real-time extracted fields
  const dataFields: Array<{ label: string; value: string }> = []
  if (productType) dataFields.push({ label: 'Product', value: productType })
  if (quantity) dataFields.push({ label: 'Quantity', value: quantity })
  if (searchQueryCount > 0) dataFields.push({ label: 'Queries', value: `${searchQueryCount} search queries generated` })

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-6">
      {/* Central pulsing orb with progress ring */}
      <m.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: DURATION.slow, ease: EASE_OUT_EXPO }}
        className="relative w-24 h-24 mb-8 flex items-center justify-center"
      >
        {/* Progress ring behind the icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <ProgressRing
            progress={progressPct ?? (isComplete ? 100 : 15)}
            size={96}
            strokeWidth={2}
          />
        </div>

        {/* Radial gradient pulse */}
        {!isComplete && (
          <m.div
            className="absolute inset-0 rounded-full bg-teal/10"
            animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0.1, 0.3] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}

        {/* Center icon */}
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
          animate={{ opacity: 1, rotate: isComplete ? 0 : 0 }}
          transition={{ duration: DURATION.normal, delay: 0.3 }}
        >
          {isComplete ? (
            <path d="M9 12l2 2 4-4M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" />
          ) : (
            <>
              <path d="M9 12h6M9 16h6M13 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V11l-8-8z" />
              <path d="M13 3v8h8" />
            </>
          )}
        </m.svg>
      </m.div>

      {/* Current substep label */}
      {latestSubstep && !isComplete && (
        <m.div
          key={latestSubstep}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 px-3 py-1 bg-surface-2 border border-surface-3 rounded-full"
        >
          <p className="text-[10px] font-semibold tracking-[1px] uppercase text-ink-4">
            {latestSubstep === 'starting' && 'Analyzing Brief'}
            {latestSubstep === 'structuring' && 'Structuring Requirements'}
            {latestSubstep === 'product_identified' && 'Product Identified'}
            {latestSubstep === 'identifying_regions' && 'Finding Regions'}
            {latestSubstep === 'complete' && 'Analysis Complete'}
            {!['starting', 'structuring', 'product_identified', 'identifying_regions', 'complete'].includes(latestSubstep) && latestSubstep.replace(/_/g, ' ')}
          </p>
        </m.div>
      )}

      {/* Extracted data fields — real data from the hook */}
      <div className="space-y-2 mb-6 min-h-[60px]">
        <AnimatePresence>
          {dataFields.map((field, i) => (
            <m.div
              key={field.label}
              initial={{ opacity: 0, x: -20, filter: 'blur(4px)' }}
              animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
              transition={{
                duration: DURATION.normal,
                delay: i * STAGGER.slow,
                ease: EASE_OUT_EXPO,
              }}
              className="flex items-center gap-2"
            >
              <span className="text-[10px] font-semibold tracking-wider uppercase text-ink-4 w-16 text-right shrink-0">
                {field.label}
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0" />
              <span className="text-[13px] text-ink-2 font-medium">{field.value}</span>
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
          <p className="w-full text-center text-[10px] font-semibold tracking-[1px] uppercase text-ink-4 mb-1">
            Target Regions
          </p>
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
      <EventTickerOverlay events={events} maxVisible={3} className="text-center max-w-[360px]" />
    </div>
  )
}
