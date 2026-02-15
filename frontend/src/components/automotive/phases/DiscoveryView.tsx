'use client'

import { useState } from 'react'
import type { DiscoveredSupplier } from '@/types/automotive'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: (removedIds?: string[]) => void
}

export default function DiscoveryView({ data, isActive, onApprove }: Props) {
  const [removedIds, setRemovedIds] = useState<Set<string>>(new Set())
  const [sortBy, setSortBy] = useState<'initial_score' | 'capability_match' | 'geographic_fit'>('initial_score')

  if (!data) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400">Searching for suppliers...</span>
        </div>
        <p className="text-xs text-zinc-600">Querying Thomasnet, Google Places, trade databases, and web</p>
      </div>
    )
  }

  const suppliers = ((data.suppliers || []) as DiscoveredSupplier[])
    .sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0))

  const totalFound = data.total_found as number || 0
  const sourcesSearched = (data.sources_searched as string[]) || []
  const gaps = (data.gaps_identified as string[]) || []

  const toggleRemove = (id: string) => {
    const next = new Set(removedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setRemovedIds(next)
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Supplier Discovery</h3>
          <p className="text-xs text-zinc-500 mt-1">
            Found {totalFound} suppliers across {sourcesSearched.join(', ')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1 text-xs text-zinc-300"
          >
            <option value="initial_score">Score</option>
            <option value="capability_match">Capability</option>
            <option value="geographic_fit">Geography</option>
          </select>
          {isActive && (
            <button
              onClick={() => onApprove(removedIds.size > 0 ? Array.from(removedIds) : undefined)}
              className="px-4 py-1.5 text-sm bg-amber-500 text-zinc-950 font-semibold rounded-lg hover:bg-amber-400"
            >
              Approve & Qualify ({suppliers.length - removedIds.size})
            </button>
          )}
        </div>
      </div>

      {/* Gaps warning */}
      {gaps.length > 0 && (
        <div className="px-6 py-3 bg-amber-500/10 border-b border-amber-500/20">
          <p className="text-xs text-amber-400">
            {gaps.map((g, i) => <span key={i} className="block">• {g}</span>)}
          </p>
        </div>
      )}

      {/* Supplier list */}
      <div className="divide-y divide-zinc-800">
        {suppliers.map((s, idx) => {
          const isRemoved = removedIds.has(s.supplier_id)
          return (
            <div
              key={s.supplier_id}
              className={`px-6 py-4 flex items-start gap-4 ${isRemoved ? 'opacity-30' : ''}`}
            >
              {isActive && (
                <button
                  onClick={() => toggleRemove(s.supplier_id)}
                  className={`mt-1 w-5 h-5 rounded border flex-shrink-0 flex items-center justify-center text-xs
                    ${isRemoved ? 'border-red-500 bg-red-500/10 text-red-400' : 'border-zinc-600 hover:border-zinc-400'}`}
                >
                  {isRemoved ? '×' : ''}
                </button>
              )}

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-zinc-600 font-mono w-6">{idx + 1}.</span>
                  <h4 className="font-medium text-zinc-200 truncate">{s.company_name}</h4>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 font-mono">
                    {Math.round(s.initial_score)}
                  </span>
                </div>
                <p className="text-xs text-zinc-500 mt-1 ml-9">{s.headquarters}</p>
                <div className="flex items-center gap-4 mt-2 ml-9">
                  {s.known_processes.length > 0 && (
                    <span className="text-xs text-zinc-400">{s.known_processes.join(', ')}</span>
                  )}
                  {s.known_certifications.length > 0 && (
                    <span className="text-xs text-emerald-400">{s.known_certifications.join(', ')}</span>
                  )}
                  {s.employee_count && (
                    <span className="text-xs text-zinc-500">{s.employee_count} employees</span>
                  )}
                </div>
                <div className="flex gap-1 mt-2 ml-9">
                  {s.sources.map((src) => (
                    <span key={src} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500">{src}</span>
                  ))}
                </div>
              </div>

              {s.website && (
                <a
                  href={s.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-zinc-500 hover:text-zinc-300 flex-shrink-0"
                >
                  Website →
                </a>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
