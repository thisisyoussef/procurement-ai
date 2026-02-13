'use client'

import { useMemo } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import StarRating from '@/components/StarRating'

function ScoreBar({ score, label }: { score: number; label: string }) {
  const color =
    score >= 70
      ? 'bg-green-400'
      : score >= 40
      ? 'bg-amber-400'
      : 'bg-red-400'
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-workspace-muted">{label}</span>
        <span className="font-medium text-workspace-text">{Math.round(score)}</span>
      </div>
      <div className="h-1.5 bg-workspace-hover rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const styles: Record<string, string> = {
    high: 'bg-green-400/10 text-green-400 border-green-400/20',
    medium: 'bg-amber-400/10 text-amber-400 border-amber-400/20',
    low: 'bg-red-400/10 text-red-400 border-red-400/20',
  }
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${styles[confidence] || styles.low}`}>
      {confidence}
    </span>
  )
}

export default function ComparePhase() {
  const { status, loading } = useWorkspace()

  const comparison = status?.comparison_result
  const recommendation = status?.recommendation
  const suppliers = status?.discovery_results?.suppliers
  const verifications = status?.verification_results

  // Maps
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
      <div className="text-center py-16">
        {loading ? (
          <div className="inline-flex items-center gap-3 px-6 py-3 glass-card">
            <span className="w-2 h-2 rounded-full bg-teal animate-pulse" />
            <span className="text-sm text-workspace-text">
              {status?.current_stage === 'comparing'
                ? 'Comparing suppliers...'
                : status?.current_stage === 'recommending'
                ? 'Generating recommendations...'
                : 'Working...'}
            </span>
          </div>
        ) : (
          <p className="text-workspace-muted text-sm">
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
    <div className="space-y-8">
      {/* ── Section 1: Comparison Matrix ──────────── */}
      {comparison && (
        <div>
          <h2 className="text-xl font-heading text-workspace-text mb-4">
            Supplier Comparison
          </h2>

          {/* Best-of badges */}
          <div className="flex gap-2 mb-4 flex-wrap">
            {comparison.best_value && (
              <span className="text-[11px] px-3 py-1 bg-green-400/10 text-green-400 rounded-full border border-green-400/20">
                Best Value: {comparison.best_value}
              </span>
            )}
            {comparison.best_quality && (
              <span className="text-[11px] px-3 py-1 bg-teal/10 text-teal rounded-full border border-teal/20">
                Best Quality: {comparison.best_quality}
              </span>
            )}
            {comparison.best_speed && (
              <span className="text-[11px] px-3 py-1 bg-purple-400/10 text-purple-400 rounded-full border border-purple-400/20">
                Fastest: {comparison.best_speed}
              </span>
            )}
          </div>

          {/* Table */}
          <div className="glass-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-workspace-border">
                  <th className="text-left py-3 px-4 text-workspace-muted text-xs font-medium">Supplier</th>
                  <th className="text-left py-3 px-4 text-workspace-muted text-xs font-medium">Est. Price</th>
                  <th className="text-left py-3 px-4 text-workspace-muted text-xs font-medium">Shipping</th>
                  <th className="text-left py-3 px-4 text-workspace-muted text-xs font-medium">Landed</th>
                  <th className="text-left py-3 px-4 text-workspace-muted text-xs font-medium">MOQ</th>
                  <th className="text-left py-3 px-4 text-workspace-muted text-xs font-medium">Lead Time</th>
                  <th className="text-right py-3 px-4 text-workspace-muted text-xs font-medium">Score</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((c: any, i: number) => (
                  <tr
                    key={i}
                    className={`border-b border-workspace-border/50 ${
                      i === 0 ? 'bg-teal/5' : ''
                    }`}
                  >
                    <td className="py-3 px-4 font-medium text-workspace-text">
                      {i === 0 && <span className="text-teal mr-1">★</span>}
                      {c.supplier_name}
                    </td>
                    <td className="py-3 px-4 text-workspace-muted">{c.estimated_unit_price || '—'}</td>
                    <td className="py-3 px-4 text-workspace-muted">
                      {c.estimated_shipping_cost ? (
                        <span className="text-teal">{c.estimated_shipping_cost}</span>
                      ) : '—'}
                    </td>
                    <td className="py-3 px-4 text-workspace-text font-medium">
                      {c.estimated_landed_cost || '—'}
                    </td>
                    <td className="py-3 px-4 text-workspace-muted">{c.moq || '—'}</td>
                    <td className="py-3 px-4 text-workspace-muted">{c.lead_time || '—'}</td>
                    <td className="py-3 px-4 text-right">
                      <span className="font-bold text-lg text-workspace-text">
                        {Math.round(c.overall_score)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Strengths / Weaknesses Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
            {sorted.map((c: any, i: number) => (
              <div key={i} className="glass-card p-4">
                <h4 className="font-medium text-workspace-text text-sm mb-2">{c.supplier_name}</h4>

                {/* Star ratings */}
                {(c.price_score || c.quality_score || c.shipping_score) && (
                  <div className="flex flex-wrap gap-x-3 gap-y-0.5 mb-3 pb-3 border-b border-workspace-border/50">
                    {c.price_score ? <StarRating score={c.price_score} label="Price" size="sm" /> : null}
                    {c.quality_score ? <StarRating score={c.quality_score} label="Quality" size="sm" /> : null}
                    {c.shipping_score ? <StarRating score={c.shipping_score} label="Shipping" size="sm" /> : null}
                    {c.lead_time_score ? <StarRating score={c.lead_time_score} label="Speed" size="sm" /> : null}
                  </div>
                )}

                {c.strengths?.length > 0 && (
                  <div className="mb-2">
                    <p className="text-[10px] text-green-400 font-medium mb-1">Strengths</p>
                    <ul className="text-xs text-workspace-muted space-y-0.5">
                      {c.strengths.map((s: string, j: number) => (
                        <li key={j}>+ {s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {c.weaknesses?.length > 0 && (
                  <div>
                    <p className="text-[10px] text-red-400 font-medium mb-1">Weaknesses</p>
                    <ul className="text-xs text-workspace-muted space-y-0.5">
                      {c.weaknesses.map((w: string, j: number) => (
                        <li key={j}>- {w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Narrative */}
          {comparison.analysis_narrative && (
            <div className="mt-6 p-4 glass-card">
              <h4 className="text-xs font-medium text-workspace-muted mb-2">Analysis</h4>
              <p className="text-sm text-workspace-text leading-relaxed whitespace-pre-line">
                {comparison.analysis_narrative}
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Section 2: AI Recommendations ────────── */}
      {recommendation && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-full bg-teal flex items-center justify-center">
              <span className="text-workspace-bg text-xs font-bold">AI</span>
            </div>
            <h2 className="text-xl font-heading text-workspace-text">
              Recommendations
            </h2>
          </div>

          {/* Executive summary */}
          {recommendation.executive_summary && (
            <div className="p-4 glass-card border-teal/20 mb-6">
              <p className="text-sm text-workspace-text leading-relaxed">
                {recommendation.executive_summary}
              </p>
            </div>
          )}

          {/* Ranked cards */}
          <div className="space-y-4">
            {recommendation.recommendations.map((rec: any) => {
              const supplier = suppliers?.[rec.supplier_index]
              const verification = verificationMap.get(rec.supplier_name)
              const comp = comparisonMap.get(rec.supplier_name)

              return (
                <div
                  key={rec.rank}
                  className={`glass-card p-5 ${
                    rec.rank === 1 ? 'border-teal/30 bg-teal/5' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
                          rec.rank === 1
                            ? 'bg-teal text-workspace-bg'
                            : rec.rank === 2
                            ? 'bg-workspace-muted text-workspace-bg'
                            : 'bg-workspace-hover text-workspace-muted'
                        }`}
                      >
                        #{rec.rank}
                      </div>
                      <div>
                        <h3 className="font-semibold text-workspace-text text-lg">
                          {rec.supplier_name}
                        </h3>
                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                          <span className="text-[10px] px-2 py-0.5 bg-workspace-hover text-workspace-muted rounded-full border border-workspace-border">
                            {rec.best_for}
                          </span>
                          <ConfidenceBadge confidence={rec.confidence} />
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-2xl font-bold text-workspace-text">
                        {Math.round(rec.overall_score)}
                      </span>
                      <p className="text-[10px] text-workspace-muted">/ 100</p>
                    </div>
                  </div>

                  <p className="mt-3 text-sm text-workspace-muted leading-relaxed">
                    {rec.reasoning}
                  </p>

                  {/* Cost breakdown */}
                  {comp && (comp.estimated_unit_price || comp.estimated_landed_cost) && (
                    <div className="mt-3 flex flex-wrap gap-4 text-xs">
                      {comp.estimated_unit_price && (
                        <div>
                          <span className="text-workspace-muted">Unit: </span>
                          <span className="text-workspace-text font-medium">{comp.estimated_unit_price}</span>
                        </div>
                      )}
                      {comp.estimated_shipping_cost && (
                        <div>
                          <span className="text-workspace-muted">Ship: </span>
                          <span className="text-teal font-medium">{comp.estimated_shipping_cost}</span>
                        </div>
                      )}
                      {comp.estimated_landed_cost && (
                        <div>
                          <span className="text-workspace-muted">Landed: </span>
                          <span className="text-workspace-text font-bold">{comp.estimated_landed_cost}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Star ratings */}
                  {comp && (comp.price_score || comp.quality_score) && (
                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
                      {comp.price_score ? <StarRating score={comp.price_score} label="Price" size="sm" /> : null}
                      {comp.quality_score ? <StarRating score={comp.quality_score} label="Quality" size="sm" /> : null}
                      {comp.shipping_score ? <StarRating score={comp.shipping_score} label="Shipping" size="sm" /> : null}
                      {comp.lead_time_score ? <StarRating score={comp.lead_time_score} label="Speed" size="sm" /> : null}
                    </div>
                  )}

                  {/* Contact info */}
                  {supplier && (
                    <div className="mt-3 flex items-center gap-3 flex-wrap">
                      {supplier.website && (
                        <a
                          href={supplier.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs px-3 py-1.5 bg-workspace-hover text-workspace-muted rounded-lg hover:text-teal transition-colors border border-workspace-border"
                        >
                          Website →
                        </a>
                      )}
                      {supplier.email && (
                        <span className="text-xs text-workspace-muted">{supplier.email}</span>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Caveats */}
          {recommendation.caveats?.length > 0 && (
            <div className="mt-6 p-4 glass-card border-amber-400/20">
              <h4 className="text-xs font-medium text-amber-400 mb-2">Caveats</h4>
              <ul className="space-y-1">
                {recommendation.caveats.map((caveat: string, i: number) => (
                  <li key={i} className="text-sm text-workspace-muted flex items-start gap-2">
                    <span className="text-amber-400 mt-0.5 shrink-0">⚠</span>
                    <span>{caveat}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
