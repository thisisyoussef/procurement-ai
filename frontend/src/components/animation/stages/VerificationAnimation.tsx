'use client'

import { useMemo } from 'react'
import { m, AnimatePresence } from '@/lib/motion'
import { DURATION, EASE_OUT_EXPO, STAGGER, SPRING_SNAPPY } from '@/lib/motion/config'
import { useStageProgress } from '../shared/useStageProgress'
import ProgressRing from '../shared/ProgressRing'
import AnimatedCounter from '../AnimatedCounter'
import EventTickerOverlay from '../shared/EventTickerOverlay'

interface SupplierTile {
  name: string
  verified: boolean
}

/**
 * Verification Animation — "Supplier Grid Check"
 *
 * Shows a grid of supplier tiles. As verification events arrive,
 * each tile's progress ring fills and a checkmark appears.
 */
export default function VerificationAnimation() {
  const { events, supplierNames, progressPct, supplierCount } = useStageProgress('verifying')

  // Build tile data: all discovered suppliers, marking verified ones
  const tiles: SupplierTile[] = useMemo(() => {
    // Use supplier names from verification events
    const verified = new Set(supplierNames)
    // Show up to 20 tiles
    const allNames = Array.from(verified)

    // If we know total count from progress events, pad with placeholders
    const totalMatch = events.find((e) => e.detail.match(/Verifying supplier \d+\/(\d+)/))
    const totalCount = totalMatch
      ? parseInt(totalMatch.detail.match(/Verifying supplier \d+\/(\d+)/)?.[1] || '0')
      : Math.max(supplierCount, allNames.length)

    const tiles: SupplierTile[] = allNames.map((name) => ({ name, verified: true }))

    // Add remaining unverified placeholders
    const remaining = Math.min(20, totalCount) - tiles.length
    for (let i = 0; i < remaining; i++) {
      tiles.push({ name: `Supplier ${tiles.length + 1}`, verified: false })
    }

    return tiles.slice(0, 20)
  }, [supplierNames, events, supplierCount])

  const verifiedCount = tiles.filter((t) => t.verified).length
  const totalCount = tiles.length

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-4">
      {/* Counter */}
      <m.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: DURATION.normal, ease: EASE_OUT_EXPO }}
        className="text-center mb-6"
      >
        <p className="text-[24px] font-semibold text-ink tabular-nums">
          <AnimatedCounter value={verifiedCount} />
          <span className="text-ink-4">/{totalCount}</span>
        </p>
        <p className="text-[12px] text-ink-3 mt-0.5">suppliers verified</p>
      </m.div>

      {/* Supplier grid */}
      <div className="grid grid-cols-4 sm:grid-cols-5 gap-3 max-w-[480px] w-full mb-6">
        <AnimatePresence>
          {tiles.map((tile, i) => (
            <m.div
              key={tile.name}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                duration: DURATION.fast,
                delay: i * STAGGER.fast,
                ease: EASE_OUT_EXPO,
              }}
              className={`relative flex flex-col items-center gap-1.5 p-2 rounded-lg border transition-colors ${
                tile.verified
                  ? 'border-teal/30 bg-teal/5'
                  : 'border-surface-3 bg-surface-2'
              }`}
            >
              <ProgressRing
                progress={tile.verified ? 100 : 0}
                size={32}
                strokeWidth={2}
              />

              {/* Checkmark overlay */}
              {tile.verified && (
                <m.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={SPRING_SNAPPY}
                  className="absolute top-1 right-1"
                >
                  <svg width={14} height={14} viewBox="0 0 14 14" className="text-teal">
                    <circle cx={7} cy={7} r={7} fill="currentColor" opacity={0.15} />
                    <path
                      d="M4 7l2 2 4-4"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={1.5}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </m.div>
              )}

              <p className="text-[9px] text-ink-3 text-center truncate w-full leading-tight">
                {tile.name}
              </p>
            </m.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Overall progress bar */}
      {progressPct !== null && (
        <m.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: DURATION.fast }}
          className="w-full max-w-[300px] mb-4"
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
      <EventTickerOverlay events={events} maxVisible={2} className="text-center max-w-[360px]" />
    </div>
  )
}
