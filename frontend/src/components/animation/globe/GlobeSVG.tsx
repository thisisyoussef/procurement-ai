'use client'

import { forwardRef, useMemo } from 'react'
import { m } from '@/lib/motion'
import { WORLD_MAP_DOTS } from './worldMapDots'
import { resolveRegion, CENTER_POINT, type RegionPoint } from './regionCoordinates'

interface ArcData {
  id: string
  target: RegionPoint
  active: boolean
}

interface GlobeSVGProps {
  /** Region names that have been activated (arc drawn + ping) */
  activeRegions: string[]
  /** All known target regions (dim dots shown from the start) */
  targetRegions: string[]
  /** Region currently being searched (brighter arc animation) */
  searchingRegion: string | null
  /** Whether the initial dot ripple has completed */
  dotsReady: boolean
  className?: string
}

/** Generate a quadratic bezier arc path from center to target */
function arcPath(cx: number, cy: number, tx: number, ty: number): string {
  // Control point: lift the arc upward for a nice curve
  const mx = (cx + tx) / 2
  const my = Math.min(cy, ty) - Math.abs(tx - cx) * 0.2 - 30
  return `M ${cx} ${cy} Q ${mx} ${my} ${tx} ${ty}`
}

/** Distance from center for ripple delay */
function distFromCenter(x: number, y: number): number {
  const dx = x - CENTER_POINT.x
  const dy = y - CENTER_POINT.y
  return Math.sqrt(dx * dx + dy * dy)
}

const GlobeSVG = forwardRef<SVGSVGElement, GlobeSVGProps>(function GlobeSVG(
  { activeRegions, targetRegions, searchingRegion, dotsReady, className = '' },
  svgRef,
) {

  // Resolve target regions to coordinates
  const targetPoints = useMemo(() => {
    const points: RegionPoint[] = []
    for (const name of targetRegions) {
      const pt = resolveRegion(name)
      if (pt) points.push(pt)
    }
    return points
  }, [targetRegions])

  // Build arc data
  const arcs: ArcData[] = useMemo(() => {
    const seen = new Set<string>()
    return targetRegions
      .map((name) => {
        const pt = resolveRegion(name)
        if (!pt || seen.has(pt.label)) return null
        seen.add(pt.label)
        return {
          id: pt.label,
          target: pt,
          active: activeRegions.includes(name),
        }
      })
      .filter(Boolean) as ArcData[]
  }, [targetRegions, activeRegions])

  // Pre-compute dot distances for stagger
  const dotDelays = useMemo(
    () => WORLD_MAP_DOTS.map((d) => distFromCenter(d.x, d.y) / 800),
    [],
  )

  // Check which dots are near active regions (within 40px)
  const activeDotIndices = useMemo(() => {
    const indices = new Set<number>()
    for (const region of activeRegions) {
      const pt = resolveRegion(region)
      if (!pt) continue
      WORLD_MAP_DOTS.forEach((dot, i) => {
        const dx = dot.x - pt.x
        const dy = dot.y - pt.y
        if (dx * dx + dy * dy < 1600) indices.add(i) // 40px radius
      })
    }
    return indices
  }, [activeRegions])

  return (
    <svg
      ref={svgRef}
      viewBox="0 0 800 400"
      className={`w-full max-w-[700px] mx-auto ${className}`}
      aria-hidden="true"
    >
      {/* Layer 1: Dot matrix — continental outlines */}
      <g className="globe-dots">
        {WORLD_MAP_DOTS.map((dot, i) => (
          <m.circle
            key={i}
            cx={dot.x}
            cy={dot.y}
            r={1.2}
            initial={{ opacity: 0 }}
            animate={{
              opacity: dotsReady ? (activeDotIndices.has(i) ? 0.7 : 0.18) : 0,
            }}
            transition={{
              duration: dotsReady ? 0.6 : 0.3,
              delay: dotsReady ? dotDelays[i] * 0.8 : 0,
              ease: 'easeOut',
            }}
            className={activeDotIndices.has(i) ? 'fill-teal' : 'fill-ink-4'}
          />
        ))}
      </g>

      {/* Layer 2: Arc lines from center to each target region */}
      <g className="globe-arcs">
        {arcs.map((arc) => {
          const d = arcPath(CENTER_POINT.x, CENTER_POINT.y, arc.target.x, arc.target.y)
          const isSearching = searchingRegion === arc.id
          return (
            <g key={arc.id}>
              {/* Trail glow */}
              {arc.active && (
                <path
                  d={d}
                  fill="none"
                  stroke="var(--color-teal)"
                  strokeWidth={2}
                  strokeOpacity={0.15}
                  className="globe-arc-glow"
                />
              )}
              {/* Main arc — animated via GSAP stroke-dashoffset (class target) */}
              <path
                d={d}
                fill="none"
                stroke="var(--color-teal)"
                strokeWidth={isSearching ? 1.8 : 1.2}
                strokeOpacity={arc.active ? 0.8 : 0}
                strokeLinecap="round"
                className={`globe-arc globe-arc-${arc.id.replace(/\s/g, '-')}`}
                data-region={arc.id}
              />
            </g>
          )
        })}
      </g>

      {/* Layer 3: Ping rings at destinations */}
      <g className="globe-pings">
        {arcs
          .filter((a) => a.active)
          .map((arc) => (
            <g key={`ping-${arc.id}`}>
              {/* Expanding ring */}
              <m.circle
                cx={arc.target.x}
                cy={arc.target.y}
                r={3}
                fill="none"
                stroke="var(--color-teal)"
                strokeWidth={1.5}
                initial={{ r: 3, opacity: 0.8 }}
                animate={{ r: 16, opacity: 0 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
              />
              {/* Solid dot */}
              <m.circle
                cx={arc.target.x}
                cy={arc.target.y}
                r={3}
                className="fill-teal"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              />
            </g>
          ))}

        {/* Center dot (Tamkin) */}
        <circle
          cx={CENTER_POINT.x}
          cy={CENTER_POINT.y}
          r={4}
          className="fill-teal"
          opacity={dotsReady ? 0.9 : 0}
        />
        <m.circle
          cx={CENTER_POINT.x}
          cy={CENTER_POINT.y}
          r={4}
          fill="none"
          stroke="var(--color-teal)"
          strokeWidth={1}
          initial={{ r: 4, opacity: 0.6 }}
          animate={{ r: 20, opacity: 0 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
        />
      </g>

      {/* Layer 4: Region labels */}
      <g className="globe-labels">
        {arcs
          .filter((a) => a.active)
          .map((arc) => (
            <m.text
              key={`label-${arc.id}`}
              x={arc.target.x}
              y={arc.target.y - 12}
              textAnchor="middle"
              className="fill-ink-2 text-[9px] font-medium"
              initial={{ opacity: 0, y: arc.target.y - 6 }}
              animate={{ opacity: 1, y: arc.target.y - 12 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            >
              {arc.target.label}
            </m.text>
          ))}
      </g>
    </svg>
  )
})

export default GlobeSVG
