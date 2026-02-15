'use client'

import type { SupplierComparison } from '@/types/automotive'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: (weights?: Record<string, number>) => void
}

export default function ComparisonView({ data, isActive, onApprove }: Props) {
  if (!data) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <div className="flex items-center justify-center gap-3">
          <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400">Building comparison matrix...</span>
        </div>
      </div>
    )
  }

  const suppliers = (data.suppliers || []) as SupplierComparison[]
  const topRec = data.top_recommendation as string || ''
  const rationale = data.recommendation_rationale as string || ''

  const dimensions = ['capability', 'quality', 'geographic', 'financial', 'scale', 'reputation'] as const
  const dimLabels: Record<string, string> = {
    capability: 'Capability',
    quality: 'Quality',
    geographic: 'Geography',
    financial: 'Financial',
    scale: 'Scale',
    reputation: 'Reputation',
  }

  const scoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400'
    if (score >= 60) return 'text-amber-400'
    return 'text-red-400'
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="font-semibold">Supplier Comparison Matrix</h3>
        {isActive && (
          <button
            onClick={() => onApprove()}
            className="px-4 py-1.5 text-sm bg-amber-500 text-zinc-950 font-semibold rounded-lg hover:bg-amber-400"
          >
            Approve Rankings
          </button>
        )}
      </div>

      {/* Recommendation */}
      {topRec && (
        <div className="px-6 py-3 bg-amber-500/5 border-b border-amber-500/10">
          <p className="text-sm">
            <span className="text-amber-400 font-semibold">Top Pick:</span>{' '}
            <span className="text-zinc-300">{topRec}</span>
          </p>
          {rationale && <p className="text-xs text-zinc-500 mt-1">{rationale}</p>}
        </div>
      )}

      {/* Matrix table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800">
              <th className="px-4 py-3 text-left text-xs text-zinc-500 font-normal uppercase tracking-wider">Dimension</th>
              {suppliers.map((s) => (
                <th key={s.supplier_id} className="px-4 py-3 text-center text-xs text-zinc-300 font-medium">
                  {s.company_name.length > 15 ? s.company_name.slice(0, 15) + '…' : s.company_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-zinc-700 bg-zinc-800/30">
              <td className="px-4 py-2.5 font-semibold text-zinc-200">COMPOSITE</td>
              {suppliers.map((s) => (
                <td key={s.supplier_id} className="px-4 py-2.5 text-center">
                  <span className={`font-bold text-lg ${scoreColor(s.composite_score)}`}>
                    {Math.round(s.composite_score)}
                  </span>
                </td>
              ))}
            </tr>
            {dimensions.map((dim) => (
              <tr key={dim} className="border-b border-zinc-800/50">
                <td className="px-4 py-2 text-zinc-400">{dimLabels[dim]}</td>
                {suppliers.map((s) => {
                  const score = (s as any)[`${dim}_score`] as number || 0
                  return (
                    <td key={s.supplier_id} className="px-4 py-2 text-center">
                      <span className={`font-mono ${scoreColor(score)}`}>{Math.round(score)}</span>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Supplier cards */}
      <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {suppliers.map((s) => (
          <div key={s.supplier_id} className="bg-zinc-800/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-sm text-zinc-200">{s.company_name}</h4>
              <span className={`text-xs font-bold ${scoreColor(s.composite_score)}`}>
                {Math.round(s.composite_score)}
              </span>
            </div>
            {s.unique_strengths?.length > 0 && (
              <div className="mb-2">
                {s.unique_strengths.map((str, i) => (
                  <p key={i} className="text-xs text-emerald-400/80">+ {str}</p>
                ))}
              </div>
            )}
            {s.notable_risks?.length > 0 && (
              <div className="mb-2">
                {s.notable_risks.map((r, i) => (
                  <p key={i} className="text-xs text-red-400/80">- {r}</p>
                ))}
              </div>
            )}
            {s.best_fit_for && (
              <p className="text-xs text-zinc-500 italic">{s.best_fit_for}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
