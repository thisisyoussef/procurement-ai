'use client'

import { Fragment } from 'react'

/* ────────────────────────────────────────────────────────
 * FunnelSummary — "34 found → 22 unique → 18 verified
 * → 8 compared → 3 recommended"
 *
 * One line that communicates more about the agent's work
 * than the entire old progress feed.
 * ──────────────────────────────────────────────────────── */

interface FunnelSummaryProps {
  totalRaw?: number
  deduplicated?: number
  verified?: number
  compared?: number
  recommended?: number
}

export default function FunnelSummary({
  totalRaw,
  deduplicated,
  verified,
  compared,
  recommended,
}: FunnelSummaryProps) {
  const steps = [
    { label: 'found', count: totalRaw },
    { label: 'unique', count: deduplicated },
    { label: 'verified', count: verified },
    { label: 'compared', count: compared },
    { label: 'recommended', count: recommended },
  ].filter((s) => s.count != null && s.count > 0)

  if (steps.length === 0) return null

  return (
    <div className="flex items-center gap-1 text-[11px] flex-wrap">
      {steps.map((step, i) => (
        <Fragment key={step.label}>
          <span className="text-ink-3">
            <span className="font-medium text-ink-2">{step.count}</span> {step.label}
          </span>
          {i < steps.length - 1 && <span className="text-ink-4 mx-0.5">&rarr;</span>}
        </Fragment>
      ))}
    </div>
  )
}
