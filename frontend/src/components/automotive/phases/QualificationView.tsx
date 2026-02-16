'use client'

import { useState } from 'react'
import type { QualifiedSupplier } from '@/types/automotive'
import { m, StaggerList, StaggerItem, DURATION } from '@/lib/motion'
import StageActionButton from '@/components/automotive/shared/StageActionButton'
import Tooltip from '@/components/automotive/shared/Tooltip'
import ProcessingState from '@/components/automotive/shared/ProcessingState'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: (overrides?: Record<string, string>) => void
}

const STATUS_STYLES: Record<string, string> = {
  qualified: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  conditional: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  disqualified: 'bg-red-500/15 text-red-400 border-red-500/30',
}

const STATUS_TOOLTIPS: Record<string, string> = {
  qualified: 'Meets all requirements. Ready for comparison and scoring.',
  conditional: 'Partially meets requirements. Review concerns below — you can override the status if appropriate.',
  disqualified: 'Does not meet minimum requirements. Will be excluded from comparison.',
}

const CHECK_ICONS: Record<string, string> = {
  verified_active: '✅',
  evidence_found: '✅',
  found: '✅',
  low: '✅',
  moderate: '⚠️',
  high: '❌',
  expired: '⚠️',
  suspended: '❌',
  not_found: '❌',
  check_failed: '⚠️',
  unknown: '⏳',
}

export default function QualificationView({ data, isActive, onApprove }: Props) {
  const [overrides, setOverrides] = useState<Record<string, string>>({})

  if (!data) {
    return (
      <m.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.98 }} transition={{ duration: DURATION.normal }}>
        <ProcessingState stage="qualify" variant={isActive ? 'processing' : 'waiting'} />
      </m.div>
    )
  }

  const suppliers = (data.suppliers || []) as QualifiedSupplier[]
  const qCount = data.qualified_count as number || 0
  const cCount = data.conditional_count as number || 0
  const dCount = data.disqualified_count as number || 0

  const getStatus = (s: QualifiedSupplier) => overrides[s.supplier_id] || s.qualification_status
  const hasOverrides = Object.keys(overrides).length > 0

  return (
    <m.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.normal, ease: [0.16, 1, 0.3, 1] }}
      className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Supplier Qualification</h3>
          <p className="text-xs text-zinc-500 mt-1">
            {qCount} qualified · {cCount} conditional · {dCount} disqualified
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasOverrides && (
            <button
              onClick={() => setOverrides({})}
              className="text-xs text-zinc-500 hover:text-zinc-300"
            >
              Reset Overrides
            </button>
          )}
          {isActive && (
            <StageActionButton
              stage="qualify"
              onClick={() => onApprove(hasOverrides ? overrides : undefined)}
            />
          )}
        </div>
      </div>

      {/* Override summary */}
      {hasOverrides && (
        <div className="px-6 py-2.5 bg-amber-500/5 border-b border-amber-500/10">
          <span className="text-xs text-amber-400">
            {Object.keys(overrides).length} status override{Object.keys(overrides).length > 1 ? 's' : ''} applied
          </span>
        </div>
      )}

      <StaggerList className="divide-y divide-zinc-800">
        {suppliers.map((s) => {
          const status = getStatus(s)
          const isOverridden = s.supplier_id in overrides

          return (
            <StaggerItem key={s.supplier_id}>
            <div className="px-6 py-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h4 className="font-medium text-zinc-200">{s.company_name}</h4>
                  <Tooltip content={STATUS_TOOLTIPS[status] || ''}>
                    <span className={`text-xs px-2 py-0.5 rounded-full border inline-flex items-center gap-1 ${STATUS_STYLES[status] || STATUS_STYLES.conditional}`}>
                      {isOverridden && <span className="line-through text-zinc-500 mr-1">{s.qualification_status.toUpperCase()}</span>}
                      {status.toUpperCase()}
                      {status === 'conditional' && (
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className="opacity-60">
                          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" />
                          <path d="M8 5.5v3M8 10.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                      )}
                    </span>
                  </Tooltip>

                  {/* Override dropdown */}
                  {isActive && (
                    <select
                      value={overrides[s.supplier_id] || ''}
                      onChange={(e) => {
                        if (e.target.value === '' || e.target.value === s.qualification_status) {
                          setOverrides(prev => {
                            const next = { ...prev }
                            delete next[s.supplier_id]
                            return next
                          })
                        } else {
                          setOverrides(prev => ({ ...prev, [s.supplier_id]: e.target.value }))
                        }
                      }}
                      className="bg-zinc-800 border border-zinc-700 rounded px-1.5 py-0.5 text-[10px] text-zinc-400"
                    >
                      <option value="">Override…</option>
                      <option value="qualified">→ Qualified</option>
                      <option value="conditional">→ Conditional</option>
                      <option value="disqualified">→ Disqualified</option>
                    </select>
                  )}
                </div>
                <span className="text-xs text-zinc-500 font-mono">
                  Confidence: {Math.round((s.overall_confidence || 0) * 100)}%
                </span>
              </div>

              {/* Verification checks */}
              <div className="grid grid-cols-5 gap-3 mb-3">
                <div className="text-xs">
                  <span className="text-zinc-500">IATF 16949</span>
                  <p className="text-zinc-300 mt-0.5">
                    {CHECK_ICONS[s.iatf_status] || '⏳'} {s.iatf_status}
                  </p>
                </div>
                <div className="text-xs">
                  <span className="text-zinc-500">Financial</span>
                  <p className="text-zinc-300 mt-0.5">
                    {CHECK_ICONS[s.financial_risk] || '⏳'} {s.financial_risk}
                  </p>
                </div>
                <div className="text-xs">
                  <span className="text-zinc-500">Registration</span>
                  <p className="text-zinc-300 mt-0.5">
                    {CHECK_ICONS[s.corporate_status] || '⏳'} {s.corporate_status}
                  </p>
                </div>
                <div className="text-xs">
                  <span className="text-zinc-500">Rating</span>
                  <p className="text-zinc-300 mt-0.5">
                    {s.google_rating ? `${s.google_rating}/5 (${s.review_count})` : '—'}
                  </p>
                </div>
                <div className="text-xs">
                  <span className="text-zinc-500">Location</span>
                  <Tooltip content={s.headquarters || ''} side="top">
                    <p className="text-zinc-300 mt-0.5 truncate">{s.headquarters}</p>
                  </Tooltip>
                </div>
              </div>

              {/* Strengths & Concerns */}
              <div className="flex gap-6">
                {s.strengths?.length > 0 && (
                  <div className="flex-1">
                    <p className="text-xs text-emerald-500 mb-1">Strengths</p>
                    <ul className="text-xs text-zinc-400 space-y-0.5">
                      {s.strengths.map((str, i) => <li key={i}>+ {str}</li>)}
                    </ul>
                  </div>
                )}
                {s.concerns?.length > 0 && (
                  <div className="flex-1">
                    <p className="text-xs text-amber-500 mb-1">Concerns</p>
                    <ul className="text-xs text-zinc-400 space-y-0.5">
                      {s.concerns.map((c, i) => <li key={i}>- {c}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </div>
            </StaggerItem>
          )
        })}
      </StaggerList>
    </m.div>
  )
}
