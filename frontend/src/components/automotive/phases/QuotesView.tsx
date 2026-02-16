'use client'

import type { ParsedQuote } from '@/types/automotive'
import { m, DURATION } from '@/lib/motion'
import StageActionButton from '@/components/automotive/shared/StageActionButton'
import ScoreBar from '@/components/automotive/shared/ScoreBar'
import Tooltip from '@/components/automotive/shared/Tooltip'
import ProcessingState from '@/components/automotive/shared/ProcessingState'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: () => void
}

const confidenceTooltip = (c: number) => {
  if (c >= 0.8) return 'High confidence — quote data was clearly structured and easily extracted.'
  if (c >= 0.5) return 'Medium confidence — some fields were estimated or partially extracted. Review highlighted fields.'
  return 'Low confidence — significant manual review recommended. Many fields could not be reliably extracted.'
}

const formatUSD = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

export default function QuotesView({ data, isActive, onApprove }: Props) {
  if (!data) {
    return (
      <m.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.98 }} transition={{ duration: DURATION.normal }}>
        <ProcessingState stage="quote_ingest" variant={isActive ? 'processing' : 'waiting'} />
      </m.div>
    )
  }

  const quotes = (data.quotes || []) as ParsedQuote[]
  const totalReceived = data.total_received as number || 0
  const totalParsed = data.total_parsed as number || 0
  const awaiting = (data.awaiting_response as string[]) || []

  const sortedQuotes = [...quotes].sort((a, b) => a.estimated_annual_tco_usd - b.estimated_annual_tco_usd)
  const hasLowConfidence = sortedQuotes.some(q => q.low_confidence_fields.length > 0)

  return (
    <m.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.normal, ease: [0.16, 1, 0.3, 1] }}
      className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Quote Analysis</h3>
          <p className="text-xs text-zinc-500 mt-1">
            {totalParsed} of {totalReceived} quotes parsed
            {awaiting.length > 0 && ` · ${awaiting.length} still awaiting`}
          </p>
        </div>
        {isActive && (
          <StageActionButton stage="quote_ingest" onClick={onApprove} />
        )}
      </div>

      {/* Low confidence warning */}
      {hasLowConfidence && (
        <div className="px-6 py-2.5 bg-amber-500/5 border-b border-amber-500/10">
          <p className="text-xs text-amber-400">
            ⚠ Some quotes have low-confidence fields that may need manual verification. Look for amber highlights below.
          </p>
        </div>
      )}

      {/* Comparison table — desktop */}
      {sortedQuotes.length > 0 && (
        <div className="overflow-x-auto hidden md:block">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="px-4 py-3 text-left text-xs text-zinc-500 font-normal">#</th>
                <th className="px-4 py-3 text-left text-xs text-zinc-500 font-normal">Supplier</th>
                <th className="px-4 py-3 text-right text-xs text-zinc-500 font-normal">Piece Price</th>
                <th className="px-4 py-3 text-right text-xs text-zinc-500 font-normal">Tooling</th>
                <th className="px-4 py-3 text-right text-xs text-zinc-500 font-normal">Lead Time</th>
                <th className="px-4 py-3 text-right text-xs text-zinc-500 font-normal">MOQ</th>
                <th className="px-4 py-3 text-right text-xs text-zinc-500 font-normal">Annual TCO</th>
                <th className="px-4 py-3 text-center text-xs text-zinc-500 font-normal">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {sortedQuotes.map((q, idx) => (
                <tr key={q.supplier_id} className={`border-b border-zinc-800/50 ${idx === 0 ? 'bg-emerald-500/5' : ''}`}>
                  <td className="px-4 py-3 text-zinc-600 font-mono text-xs">{idx + 1}</td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-zinc-200">{q.supplier_name}</span>
                    {idx === 0 && (
                      <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                        BEST TCO
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-zinc-300 font-mono">
                    ${q.piece_price.toFixed(3)}
                  </td>
                  <td className="px-4 py-3 text-right text-zinc-400">
                    {q.tooling_cost ? formatUSD(q.tooling_cost) : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-zinc-400">
                    {q.production_lead_time_weeks ? `${q.production_lead_time_weeks}w` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-zinc-400">
                    {q.moq ? q.moq.toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-zinc-200">
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
      )}

      {/* Quote cards — mobile */}
      <div className="md:hidden p-4 space-y-3">
        {sortedQuotes.map((q, idx) => (
          <div key={q.supplier_id} className={`rounded-lg p-4 ${idx === 0 ? 'bg-emerald-500/5 border border-emerald-500/20' : 'bg-zinc-800/50'}`}>
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

      {/* Quote detail cards — desktop */}
      <div className="p-6 hidden md:grid grid-cols-1 md:grid-cols-2 gap-4">
        {sortedQuotes.map((q) => (
          <div key={q.supplier_id} className="bg-zinc-800/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-sm text-zinc-200">{q.supplier_name}</h4>
              <Tooltip content={confidenceTooltip(q.extraction_confidence)}>
                <ScoreBar value={q.extraction_confidence * 100} size="sm" />
              </Tooltip>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-zinc-500">Piece Price</span>
                <p className="text-zinc-300 font-mono">${q.piece_price.toFixed(3)}</p>
              </div>
              {q.tooling_cost && (
                <div>
                  <span className="text-zinc-500">Tooling</span>
                  <p className="text-zinc-300">{formatUSD(q.tooling_cost)}</p>
                </div>
              )}
              {q.production_lead_time_weeks && (
                <div>
                  <span className="text-zinc-500">Lead Time</span>
                  <p className="text-zinc-300">{q.production_lead_time_weeks} weeks</p>
                </div>
              )}
              {q.moq && (
                <div>
                  <span className="text-zinc-500">MOQ</span>
                  <p className="text-zinc-300">{q.moq.toLocaleString()}</p>
                </div>
              )}
              <div className="col-span-2">
                <span className="text-zinc-500">Estimated Annual TCO</span>
                <p className="text-zinc-200 font-semibold">{formatUSD(q.estimated_annual_tco_usd)}</p>
              </div>
            </div>

            {q.low_confidence_fields.length > 0 && (
              <div className="mt-3 pt-2 border-t border-zinc-700/50 border-l-2 border-l-amber-500 pl-3">
                <p className="text-[10px] text-amber-500 uppercase tracking-wider mb-1">Low Confidence Fields</p>
                <p className="text-xs text-amber-400/70">{q.low_confidence_fields.join(', ')}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Awaiting responses */}
      {awaiting.length > 0 && (
        <div className="px-6 py-3 border-t border-zinc-800 bg-zinc-800/20">
          <p className="text-xs text-zinc-500">
            ⏳ Still awaiting response from {awaiting.length} supplier{awaiting.length > 1 ? 's' : ''}
          </p>
        </div>
      )}
    </m.div>
  )
}
