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
  const { events, regions, supplierCount, latestDetail } = useStageProgress('discovering')
  const svgRef = useRef<SVGSVGElement | null>(null)
  const { animateArc, pulseAllDots } = useGlobeTimeline(svgRef)

  const [dotsReady, setDotsReady] = useState(false)
  const [activeRegions, setActiveRegions] = useState<string[]>([])
  const [searchingRegion, setSearchingRegion] = useState<string | null>(null)
  const animatedArcsRef = useRef(new Set<string>())

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
  }, [events, animateArc, pulseAllDots])

  useEffect(() => {
    processEvents()
  }, [processEvents])

  // Also activate regions from parsed_requirements that arrive before discovery events
  useEffect(() => {
    if (regions.length > 0 && activeRegions.length === 0) {
      // Pre-populate target regions but don't draw arcs yet — wait for events
    }
  }, [regions, activeRegions.length])

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-4">
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

      {/* Supplier counter */}
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
        </p>
      </m.div>

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
