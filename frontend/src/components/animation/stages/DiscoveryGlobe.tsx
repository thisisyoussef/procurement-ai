'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { m } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO } from '@/lib/motion/config'
import GlobeSVG from '../globe/GlobeSVG'
import { useGlobeTimeline } from '../globe/useGlobeTimeline'
import { useStageProgress } from '../shared/useStageProgress'
import EventTickerOverlay from '../shared/EventTickerOverlay'
import AnimatedCounter from '../AnimatedCounter'

/**
 * Discovery Globe — hero animation for the "discovering" pipeline stage.
 *
 * Renders an SVG dot-matrix world map with animated arcs shooting from
 * center to each target region as progress events arrive. Supplier count
 * ticks up, event ticker shows latest search activity.
 */
export default function DiscoveryGlobe() {
  const {
    events,
    regions,
    activeRegion,
    supplierCount,
    latestDetail,
    latestSubstep,
    progressPct,
    isComplete,
  } = useStageProgress('discovering')
  const svgRef = useRef<SVGSVGElement | null>(null)
  const { animateArc, pulseAllDots, finalGlow } = useGlobeTimeline(svgRef)

  const [dotsReady, setDotsReady] = useState(false)
  const [activeRegions, setActiveRegions] = useState<string[]>([])
  const [searchingRegion, setSearchingRegion] = useState<string | null>(null)
  const animatedArcsRef = useRef(new Set<string>())
  const completeFired = useRef(false)

  // Dot ripple-in after a short delay
  useEffect(() => {
    const timer = setTimeout(() => setDotsReady(true), 300)
    return () => clearTimeout(timer)
  }, [])

  // React to new progress events → activate arcs
  const processEvents = useCallback(() => {
    for (const event of events) {
      // Regional search events → draw arc to that region
      const regionalMatch = event.detail.match(/for (.+?)-based/)
      if (regionalMatch) {
        const region = regionalMatch[1]
        if (!animatedArcsRef.current.has(region)) {
          animatedArcsRef.current.add(region)
          setSearchingRegion(region)
          setActiveRegions((prev) => (prev.includes(region) ? prev : [...prev, region]))

          // Small delay to let React render the path before GSAP animates it
          setTimeout(() => {
            animateArc(region, {
              duration: 0.6,
              onComplete: () => setSearchingRegion((cur) => (cur === region ? null : cur)),
            })
          }, 50)
        }
      }

      // Supplier memory / general search → pulse
      if (
        event.substep === 'searching_google' ||
        event.substep === 'searching_web' ||
        event.substep === 'searching_marketplaces'
      ) {
        pulseAllDots()
      }
    }

    // Fire final glow when discovery completes
    if (isComplete && !completeFired.current) {
      completeFired.current = true
      finalGlow?.()
    }
  }, [events, isComplete, animateArc, pulseAllDots, finalGlow])

  useEffect(() => {
    processEvents()
  }, [processEvents])

  // Use the hook's activeRegion for the currently-being-searched indicator
  useEffect(() => {
    if (activeRegion && !animatedArcsRef.current.has(activeRegion)) {
      setSearchingRegion(activeRegion)
    }
  }, [activeRegion])

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-4">
      {/* Active search phase label */}
      {latestSubstep && !isComplete && (
        <m.div
          key={latestSubstep}
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: DURATION.fast, ease: EASE_OUT_EXPO }}
          className="mb-3 px-3 py-1 bg-surface-2 border border-surface-3 rounded-full"
        >
          <p className="text-[10px] font-semibold tracking-[1px] uppercase text-ink-4">
            {latestSubstep === 'checking_memory' && 'Checking supplier memory'}
            {latestSubstep === 'searching_regional' && `Searching ${activeRegion || 'region'}`}
            {latestSubstep === 'searching_google' && 'Searching Google Places'}
            {latestSubstep === 'searching_web' && 'Searching the web'}
            {latestSubstep === 'searching_marketplaces' && 'Searching marketplaces'}
            {latestSubstep === 'deduplicating' && 'Removing duplicates'}
            {latestSubstep === 'complete' && 'Discovery complete'}
            {!['checking_memory', 'searching_regional', 'searching_google', 'searching_web', 'searching_marketplaces', 'deduplicating', 'complete'].includes(latestSubstep) && latestSubstep.replace(/_/g, ' ')}
          </p>
        </m.div>
      )}

      {/* Globe */}
      <m.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: DURATION.slow, ease: EASE_OUT_EXPO }}
        className="w-full max-w-[600px]"
      >
        <GlobeSVG
          activeRegions={activeRegions}
          targetRegions={regions}
          searchingRegion={searchingRegion}
          dotsReady={dotsReady}
          ref={svgRef}
        />
      </m.div>

      {/* Supplier counter + active regions */}
      <m.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: DURATION.normal, delay: 0.8, ease: EASE_OUT_EXPO }}
        className="mt-4 text-center"
      >
        <p className="text-[28px] font-semibold text-ink tabular-nums">
          <AnimatedCounter value={supplierCount} />
        </p>
        <p className="text-[12px] text-ink-3 mt-0.5">
          {supplierCount === 1 ? 'supplier found' : 'suppliers found'}
          {activeRegions.length > 0 && !isComplete && (
            <span className="text-ink-4"> across {activeRegions.length} region{activeRegions.length > 1 ? 's' : ''}</span>
          )}
        </p>
      </m.div>

      {/* Progress bar */}
      {progressPct !== null && (
        <m.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: DURATION.fast }}
          className="mt-3 w-full max-w-[300px]"
        >
          <div className="h-1 bg-surface-3 rounded-full overflow-hidden">
            <m.div
              className="h-full bg-teal rounded-full"
              initial={{ width: '0%' }}
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: DURATION.normal, ease: EASE_OUT_EXPO }}
            />
          </div>
        </m.div>
      )}

      {/* Event ticker */}
      <m.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: DURATION.normal, delay: 1.2 }}
        className="mt-4 w-full max-w-[400px]"
      >
        <EventTickerOverlay events={events} maxVisible={3} className="text-center" />
      </m.div>
    </div>
  )
}
