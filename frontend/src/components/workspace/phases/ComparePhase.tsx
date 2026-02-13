'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { authFetch } from '@/lib/auth'
import { trackTraceEvent } from '@/lib/telemetry'
import { useWorkspace } from '@/contexts/WorkspaceContext'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

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
        <div className="score-bar-fill" style={{ width: `${widthPct}%` }} />
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
  const { status, loading, projectId, setActivePhase, refreshStatus } = useWorkspace()
  const [selectedSupplierIndices, setSelectedSupplierIndices] = useState<number[]>([])
  const [approvalLoading, setApprovalLoading] = useState(false)
  const [approvalError, setApprovalError] = useState<string | null>(null)
  const [approvalSuccess, setApprovalSuccess] = useState<string | null>(null)

  const comparison = status?.comparison_result
  const recommendation = status?.recommendation
  const suppliers = status?.discovery_results?.suppliers
  const verifications = status?.verification_results
  const requirements = status?.parsed_requirements

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

  const recommendationDefaults = useMemo(
    () =>
      (recommendation?.recommendations || [])
        .slice(0, 3)
        .map((rec: any) => rec.supplier_index)
        .filter((idx: number) => Number.isInteger(idx)),
    [recommendation?.recommendations]
  )

  useEffect(() => {
    if (selectedSupplierIndices.length > 0) return
    if (!recommendationDefaults.length) return
    setSelectedSupplierIndices(recommendationDefaults)
  }, [recommendationDefaults, selectedSupplierIndices.length])

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

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-10">
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
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {sorted.slice(0, 4).map((c: any, i: number) => {
              const isRecommended = i === 0
              const supplier = suppliers?.[c.supplier_index]
              const imageUrl = getSupplierImageUrl(supplier)
              return (
                <div
                  key={i}
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
              const imageUrl = getSupplierImageUrl(supplier)

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
