'use client'

import { useState } from 'react'
import type { SupplierComparison } from '@/types/automotive'
import StageActionButton from '@/components/automotive/shared/StageActionButton'
import ScoreBar from '@/components/automotive/shared/ScoreBar'
import ProcessingState from '@/components/automotive/shared/ProcessingState'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: (weights?: Record<string, number>) => void
  weightProfile?: Record<string, number>
}

const DEFAULT_WEIGHTS: Record<string, number> = {
  capability: 20,
  quality: 20,
  geographic: 15,
  financial: 15,
  scale: 15,
  reputation: 15,
}

export default function ComparisonView({ data, isActive, onApprove, weightProfile }: Props) {
  const [showWeights, setShowWeights] = useState(false)
  const [weights, setWeights] = useState<Record<string, number>>(weightProfile || DEFAULT_WEIGHTS)

  if (!data) {
    return <ProcessingState stage="compare" variant={isActive ? 'processing' : 'waiting'} />
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

  const hasCustomWeights = JSON.stringify(weights) !== JSON.stringify(DEFAULT_WEIGHTS)

  // Find highest score per dimension for highlighting
  const highestPerDim: Record<string, string> = {}
  dimensions.forEach(dim => {
    let maxScore = -1
    let maxId = ''
    suppliers.forEach(s => {
      const score = (s as any)[`${dim}_score`] as number || 0
      if (score > maxScore) { maxScore = score; maxId = s.supplier_id }
    })
    highestPerDim[dim] = maxId
  })

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="font-semibold">Supplier Comparison Matrix</h3>
        <div className="flex items-center gap-3">
          {isActive && (
            <button
              onClick={() => setShowWeights(!showWeights)}
              className="px-3 py-1.5 text-sm bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700"
            >
              {showWeights ? 'Hide Weights' : 'Adjust Weights'}
            </button>
          )}
          {isActive && (
            <StageActionButton
              stage="compare"
              onClick={() => onApprove(hasCustomWeights ? weights : undefined)}
            />
          )}
        </div>
      </div>

      {/* Weight adjustment sliders */}
      {showWeights && (
        <div className="px-6 py-4 bg-zinc-800/30 border-b border-zinc-800">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-zinc-400">Adjust dimension weights to change ranking priorities</p>
            <button
              onClick={() => setWeights(DEFAULT_WEIGHTS)}
              className="text-xs text-zinc-500 hover:text-zinc-300"
            >
              Reset to Default
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {dimensions.map(dim => (
              <div key={dim} className="flex items-center gap-2">
                <label className="text-xs text-zinc-400 w-20">{dimLabels[dim]}</label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={weights[dim] || 0}
                  onChange={(e) => setWeights(prev => ({ ...prev, [dim]: Number(e.target.value) }))}
                  className="flex-1 h-1 accent-amber-500"
                />
                <span className="text-xs text-zinc-500 font-mono w-6 text-right">{weights[dim]}</span>
              </div>
            ))}
          </div>
        </div>
      )}

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

      {/* Matrix table — desktop */}
      <div className="overflow-x-auto hidden md:block">
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
                <td key={s.supplier_id} className="px-4 py-2.5">
                  <div className="flex flex-col items-center gap-1">
                    <ScoreBar value={s.composite_score} size="md" />
                  </div>
                </td>
              ))}
            </tr>
            {dimensions.map((dim) => (
              <tr key={dim} className="border-b border-zinc-800/50">
                <td className="px-4 py-2 text-zinc-400">{dimLabels[dim]}</td>
                {suppliers.map((s) => {
                  const score = (s as any)[`${dim}_score`] as number || 0
                  const isHighest = highestPerDim[dim] === s.supplier_id
                  return (
                    <td key={s.supplier_id} className={`px-4 py-2 ${isHighest ? 'bg-emerald-500/5' : ''}`}>
                      <ScoreBar value={score} size="sm" />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Matrix cards — mobile */}
      <div className="md:hidden p-4 space-y-3">
        {suppliers.map((s) => (
          <div key={s.supplier_id} className="bg-zinc-800/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-sm text-zinc-200">{s.company_name}</h4>
              <ScoreBar value={s.composite_score} size="md" />
            </div>
            <div className="space-y-2">
              {dimensions.map(dim => {
                const score = (s as any)[`${dim}_score`] as number || 0
                return (
                  <div key={dim} className="flex items-center gap-2">
                    <span className="text-xs text-zinc-500 w-20">{dimLabels[dim]}</span>
                    <div className="flex-1">
                      <ScoreBar value={score} size="sm" />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Supplier detail cards */}
      <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {suppliers.map((s) => (
          <div key={s.supplier_id} className="bg-zinc-800/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-sm text-zinc-200">{s.company_name}</h4>
              <ScoreBar value={s.composite_score} size="sm" />
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
