'use client'

import type { ProjectDetail } from '@/lib/automotive/client'
import ScoreBar from '@/components/automotive/shared/ScoreBar'
import Tooltip from '@/components/automotive/shared/Tooltip'

interface Props {
  project: ProjectDetail
}

export default function CompleteView({ project }: Props) {
  const parsed = project.parsed_requirement || {}
  const comparison = project.comparison_matrix || {}
  const quotes = project.quote_ingestion || {}
  const rfq = project.rfq_result || {}

  const topRec = comparison.top_recommendation as string || ''
  const rationale = comparison.recommendation_rationale as string || ''
  const quotesList = (quotes.quotes || []) as Array<{
    supplier_name: string
    piece_price: number
    tooling_cost?: number
    estimated_annual_tco_usd: number
    production_lead_time_weeks?: number
    extraction_confidence: number
  }>
  const bestQuote = quotesList.length > 0
    ? [...quotesList].sort((a, b) => a.estimated_annual_tco_usd - b.estimated_annual_tco_usd)[0]
    : null

  const formatUSD = (n: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

  const confidenceTooltip = (c: number) => {
    if (c >= 0.8) return 'High confidence — quote data was clearly structured and easily extracted.'
    if (c >= 0.5) return 'Medium confidence — some fields were estimated or partially extracted.'
    return 'Low confidence — significant manual review recommended.'
  }

  return (
    <div className="space-y-6">
      {/* Success banner */}
      <div className="bg-gradient-to-r from-emerald-900/30 to-amber-900/20 border border-emerald-800/40 rounded-xl p-8 text-center">
        <div className="text-4xl mb-3">✓</div>
        <h2 className="text-2xl font-bold text-emerald-400 mb-2">Procurement Complete</h2>
        <p className="text-zinc-400 max-w-lg mx-auto">
          Your automotive procurement pipeline has finished. Review the summary below and proceed with supplier engagement.
        </p>
      </div>

      {/* Summary grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Recommendation */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Top Recommendation</p>
          <p className="text-lg font-bold text-amber-400">{topRec || 'N/A'}</p>
          {rationale && <p className="text-xs text-zinc-500 mt-2">{rationale}</p>}
        </div>

        {/* Best TCO */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Best TCO Quote</p>
          {bestQuote ? (
            <>
              <p className="text-lg font-bold text-emerald-400">{formatUSD(bestQuote.estimated_annual_tco_usd)}/yr</p>
              <p className="text-xs text-zinc-400 mt-1">{bestQuote.supplier_name}</p>
              <p className="text-xs text-zinc-500 mt-1">
                ${bestQuote.piece_price.toFixed(3)}/pc
                {bestQuote.tooling_cost && ` + ${formatUSD(bestQuote.tooling_cost)} tooling`}
              </p>
            </>
          ) : (
            <p className="text-sm text-zinc-500">No quotes received</p>
          )}
        </div>

        {/* Pipeline stats */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Pipeline Stats</p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-500">Part</span>
              <span className="text-zinc-300">{(parsed.part_description as string) || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Suppliers Found</span>
              <span className="text-zinc-300">{((project.discovery_result || {}) as any).total_found || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Qualified</span>
              <span className="text-zinc-300">{((project.qualification_result || {}) as any).qualified_count || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">RFQs Sent</span>
              <span className="text-zinc-300">{(rfq as any).total_sent || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Quotes Received</span>
              <span className="text-zinc-300">{(quotes as any).total_parsed || '—'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* All quotes ranked */}
      {quotesList.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-zinc-800">
            <h3 className="font-semibold">Final Quote Rankings</h3>
          </div>

          {/* Desktop table */}
          <div className="hidden md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="px-4 py-3 text-left text-xs text-zinc-500 font-normal">#</th>
                  <th className="px-4 py-3 text-left text-xs text-zinc-500 font-normal">Supplier</th>
                  <th className="px-4 py-3 text-right text-xs text-zinc-500 font-normal">Piece Price</th>
                  <th className="px-4 py-3 text-right text-xs text-zinc-500 font-normal">Tooling</th>
                  <th className="px-4 py-3 text-right text-xs text-zinc-500 font-normal">Lead Time</th>
                  <th className="px-4 py-3 text-right text-xs text-zinc-500 font-normal">Annual TCO</th>
                  <th className="px-4 py-3 text-center text-xs text-zinc-500 font-normal">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {[...quotesList]
                  .sort((a, b) => a.estimated_annual_tco_usd - b.estimated_annual_tco_usd)
                  .map((q, idx) => (
                    <tr key={q.supplier_name} className={`border-b border-zinc-800/50 ${idx === 0 ? 'bg-emerald-500/5' : ''}`}>
                      <td className="px-4 py-3 text-zinc-600 font-mono text-xs">{idx + 1}</td>
                      <td className="px-4 py-3">
                        <span className="font-medium text-zinc-200">{q.supplier_name}</span>
                        {idx === 0 && (
                          <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            BEST TCO
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-300 font-mono">${q.piece_price.toFixed(3)}</td>
                      <td className="px-4 py-3 text-right text-zinc-400">
                        {q.tooling_cost ? formatUSD(q.tooling_cost) : '—'}
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-400">
                        {q.production_lead_time_weeks ? `${q.production_lead_time_weeks}w` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-200 font-semibold">
                        {formatUSD(q.estimated_annual_tco_usd)}
                      </td>
                      <td className="px-4 py-3">
                        <Tooltip content={confidenceTooltip(q.extraction_confidence)}>
                          <div className="w-20 mx-auto">
                            <ScoreBar value={q.extraction_confidence * 100} size="sm" />
                          </div>
                        </Tooltip>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden p-4 space-y-3">
            {[...quotesList]
              .sort((a, b) => a.estimated_annual_tco_usd - b.estimated_annual_tco_usd)
              .map((q, idx) => (
                <div key={q.supplier_name} className={`rounded-lg p-4 ${idx === 0 ? 'bg-emerald-500/5 border border-emerald-500/20' : 'bg-zinc-800/50'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm text-zinc-200">{q.supplier_name}</span>
                    {idx === 0 && <span className="text-[10px] text-emerald-400">BEST TCO</span>}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div><span className="text-zinc-500">Piece Price</span><p className="text-zinc-300 font-mono">${q.piece_price.toFixed(3)}</p></div>
                    <div><span className="text-zinc-500">Annual TCO</span><p className="text-zinc-200 font-semibold">{formatUSD(q.estimated_annual_tco_usd)}</p></div>
                    {q.tooling_cost && <div><span className="text-zinc-500">Tooling</span><p className="text-zinc-300">{formatUSD(q.tooling_cost)}</p></div>}
                    {q.production_lead_time_weeks && <div><span className="text-zinc-500">Lead Time</span><p className="text-zinc-300">{q.production_lead_time_weeks}w</p></div>}
                  </div>
                  <div className="mt-2">
                    <Tooltip content={confidenceTooltip(q.extraction_confidence)}>
                      <ScoreBar value={q.extraction_confidence * 100} size="sm" />
                    </Tooltip>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Next steps */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="font-semibold mb-3">Recommended Next Steps</h3>
        <div className="space-y-2 text-sm text-zinc-400">
          <p>1. Schedule site visits to top 2-3 suppliers for facility audits</p>
          <p>2. Request PPAP samples from shortlisted suppliers</p>
          <p>3. Negotiate final pricing and terms based on TCO analysis</p>
          <p>4. Execute supply agreement with selected supplier</p>
          <p>5. Set up EDI / logistics integration and kick off tooling</p>
        </div>
      </div>
    </div>
  )
}
