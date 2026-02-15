'use client'

import { useMemo } from 'react'
import { m } from '@/lib/motion'
import { staggerContainer, cardEntrance } from '@/lib/motion/variants'
import { EASE_OUT_EXPO } from '@/lib/motion/config'
import FunnelSummary from './FunnelSummary'

/* ────────────────────────────────────────────────────────
 * VerdictView — "recommendation first" default view.
 *
 * Shows:
 *  1. Executive summary (the agent's judgment in prose)
 *  2. Compact ranked list (top 3 picks)
 *  3. Primary CTA (Approve & send outreach)
 *  4. Funnel summary (34 found → 3 recommended)
 *  5. Link to FullComparisonView for detail
 * ──────────────────────────────────────────────────────── */

interface VerdictViewProps {
  recommendation: {
    recommendations: any[]
    executive_summary?: string
    caveats?: string[]
    decision_checkpoint_summary?: string
  }
  suppliers: any[]
  discoveryResults: any
  verificationResults: any
  comparisonResult: any
  onApproveOutreach: () => void
  onShowFullComparison: () => void
  onOpenSupplierProfile: (supplierIndex: number) => void
  approvalLoading: boolean
}

function getInitials(name: string): string {
  return name
    .split(/[\s&]+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
}

function getSupplierImageUrl(supplier: any): string | null {
  if (!supplier) return null
  const direct = [
    supplier.image_url,
    supplier.product_image_url,
    supplier.thumbnail,
    supplier.photo_url,
    supplier.logo_url,
  ]
  for (const candidate of direct) {
    if (typeof candidate === 'string' && candidate.startsWith('http')) return candidate
  }
  const raw = supplier.raw_data || {}
  const rawCandidates = [raw.image_url, raw.product_image, raw.thumbnail, raw.logo]
  for (const candidate of rawCandidates) {
    if (typeof candidate === 'string' && candidate.startsWith('http')) return candidate
  }
  return null
}

export default function VerdictView({
  recommendation,
  suppliers,
  discoveryResults,
  verificationResults,
  comparisonResult,
  onApproveOutreach,
  onShowFullComparison,
  onOpenSupplierProfile,
  approvalLoading,
}: VerdictViewProps) {
  const picks = recommendation.recommendations.slice(0, 3)

  const funnelData = useMemo(
    () => ({
      totalRaw: discoveryResults?.total_raw_results,
      deduplicated: discoveryResults?.deduplicated_count,
      verified: verificationResults?.verifications?.length,
      compared: comparisonResult?.comparisons?.length,
      recommended: recommendation.recommendations.length,
    }),
    [discoveryResults, verificationResults, comparisonResult, recommendation]
  )

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 space-y-8">
      {/* ── Executive summary (the verdict) ──────── */}
      {recommendation.executive_summary && (
        <m.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_OUT_EXPO }}
        >
          <h2 className="font-heading text-2xl text-ink mb-3">My Recommendation</h2>
          <div className="border-l-[2px] border-l-teal pl-5">
            <p className="text-[14px] text-ink-2 leading-relaxed">
              {recommendation.executive_summary}
            </p>
          </div>
        </m.div>
      )}

      {/* ── Ranked picks (compact) ───────────────── */}
      <m.div
        className="space-y-0 rounded-xl border border-surface-3 overflow-hidden"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {picks.map((rec: any, i: number) => {
          const supplier = suppliers?.[rec.supplier_index]
          const imageUrl = getSupplierImageUrl(supplier)
          const isTop = i === 0

          return (
            <m.div
              key={rec.rank}
              variants={cardEntrance}
              className={`flex items-center gap-4 px-5 py-4 ${
                i < picks.length - 1 ? 'border-b border-surface-3' : ''
              } ${isTop ? 'bg-teal/[0.03]' : 'bg-white'}`}
            >
              {/* Rank */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-bold shrink-0 ${
                  isTop ? 'bg-teal text-white' : 'bg-surface-2 text-ink-3'
                }`}
              >
                {rec.rank}
              </div>

              {/* Thumbnail */}
              {imageUrl ? (
                <div className="w-10 h-10 rounded-lg overflow-hidden border border-surface-3 shrink-0">
                  <img
                    src={imageUrl}
                    alt={rec.supplier_name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                </div>
              ) : (
                <div className="w-10 h-10 rounded-lg bg-surface-2 flex items-center justify-center text-[10px] font-bold text-ink-4 shrink-0">
                  {getInitials(rec.supplier_name)}
                </div>
              )}

              {/* Name + details */}
              <div className="flex-1 min-w-0">
                <p
                  className="text-[13px] font-medium text-ink truncate cursor-pointer hover:text-teal transition-colors"
                  onClick={() => onOpenSupplierProfile(rec.supplier_index)}
                >
                  {rec.supplier_name}
                </p>
                <p className="text-[11px] text-ink-4 truncate">{rec.best_for}</p>
              </div>

              {/* Score */}
              <div className="text-right shrink-0">
                <span className="font-heading text-lg text-ink">{Math.round(rec.overall_score)}</span>
                <span className="text-[9px] text-ink-4">/100</span>
              </div>
            </m.div>
          )
        })}
      </m.div>

      {/* ── Decision confidence (visible by default) ── */}
      {picks[0] && (picks[0].why_trust?.length > 0 || picks[0].uncertainty_notes?.length > 0) && (
        <div className="space-y-2 bg-surface-2/30 rounded-xl px-5 py-4">
          {picks[0].why_trust?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[1px] text-ink-4 mb-1">
                Why trust this pick
              </p>
              {picks[0].why_trust.slice(0, 2).map((item: string, idx: number) => (
                <p key={idx} className="text-[11px] text-ink-3">
                  &bull; {item}
                </p>
              ))}
            </div>
          )}
          {picks[0].uncertainty_notes?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[1px] text-ink-4 mb-1">
                Key uncertainties
              </p>
              {picks[0].uncertainty_notes.slice(0, 2).map((item: string, idx: number) => (
                <p key={idx} className="text-[11px] text-ink-3">
                  &bull; {item}
                </p>
              ))}
            </div>
          )}
          {picks[0].verify_before_po?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[1px] text-ink-4 mb-1">
                Verify before placing order
              </p>
              {picks[0].verify_before_po.slice(0, 2).map((item: string, idx: number) => (
                <p key={idx} className="text-[11px] text-ink-3">
                  &bull; {item}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Actions ──────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={onApproveOutreach}
          disabled={approvalLoading}
          className="px-5 py-2.5 bg-teal text-white rounded-lg text-[13px] font-medium
                     hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {approvalLoading ? 'Sending outreach\u2026' : 'Approve & send outreach'}
        </button>
        <button
          onClick={onShowFullComparison}
          className="px-4 py-2 border border-surface-3 text-ink-3 rounded-lg text-[12px]
                     hover:bg-surface-2 transition-colors"
        >
          See full comparison &rarr;
        </button>
      </div>

      {/* ── Funnel summary ───────────────────────── */}
      <div className="border border-surface-3 rounded-xl px-4 py-3">
        <p className="text-[10px] font-semibold tracking-[1.5px] uppercase text-ink-4 mb-1.5">
          What I considered
        </p>
        <FunnelSummary {...funnelData} />
      </div>

      {/* ── Caveats ──────────────────────────────── */}
      {(recommendation.caveats?.length || 0) > 0 && (
        <div className="card border-l-[2px] border-l-warm px-5 py-4">
          <p className="text-[9px] uppercase tracking-wider text-ink-4 mb-2">Caveats</p>
          <div className="space-y-1.5">
            {(recommendation.caveats || []).map((caveat: string, i: number) => (
              <p key={i} className="text-[12px] text-ink-3 flex items-start gap-2">
                <span className="text-warm mt-0.5 shrink-0">&middot;</span>
                {caveat}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
