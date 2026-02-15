'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { authFetch } from '@/lib/auth'
import { featureFlags } from '@/lib/featureFlags'
import { trackTraceEvent } from '@/lib/telemetry'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import { DecisionLane } from '@/types/pipeline'
import { m, AnimatePresence } from '@/lib/motion'
import { staggerContainer, cardEntrance } from '@/lib/motion/variants'
import { EASE_OUT_EXPO, DURATION } from '@/lib/motion/config'
import StageAnimationRouter from '@/components/animation/StageAnimationRouter'
import VerdictView from '@/components/workspace/compare/VerdictView'

type CompareView = 'verdict' | 'full_comparison'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')
const PRIMARY_LANES: Array<Exclude<DecisionLane, 'alternative'>> = [
  'best_overall',
  'best_low_risk',
  'best_speed_to_order',
]
const LANE_LABELS: Record<Exclude<DecisionLane, 'alternative'>, string> = {
  best_overall: 'Best overall',
  best_low_risk: 'Best low risk',
  best_speed_to_order: 'Best speed to order',
}

function normalizeStarScore(score: number): number {
  if (!Number.isFinite(score)) return 0
  if (score <= 5) return Math.min(5, Math.max(0, score))
  return Math.min(5, Math.max(0, score / 20))
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
  const rawCandidates = [
    raw.image_url,
    raw.product_image,
    raw.product_image_url,
    raw.thumbnail,
    raw.thumbnail_url,
    raw.logo,
    raw.logo_url,
  ]
  for (const candidate of rawCandidates) {
    if (typeof candidate === 'string' && candidate.startsWith('http')) return candidate
  }

  if (Array.isArray(raw.images)) {
    const first = raw.images.find((value: unknown) => typeof value === 'string' && value.startsWith('http'))
    if (typeof first === 'string') return first
  }

  if (Array.isArray(raw.image_urls)) {
    const first = raw.image_urls.find((value: unknown) => typeof value === 'string' && value.startsWith('http'))
    if (typeof first === 'string') return first
  }

  return null
}

function ScoreBar({ score, label }: { score: number; label: string }) {
  const stars = normalizeStarScore(score)
  const widthPct = (stars / 5) * 100

  return (
    <div>
      <div className="flex justify-between text-[10px] mb-1">
        <span className="text-ink-4">{label}</span>
        <span className="font-medium text-ink-2">{stars.toFixed(1)}/5</span>
      </div>
      <div className="score-bar">
        <m.div
          className="score-bar-fill"
          style={{ width: `${widthPct}%`, transformOrigin: 'left' }}
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT_EXPO, delay: 0.15 }}
        />
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

function arraysEqual(left: number[], right: number[]): boolean {
  if (left.length !== right.length) return false
  return left.every((value, idx) => value === right[idx])
}

