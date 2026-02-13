'use client'

import { useMemo } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'

function ScoreBar({ score, label, compact }: { score: number; label: string; compact?: boolean }) {
  return (
    <div>
      <div className="flex justify-between text-[10px] mb-1">
        <span className="text-ink-4">{label}</span>
        <span className="font-medium text-ink-2">{Math.round(score)}</span>
      </div>
      <div className="score-bar">
        <div className="score-bar-fill" style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
    </div>
  )
}

function getInitials(name: string): string {
  return name
    .split(/[\s&]+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
}

export default function ComparePhase() {
  const { status, loading } = useWorkspace()

  const comparison = status?.comparison_result
  const recommendation = status?.recommendation
  const suppliers = status?.discovery_results?.suppliers
  const verifications = status?.verification_results

  const verificationMap = useMemo(() => {
    const map = new Map<string, any>()
    if (verifications?.verifications) {
      for (const v of verifications.verifications) map.set(v.supplier_name, v)
    }
    return map
  }, [verifications])

  const comparisonMap = useMemo(() => {
    const map = new Map<string, any>()
    if (comparison?.comparisons) {
      for (const c of comparison.comparisons) map.set(c.supplier_name, c)
    }
    return map
  }, [comparison])

  // Loading
  if (!comparison && !recommendation) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] px-6">
        {loading ? (
          <>
            <span className="status-dot bg-teal animate-pulse-dot mb-4" style={{ width: 10, height: 10 }} />
            <p className="text-[14px] text-ink-2 font-medium">
              {status?.current_stage === 'comparing'
                ? 'Comparing suppliers side by side...'
                : status?.current_stage === 'recommending'
                ? 'Generating recommendations...'
                : 'Working...'}
            </p>
          </>
        ) : (
          <p className="text-ink-4 text-[13px]">
            Comparison results will appear here after supplier verification.
          </p>
        )}
      </div>
    )
  }

  const sorted = comparison?.comparisons
    ? [...comparison.comparisons].sort((a: any, b: any) => b.overall_score - a.overall_score)
    : []

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-10">
      {/* ── Editorial Supplier Cards ──────────── */}
      {comparison && sorted.length > 0 && (
        <div>
          <h2 className="font-heading text-2xl text-ink mb-2">Supplier Comparison</h2>

          {/* Best-of text badges */}
          <div className="flex gap-3 mb-6 flex-wrap text-[11px] text-ink-3">
            {comparison.best_value && (
              <span>Best Value: <span className="text-teal font-medium">{comparison.best_value}</span></span>
            )}
            {comparison.best_quality && (
              <span>Best Quality: <span className="text-teal font-medium">{comparison.best_quality}</span></span>
            )}
            {comparison.best_speed && (
              <span>Fastest: <span className="text-teal font-medium">{comparison.best_speed}</span></span>
            )}
          </div>

          {/* Side-by-side editorial cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {sorted.slice(0, 4).map((c: any, i: number) => {
              const isRecommended = i === 0
              return (
                <div
                  key={i}
                  className={`card p-5 ${isRecommended ? 'border-t-[2px] border-t-teal' : ''}`}
                >
                  {isRecommended && (
                    <p className="text-[9px] font-bold text-teal tracking-[2px] uppercase mb-3">Recommended</p>
                  )}

                  {/* Avatar + name */}
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-surface-2 flex items-center justify-center text-[12px] font-bold text-ink-3 shrink-0">
                      {getInitials(c.supplier_name)}
                    </div>
                    <div className="min-w-0">
                      <p className="font-heading text-[15px] text-ink truncate">{c.supplier_name}</p>
                      {c.moq && <p className="text-[10px] text-ink-4">MOQ: {c.moq}</p>}
                    </div>
                  </div>

                  {/* Large price */}
                  {c.estimated_landed_cost && (
                    <p className="font-heading text-2xl text-ink mb-1">
                      {c.estimated_landed_cost}
                    </p>
                  )}
                  {c.estimated_unit_price && !c.estimated_landed_cost && (
                    <p className="font-heading text-2xl text-ink mb-1">
                      {c.estimated_unit_price}
                    </p>
                  )}
                  {c.lead_time && (
                    <p className="text-[10px] text-ink-4 mb-4">{c.lead_time} lead time</p>
                  )}

                  {/* Score bars */}
                  <div className="space-y-2 mb-4">
                    {c.price_score != null && <ScoreBar score={c.price_score} label="Price" />}
                    {c.quality_score != null && <ScoreBar score={c.quality_score} label="Quality" />}
                    {c.shipping_score != null && <ScoreBar score={c.shipping_score} label="Shipping" />}
                    {c.lead_time_score != null && <ScoreBar score={c.lead_time_score} label="Speed" />}
                  </div>

                  {/* Strengths / Weaknesses as dot-prefixed text */}
                  {c.strengths?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-[9px] uppercase tracking-wider text-ink-4 mb-1">Strengths</p>
                      {c.strengths.map((s: string, j: number) => (
                        <p key={j} className="text-[11px] text-ink-3 flex items-start gap-1.5">
                          <span className="text-teal mt-1 shrink-0">·</span> {s}
                        </p>
                      ))}
                    </div>
                  )}
                  {c.weaknesses?.length > 0 && (
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-ink-4 mb-1">Weaknesses</p>
                      {c.weaknesses.map((w: string, j: number) => (
                        <p key={j} className="text-[11px] text-ink-3 flex items-start gap-1.5">
                          <span className="text-red-400 mt-1 shrink-0">·</span> {w}
                        </p>
                      ))}
                    </div>
                  )}

                  {/* Overall score */}
                  <div className="mt-4 pt-3 border-t border-surface-3 flex items-center justify-between">
                    <span className="text-[10px] text-ink-4">Overall</span>
                    <span className="font-heading text-xl text-ink">{Math.round(c.overall_score)}</span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Narrative */}
          {comparison.analysis_narrative && (
            <div className="mt-6 card p-6">
              <p className="text-[9px] uppercase tracking-wider text-ink-4 mb-2">Analysis</p>
              <p className="text-[13px] text-ink-2 leading-relaxed whitespace-pre-line">
                {comparison.analysis_narrative}
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── AI Recommendation ─────────────────── */}
      {recommendation && (
        <div>
          <h2 className="font-heading text-2xl text-ink mb-4">Recommendation</h2>

          {/* Executive summary with teal left line */}
          {recommendation.executive_summary && (
            <div className="border-l-[2px] border-l-teal pl-5 mb-8">
              <p className="text-[14px] text-ink-2 leading-relaxed">
                {recommendation.executive_summary}
              </p>
            </div>
          )}

          {/* Ranked picks */}
          <div className="space-y-4">
            {recommendation.recommendations.map((rec: any) => {
              const supplier = suppliers?.[rec.supplier_index]
              const comp = comparisonMap.get(rec.supplier_name)

              return (
                <div
                  key={rec.rank}
                  className={`card p-5 ${rec.rank === 1 ? 'border-t-[2px] border-t-teal' : ''}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-bold ${
                          rec.rank === 1
                            ? 'bg-teal text-white'
                            : 'bg-surface-2 text-ink-3'
                        }`}
                      >
                        {rec.rank}
                      </div>
                      <div>
                        <h3 className="font-heading text-lg text-ink">{rec.supplier_name}</h3>
                        <p className="text-[11px] text-ink-4">{rec.best_for}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="font-heading text-2xl text-ink">
                        {Math.round(rec.overall_score)}
                      </span>
                      <p className="text-[9px] text-ink-4">/ 100</p>
                    </div>
                  </div>

                  <p className="mt-3 text-[12px] text-ink-3 leading-relaxed">
                    {rec.reasoning}
                  </p>

                  {/* Cost row */}
                  {comp && (comp.estimated_unit_price || comp.estimated_landed_cost) && (
                    <div className="mt-3 flex flex-wrap gap-4 text-[11px]">
                      {comp.estimated_unit_price && (
                        <span><span className="text-ink-4">Unit:</span> <span className="text-ink-2 font-medium">{comp.estimated_unit_price}</span></span>
                      )}
                      {comp.estimated_shipping_cost && (
                        <span><span className="text-ink-4">Shipping:</span> <span className="text-teal">{comp.estimated_shipping_cost}</span></span>
                      )}
                      {comp.estimated_landed_cost && (
                        <span><span className="text-ink-4">Landed:</span> <span className="text-ink font-semibold">{comp.estimated_landed_cost}</span></span>
                      )}
                    </div>
                  )}

                  {/* Contact */}
                  {supplier && (
                    <div className="mt-3 flex items-center gap-3 text-[11px]">
                      {supplier.website && (
                        <a
                          href={supplier.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-teal hover:underline"
                        >
                          Website
                        </a>
                      )}
                      {supplier.email && (
                        <span className="text-ink-4">{supplier.email}</span>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Caveats */}
          {recommendation.caveats?.length > 0 && (
            <div className="mt-6 card border-l-[2px] border-l-warm px-5 py-4">
              <p className="text-[9px] uppercase tracking-wider text-ink-4 mb-2">Caveats</p>
              <div className="space-y-1.5">
                {recommendation.caveats.map((caveat: string, i: number) => (
                  <p key={i} className="text-[12px] text-ink-3 flex items-start gap-2">
                    <span className="text-warm mt-0.5 shrink-0">·</span>
                    {caveat}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
