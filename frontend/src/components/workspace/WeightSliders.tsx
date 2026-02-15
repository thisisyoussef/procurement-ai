'use client'

import { useMemo } from 'react'

interface WeightSlidersProps {
  weights: Record<string, number>
  onChange: (weights: Record<string, number>) => void
}

const DEFAULT_WEIGHTS: Record<string, number> = {
  cost: 30,
  quality: 30,
  speed: 20,
  risk: 20,
}

const LABELS: Record<string, string> = {
  cost: 'Price',
  quality: 'Quality',
  speed: 'Speed',
  risk: 'Risk',
  proximity: 'Proximity',
}

export default function WeightSliders({ weights, onChange }: WeightSlidersProps) {
  const merged = useMemo(
    () => ({
      ...DEFAULT_WEIGHTS,
      ...Object.fromEntries(
        Object.entries(weights || {}).map(([key, value]) => [key, Number(value) || 0])
      ),
    }),
    [weights]
  )

  const keys = Object.keys(merged)
  const total = keys.reduce((sum, key) => sum + merged[key], 0)

  return (
    <div className="rounded-xl border border-surface-3 bg-white px-3 py-3">
      <p className="text-[12px] font-semibold text-ink">Priority weighting</p>
      <div className="mt-2 space-y-2.5">
        {keys.map((key) => {
          const label = LABELS[key] || key
          const value = merged[key]
          return (
            <label key={key} className="block">
              <div className="mb-1 flex items-center justify-between text-[11px]">
                <span className="text-ink-3">{label}</span>
                <span className="font-medium text-ink-2">{Math.round(value)}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={value}
                onChange={(event) =>
                  onChange({
                    ...merged,
                    [key]: Number(event.target.value) || 0,
                  })
                }
                className="w-full accent-teal"
              />
            </label>
          )
        })}
      </div>
      <p className="mt-2 text-[10px] text-ink-4">
        Total: {Math.round(total)}% (weights are treated as relative signals)
      </p>
    </div>
  )
}
