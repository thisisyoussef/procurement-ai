'use client'

import type { QualifiedSupplier } from '@/types/automotive'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: (overrides?: Record<string, string>) => void
}

const STATUS_STYLES = {
  qualified: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  conditional: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  disqualified: 'bg-red-500/15 text-red-400 border-red-500/30',
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
  if (!data) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400">Verifying suppliers...</span>
        </div>
        <p className="text-xs text-zinc-600">Checking IATF, financials, registration, capabilities, reviews</p>
      </div>
    )
  }

  const suppliers = (data.suppliers || []) as QualifiedSupplier[]
  const qCount = data.qualified_count as number || 0
  const cCount = data.conditional_count as number || 0
  const dCount = data.disqualified_count as number || 0

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Supplier Qualification</h3>
          <p className="text-xs text-zinc-500 mt-1">
            {qCount} qualified • {cCount} conditional • {dCount} disqualified
          </p>
        </div>
        {isActive && (
          <button
            onClick={() => onApprove()}
            className="px-4 py-1.5 text-sm bg-amber-500 text-zinc-950 font-semibold rounded-lg hover:bg-amber-400"
          >
            Approve Shortlist
          </button>
        )}
      </div>

      <div className="divide-y divide-zinc-800">
        {suppliers.map((s) => (
          <div key={s.supplier_id} className="px-6 py-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <h4 className="font-medium text-zinc-200">{s.company_name}</h4>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_STYLES[s.qualification_status]}`}>
                  {s.qualification_status.toUpperCase()}
                </span>
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
                <p className="text-zinc-300 mt-0.5 truncate">{s.headquarters}</p>
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
        ))}
      </div>
    </div>
  )
}