export default function ComparePhase() {
  const {
    status,
    loading,
    projectId,
    setActivePhase,
    refreshStatus,
    setDecisionPreference,
  } = useWorkspace()
  const searchParams = useSearchParams()
  const router = useRouter()
  const [compareView, setCompareView] = useState<CompareView>('verdict')
  const [selectedSupplierIndices, setSelectedSupplierIndices] = useState<number[]>([])
  const [selectedLane, setSelectedLane] = useState<Exclude<DecisionLane, 'alternative'>>(
    'best_overall'
  )
  const [laneSaving, setLaneSaving] = useState(false)
  const [expandedTrustPanels, setExpandedTrustPanels] = useState<Record<number, boolean>>({})
  const [dismissedManualVerification, setDismissedManualVerification] = useState<Record<number, boolean>>({})
  const [approvalLoading, setApprovalLoading] = useState(false)
  const [approvalError, setApprovalError] = useState<string | null>(null)
  const [approvalSuccess, setApprovalSuccess] = useState<string | null>(null)

  const comparison = status?.comparison_result
  const recommendation = status?.recommendation
  const suppliers = status?.discovery_results?.suppliers
  const verifications = status?.verification_results
  const requirements = status?.parsed_requirements
  const persistedLanePreference = status?.decision_preference

  useEffect(() => {
    if (!featureFlags.tamkinFocusCircleSearchV1) return
    if (!persistedLanePreference) return
    if (!PRIMARY_LANES.includes(persistedLanePreference as Exclude<DecisionLane, 'alternative'>)) return
    const persisted = persistedLanePreference as Exclude<DecisionLane, 'alternative'>
    setSelectedLane((prev) => (prev === persisted ? prev : persisted))
  }, [persistedLanePreference])

  function openSupplierProfile(supplierIndex: number) {
    const params = new URLSearchParams(searchParams.toString())
    params.set('supplierIndex', String(supplierIndex))
    router.push(`/product?${params.toString()}`)
  }

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

  const sorted = comparison?.comparisons
    ? [...comparison.comparisons].sort((a: any, b: any) => b.overall_score - a.overall_score)
    : []

  const recommendationDefaults = useMemo(() => {
    const recommendations = recommendation?.recommendations || []
    const orderedRecommendations =
      featureFlags.tamkinFocusCircleSearchV1
        ? [
            ...recommendations.filter((rec: any) => rec?.lane === selectedLane),
            ...recommendations.filter((rec: any) => rec?.lane !== selectedLane),
          ]
        : recommendations
    return orderedRecommendations
      .slice(0, 3)
      .map((rec: any) => rec.supplier_index)
      .filter((idx: number) => Number.isInteger(idx))
  }, [recommendation?.recommendations, selectedLane])

  useEffect(() => {
    if (!recommendationDefaults.length) return
    setSelectedSupplierIndices((prev) => {
      if (!featureFlags.tamkinFocusCircleSearchV1 && prev.length > 0) return prev
      if (arraysEqual(prev, recommendationDefaults)) return prev
      return recommendationDefaults
    })
  }, [recommendationDefaults])

  const selectedSuppliers = useMemo(
    () =>
      selectedSupplierIndices
        .map((idx) => ({
          idx,
          supplier: suppliers?.[idx],
          comparison: sorted.find((row: any) => row.supplier_index === idx),
        }))
        .filter((row) => !!row.supplier),
    [selectedSupplierIndices, sorted, suppliers]
  )

  const toggleSupplierSelection = useCallback((supplierIndex: number) => {
    setSelectedSupplierIndices((prev) =>
      prev.includes(supplierIndex)
        ? prev.filter((idx) => idx !== supplierIndex)
        : [...prev, supplierIndex]
    )
    setApprovalError(null)
    setApprovalSuccess(null)
  }, [])

  const handleLaneSelection = useCallback(
    async (lane: Exclude<DecisionLane, 'alternative'>) => {
      if (!featureFlags.tamkinFocusCircleSearchV1) return
      setSelectedLane(lane)
      if (!projectId) return

      trackTraceEvent(
        'decision_lane_selected',
        { project_id: projectId, lane_preference: lane },
        { projectId }
      )

      setLaneSaving(true)
      const persisted = await setDecisionPreference(lane)
      if (!persisted) {
        trackTraceEvent(
          'decision_lane_persist_failed',
          { project_id: projectId, lane_preference: lane },
          { projectId, level: 'warn' }
        )
      }
      setLaneSaving(false)
    },
    [projectId, setDecisionPreference]
  )

  const toggleTrustPanel = useCallback((supplierIndex: number) => {
    setExpandedTrustPanels((prev) => ({ ...prev, [supplierIndex]: !prev[supplierIndex] }))
  }, [])

  const dismissManualVerificationBadge = useCallback(
    (supplierIndex: number) => {
      if (!projectId) return
      setDismissedManualVerification((prev) => ({ ...prev, [supplierIndex]: true }))
      trackTraceEvent(
        'manual_verification_badge_dismissed',
        { project_id: projectId, supplier_index: supplierIndex },
        { projectId }
      )
    },
    [projectId]
  )

  const approveAndSendOutreach = useCallback(async () => {
    if (!projectId) return
    if (!selectedSupplierIndices.length) {
      setApprovalError('Pick at least one supplier before approving outreach.')
      return
    }

    setApprovalLoading(true)
    setApprovalError(null)
    setApprovalSuccess(null)
    trackTraceEvent(
      'compare_outreach_approval_attempt',
      { project_id: projectId, supplier_indices: selectedSupplierIndices },
      { projectId }
    )

    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/outreach/quick-approval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approve: true,
          max_suppliers: Math.min(10, selectedSupplierIndices.length),
          supplier_indices: selectedSupplierIndices,
        }),
      })

      if (!res.ok) {
        let detail = `HTTP ${res.status}`
        try {
          const payload = await res.json()
          detail = payload.detail || JSON.stringify(payload)
        } catch {
          // Keep HTTP detail.
        }
        throw new Error(detail)
      }

      const payload = await res.json()
      setApprovalSuccess(
        `Outreach approved. Sent to ${payload?.sent_count ?? 0} supplier(s).`
      )
      trackTraceEvent(
        'compare_outreach_approval_success',
        {
          project_id: projectId,
          sent_count: payload?.sent_count,
          failed_count: payload?.failed_count,
          supplier_indices: selectedSupplierIndices,
        },
        { projectId }
      )
      refreshStatus()
      setActivePhase('outreach')
    } catch (err: any) {
      setApprovalError(err?.message || 'Could not approve outreach.')
      trackTraceEvent(
        'compare_outreach_approval_error',
        {
          project_id: projectId,
          supplier_indices: selectedSupplierIndices,
          detail: err?.message || 'unknown',
        },
        { projectId, level: 'warn' }
      )
    } finally {
      setApprovalLoading(false)
    }
  }, [projectId, refreshStatus, selectedSupplierIndices, setActivePhase])

  const plainLanguagePreview = useMemo(() => {
    const product = requirements?.product_type || 'your product'
    const quantity = requirements?.quantity ? `${requirements.quantity} units` : 'your target quantity'
    const budget = requirements?.budget_range || 'your budget target'
    const location = requirements?.delivery_location || 'your delivery location'
    const deadline = requirements?.deadline || 'your timeline'

    return selectedSuppliers.map((row) => {
      const supplierName = row.supplier?.name || `Supplier ${row.idx + 1}`
      return `Tamkin will ask ${supplierName} for a quote on ${product}, around ${quantity}, within ${budget}, delivered to ${location} by ${deadline}. It will request MOQ, unit price, lead time, and sample readiness.`
    })
  }, [requirements, selectedSuppliers])

  const missingPrimaryLanes = useMemo(() => {
    if (!featureFlags.tamkinFocusCircleSearchV1 || !recommendation?.lane_coverage) return []
    return PRIMARY_LANES.filter((lane) => (recommendation.lane_coverage?.[lane] || 0) < 1)
  }, [recommendation?.lane_coverage])

  // Loading / empty state (must come after hooks so hook order is stable across renders)
  if (!comparison && !recommendation) {
    if (loading) return <StageAnimationRouter />
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <p className="text-ink-4 text-[13px]">
          Comparison results will appear here after supplier verification.
        </p>
      </div>
    )
  }

  // ─── Verdict View (default — recommendation-first) ────
  if (compareView === 'verdict' && recommendation && suppliers) {
    return (
      <VerdictView
        recommendation={recommendation}
        suppliers={suppliers}
        discoveryResults={status?.discovery_results}
        verificationResults={verifications}
        comparisonResult={comparison}
        onApproveOutreach={() => void approveAndSendOutreach()}
        onShowFullComparison={() => setCompareView('full_comparison')}
        onOpenSupplierProfile={openSupplierProfile}
        approvalLoading={approvalLoading}
      />
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-10">
      {/* ── Back to verdict view ────────────────── */}
      {recommendation && (
        <button
          onClick={() => setCompareView('verdict')}
          className="text-[12px] text-teal hover:text-teal-600 transition-colors flex items-center gap-1"
        >
          <span>&larr;</span> Back to recommendation
        </button>
      )}
      {/* ── Compare → Outreach touchpoint ─────── */}
      {recommendation && sorted.length > 0 && (
        <div className="card p-6 space-y-5">
          <div>
            <h2 className="font-heading text-2xl text-ink mb-1">Approve outreach shortlist</h2>
            <p className="text-[12px] text-ink-3">
              Pick who Tamkin should contact next. You can add suppliers before outreach starts.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sorted.slice(0, 8).map((supplierComp: any) => {
              const idx = supplierComp.supplier_index
              const selected = selectedSupplierIndices.includes(idx)
              const supplier = suppliers?.[idx]
              const verification = verificationMap.get(supplierComp.supplier_name)
              const imageUrl = getSupplierImageUrl(supplier)

              return (
                <label
                  key={idx}
                  className={`rounded-xl border px-3 py-3 cursor-pointer transition-colors ${
                    selected
                      ? 'border-teal bg-teal/[0.05]'
                      : 'border-surface-3 hover:border-surface-4'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggleSupplierSelection(idx)}
                      className="mt-1 accent-teal"
                    />

                    <div className="flex-1 min-w-0 space-y-2">
                      {imageUrl ? (
                        <div className="h-20 rounded-lg overflow-hidden border border-surface-3">
                          <img
                            src={imageUrl}
                            alt={`${supplierComp.supplier_name} product`}
                            className="w-full h-full object-cover"
                            loading="lazy"
                          />
                        </div>
                      ) : null}

                      <div>
                        <p className="text-[12px] font-medium text-ink truncate">
                          {supplierComp.supplier_name}
                        </p>
                        <p className="text-[10px] text-ink-4">
                          {supplier?.city || supplier?.country
                            ? `${supplier?.city || ''}${supplier?.city && supplier?.country ? ', ' : ''}${supplier?.country || ''}`
                            : 'Location not listed'}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2 text-[10px] text-ink-4">
                        {supplierComp.estimated_landed_cost ? (
                          <span>Landed: {supplierComp.estimated_landed_cost}</span>
                        ) : supplierComp.estimated_unit_price ? (
                          <span>Unit: {supplierComp.estimated_unit_price}</span>
                        ) : null}
                        {supplierComp.lead_time ? <span>Lead: {supplierComp.lead_time}</span> : null}
                        {verification?.risk_level ? (
                          <span>
                            Risk: <span className="text-ink-3">{verification.risk_level}</span>
                          </span>
                        ) : null}
                        {verification?.composite_score != null ? (
                          <span>
                            Verified: <span className="text-ink-3">{Math.round(verification.composite_score)}/100</span>
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </label>
              )
            })}
          </div>

          <div className="rounded-xl border border-surface-3 bg-surface-2/50 px-4 py-3">
            <p className="text-[11px] font-semibold text-ink-2 mb-2">What will be sent (plain language)</p>
            {plainLanguagePreview.length > 0 ? (
              <div className="space-y-2">
                {plainLanguagePreview.map((line, idx) => (
                  <p key={`${selectedSupplierIndices[idx]}-preview`} className="text-[11px] text-ink-3">
                    {line}
                  </p>
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-ink-4">Select suppliers to preview outreach intent.</p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => void approveAndSendOutreach()}
              disabled={approvalLoading || selectedSupplierIndices.length === 0}
              className="px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {approvalLoading ? 'Sending outreach…' : 'Approve and send outreach'}
            </button>
            <button
              onClick={() => setActivePhase('outreach')}
              className="px-4 py-2 border border-surface-3 text-ink-3 rounded-lg text-[12px] hover:bg-surface-2 transition-colors"
            >
              Review outreach phase
            </button>
          </div>

          {approvalError ? (
            <p className="text-[11px] text-red-600">{approvalError}</p>
          ) : null}
          {approvalSuccess ? (
            <p className="text-[11px] text-teal">{approvalSuccess}</p>
          ) : null}
        </div>
      )}

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
          <m.div
            className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            {sorted.slice(0, 4).map((c: any, i: number) => {
              const isRecommended = i === 0
              const supplier = suppliers?.[c.supplier_index]
              const imageUrl = getSupplierImageUrl(supplier)
              return (
                <m.div
                  key={i}
                  variants={cardEntrance}
                  className={`card p-5 ${isRecommended ? 'border-t-[2px] border-t-teal' : ''}`}
                >
                  {isRecommended && (
                    <p className="text-[9px] font-bold text-teal tracking-[2px] uppercase mb-3">Recommended</p>
                  )}

                  {imageUrl ? (
                    <div className="mb-4 h-28 rounded-xl overflow-hidden border border-surface-3">
                      <img
                        src={imageUrl}
                        alt={`${c.supplier_name} product`}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    </div>
                  ) : null}

                  {/* Avatar + name */}
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-surface-2 flex items-center justify-center text-[12px] font-bold text-ink-3 shrink-0">
                      {getInitials(c.supplier_name)}
                    </div>
                    <div className="min-w-0">
                      <p className="font-heading text-[15px] text-ink truncate cursor-pointer hover:text-teal transition-colors" onClick={() => openSupplierProfile(c.supplier_index)}>{c.supplier_name}</p>
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
                </m.div>
              )
            })}
          </m.div>

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

          {featureFlags.tamkinFocusCircleSearchV1 && (
            <div className="card p-5 mb-5 space-y-4">
              <div>
                <p className="text-[10px] font-semibold tracking-[1.2px] uppercase text-ink-4">
                  Decision Checkpoint
                </p>
                <p className="text-[13px] text-ink-2 mt-1">
                  {recommendation.decision_checkpoint_summary ||
                    'Review the lane fit, trust notes, and verification checklist before outreach.'}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                {PRIMARY_LANES.map((lane) => (
                  <button
                    key={lane}
                    onClick={() => void handleLaneSelection(lane)}
                    className={`px-3 py-1.5 rounded-full border text-[11px] transition-colors ${
                      selectedLane === lane
                        ? 'border-teal bg-teal/10 text-teal'
                        : 'border-surface-3 text-ink-4 hover:border-teal hover:text-teal'
                    }`}
                  >
                    {LANE_LABELS[lane]}
                  </button>
                ))}
              </div>
              {laneSaving ? <p className="text-[10px] text-ink-4">Saving lane preference…</p> : null}
            </div>
          )}

          {featureFlags.tamkinFocusCircleSearchV1 &&
          (recommendation.elimination_rationale || missingPrimaryLanes.length > 0) ? (
            <div className="mb-5 rounded-xl border border-warm/40 bg-warm/10 px-4 py-3">
              <p className="text-[11px] font-medium text-ink-2 mb-1">Why fewer options are shown</p>
              <p className="text-[11px] text-ink-3">
                {recommendation.elimination_rationale ||
                  `Lane coverage is incomplete for: ${missingPrimaryLanes.map((lane) => LANE_LABELS[lane]).join(', ')}.`}
              </p>
            </div>
          ) : null}

          {/* Executive summary with teal left line */}
          {recommendation.executive_summary && (
            <div className="border-l-[2px] border-l-teal pl-5 mb-8">
              <p className="text-[14px] text-ink-2 leading-relaxed">
                {recommendation.executive_summary}
              </p>
            </div>
          )}

          {/* Ranked picks */}
          <m.div
            className="space-y-4"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            {recommendation.recommendations.map((rec: any) => {
              const supplier = suppliers?.[rec.supplier_index]
              const comp = comparisonMap.get(rec.supplier_name)
              const imageUrl = getSupplierImageUrl(supplier)

              return (
                <m.div
                  key={rec.rank}
                  variants={cardEntrance}
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
                        <h3 className="font-heading text-lg text-ink cursor-pointer hover:text-teal transition-colors" onClick={() => openSupplierProfile(rec.supplier_index)}>{rec.supplier_name}</h3>
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

                  {featureFlags.tamkinFocusCircleSearchV1 &&
                  rec.needs_manual_verification &&
                  !dismissedManualVerification[rec.supplier_index] ? (
                    <div className="mt-3 inline-flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-1.5">
                      <span className="text-[10px] text-amber-700 font-semibold">Needs manual verification</span>
                      {rec.manual_verification_reason ? (
                        <span className="text-[10px] text-amber-700">{rec.manual_verification_reason}</span>
                      ) : null}
                      <button
                        onClick={() => dismissManualVerificationBadge(rec.supplier_index)}
                        className="text-[10px] text-amber-700 hover:text-amber-800"
                        aria-label="Dismiss manual verification badge"
                      >
                        Dismiss
                      </button>
                    </div>
                  ) : null}

                  {imageUrl ? (
                    <div className="mt-3 h-24 rounded-lg overflow-hidden border border-surface-3">
                      <img
                        src={imageUrl}
                        alt={`${rec.supplier_name} product`}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    </div>
                  ) : null}

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

                  {featureFlags.tamkinFocusCircleSearchV1 ? (
                    <div className="mt-3 rounded-lg border border-surface-3 bg-surface-2/30 px-3 py-3">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[1px] text-ink-4">
                          Decision Confidence
                        </p>
                        <button
                          onClick={() => toggleTrustPanel(rec.supplier_index)}
                          className="text-[10px] text-teal hover:text-teal-700 transition-colors"
                        >
                          {expandedTrustPanels[rec.supplier_index] ? 'Collapse details' : 'Expand details'}
                        </button>
                      </div>

                      <div className="space-y-2">
                        <div>
                          <p className="text-[10px] font-medium text-ink-2 mb-1">Why trust</p>
                          {(expandedTrustPanels[rec.supplier_index]
                            ? rec.why_trust || []
                            : (rec.why_trust || []).slice(0, 1)
                          ).length > 0 ? (
                            (expandedTrustPanels[rec.supplier_index]
                              ? rec.why_trust || []
                              : (rec.why_trust || []).slice(0, 1)
                            ).map((item: string, idx: number) => (
                              <p key={`${rec.supplier_index}-trust-${idx}`} className="text-[11px] text-ink-3">
                                • {item}
                              </p>
                            ))
                          ) : (
                            <p className="text-[11px] text-ink-4">No trust notes were generated.</p>
                          )}
                        </div>
                        <div>
                          <p className="text-[10px] font-medium text-ink-2 mb-1">Key uncertainties</p>
                          {(expandedTrustPanels[rec.supplier_index]
                            ? rec.uncertainty_notes || []
                            : (rec.uncertainty_notes || []).slice(0, 1)
                          ).length > 0 ? (
                            (expandedTrustPanels[rec.supplier_index]
                              ? rec.uncertainty_notes || []
                              : (rec.uncertainty_notes || []).slice(0, 1)
                            ).map((item: string, idx: number) => (
                              <p key={`${rec.supplier_index}-uncertainty-${idx}`} className="text-[11px] text-ink-3">
                                • {item}
                              </p>
                            ))
                          ) : (
                            <p className="text-[11px] text-ink-4">No uncertainty notes were provided.</p>
                          )}
                        </div>
                        <div>
                          <p className="text-[10px] font-medium text-ink-2 mb-1">Verify before PO</p>
                          {(expandedTrustPanels[rec.supplier_index]
                            ? rec.verify_before_po || []
                            : (rec.verify_before_po || []).slice(0, 1)
                          ).length > 0 ? (
                            (expandedTrustPanels[rec.supplier_index]
                              ? rec.verify_before_po || []
                              : (rec.verify_before_po || []).slice(0, 1)
                            ).map((item: string, idx: number) => (
                              <p key={`${rec.supplier_index}-verify-${idx}`} className="text-[11px] text-ink-3">
                                • {item}
                              </p>
                            ))
                          ) : (
                            <p className="text-[11px] text-ink-4">No manual checklist provided.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : null}

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
                </m.div>
              )
            })}
          </m.div>

          {/* Caveats */}
          {(recommendation.caveats?.length || 0) > 0 && (
            <div className="mt-6 card border-l-[2px] border-l-warm px-5 py-4">
              <p className="text-[9px] uppercase tracking-wider text-ink-4 mb-2">Caveats</p>
              <div className="space-y-1.5">
                {(recommendation.caveats || []).map((caveat: string, i: number) => (
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
