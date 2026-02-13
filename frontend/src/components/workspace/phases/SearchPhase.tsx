'use client'

import { useState, useMemo } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import SupplierCard from '../SupplierCard'

type SortKey = 'relevance' | 'rating' | 'verification' | 'name'

const SEARCH_STEPS = [
  { stage: 'discovering', label: 'Discovering suppliers worldwide' },
  { stage: 'verifying', label: 'Verifying credentials & websites' },
]

export default function SearchPhase() {
  const { status, loading } = useWorkspace()

  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortKey>('relevance')
  const [filterCountry, setFilterCountry] = useState('all')
  const [showIntermediaries, setShowIntermediaries] = useState(true)
  const [visibleCount, setVisibleCount] = useState(12)

  const suppliers = status?.discovery_results?.suppliers || []
  const verifications = status?.verification_results?.verifications || []
  const currentStage = status?.current_stage || 'idle'
  const productType = status?.parsed_requirements?.product_type || 'your product'

  // Verification map
  const verificationMap = useMemo(() => {
    const map = new Map<string, any>()
    for (const v of verifications) {
      map.set(v.supplier_name, v)
    }
    return map
  }, [verifications])

  // Unique countries
  const countries = useMemo(() => {
    const set = new Set<string>()
    for (const s of suppliers) {
      if (s.country) set.add(s.country)
    }
    return Array.from(set).sort()
  }, [suppliers])

  // Filter + sort
  const filtered = useMemo(() => {
    let list = [...suppliers]

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      list = list.filter(
        (s: any) =>
          s.name.toLowerCase().includes(q) ||
          s.description?.toLowerCase().includes(q) ||
          s.categories?.some((c: string) => c.toLowerCase().includes(q)) ||
          s.city?.toLowerCase().includes(q) ||
          s.country?.toLowerCase().includes(q)
      )
    }

    if (filterCountry !== 'all') {
      list = list.filter((s: any) => s.country === filterCountry)
    }

    if (!showIntermediaries) {
      list = list.filter((s: any) => !s.is_intermediary)
    }

    list.sort((a: any, b: any) => {
      switch (sortBy) {
        case 'relevance':
          return b.relevance_score - a.relevance_score
        case 'rating':
          return (b.google_rating || 0) - (a.google_rating || 0)
        case 'verification': {
          const va = verificationMap.get(a.name)?.composite_score || 0
          const vb = verificationMap.get(b.name)?.composite_score || 0
          return vb - va
        }
        case 'name':
          return a.name.localeCompare(b.name)
        default:
          return 0
      }
    })

    return list
  }, [suppliers, searchQuery, filterCountry, showIntermediaries, sortBy, verificationMap])

  const visible = filtered.slice(0, visibleCount)

  // ─── Dark searching state ────────────────────────────
  if (!status?.discovery_results) {
    return (
      <div className="bg-white min-h-[80vh] -mx-0 flex flex-col items-center justify-center relative overflow-hidden">
        {/* Breathing glow */}
        <div
          className="absolute top-1/2 left-1/2 w-64 h-64 rounded-full bg-teal/10 animate-breathe pointer-events-none"
          style={{ filter: 'blur(80px)' }}
        />

        {loading ? (
          <div className="relative z-10 text-center px-6">
            <p className="text-ink font-heading text-2xl mb-2">
              Searching the world for{' '}
              <em className="text-teal">{productType}</em>
            </p>
            <p className="text-ink-4 text-[13px] mb-10">
              This usually takes 1-3 minutes
            </p>

            {/* Progress steps */}
            <div className="flex flex-col items-start gap-4 max-w-xs mx-auto">
              {SEARCH_STEPS.map((step) => {
                const isDone =
                  step.stage === 'discovering'
                    ? !!status?.discovery_results
                    : step.stage === 'verifying'
                    ? !!status?.verification_results
                    : false
                const isActive = currentStage === step.stage

                return (
                  <div key={step.stage} className="flex items-center gap-3">
                    <span
                      className={`status-dot ${
                        isDone
                          ? 'bg-teal/40'
                          : isActive
                          ? 'bg-teal animate-pulse-dot'
                          : 'bg-surface-3'
                      }`}
                    />
                    <span
                      className={`text-[12px] ${
                        isActive ? 'text-ink' : isDone ? 'text-ink-3' : 'text-ink-4'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* Large counter */}
            {suppliers.length > 0 && (
              <div className="mt-10">
                <span className="text-5xl font-heading text-teal">
                  {suppliers.length}
                </span>
                <p className="text-ink-4 text-[11px] mt-1">suppliers found</p>
              </div>
            )}
          </div>
        ) : (
          <div className="relative z-10 text-center px-6">
            <p className="text-ink-4 text-[13px]">
              No supplier results yet. Start a project in the Brief phase.
            </p>
          </div>
        )}
      </div>
    )
  }

  // ─── Results with dark background ────────────────────
  return (
    <div className="bg-white min-h-[80vh] px-6 py-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-heading text-ink">
              Discovered Suppliers
            </h2>
            <div className="flex gap-3 text-[11px] text-ink-4 mt-1">
              <span>{status.discovery_results.total_raw_results} raw</span>
              <span>{status.discovery_results.deduplicated_count} unique</span>
              <span>{suppliers.length} active</span>
            </div>
          </div>

          {/* Still processing indicator */}
          {(currentStage === 'discovering' || currentStage === 'verifying') && (
            <div className="flex items-center gap-2 text-[11px] text-teal">
              <span className="status-dot bg-teal animate-pulse-dot" />
              {currentStage === 'discovering' ? 'Finding more...' : 'Verifying...'}
            </div>
          )}
        </div>

        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter suppliers..."
            className="flex-1 min-w-[160px] bg-white border border-surface-3 rounded-lg px-3 py-2 text-[12px]
                       text-ink placeholder:text-ink-4
                       focus:outline-none focus:ring-1 focus:ring-teal/30 focus:border-teal/30"
          />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortKey)}
            className="bg-white border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink-3
                       focus:outline-none focus:ring-1 focus:ring-teal/30"
          >
            <option value="relevance">Relevance</option>
            <option value="rating">Rating</option>
            <option value="verification">Verification</option>
            <option value="name">Name</option>
          </select>
          <select
            value={filterCountry}
            onChange={(e) => setFilterCountry(e.target.value)}
            className="bg-white border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink-3
                       focus:outline-none focus:ring-1 focus:ring-teal/30"
          >
            <option value="all">All countries</option>
            {countries.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <label className="flex items-center gap-1.5 text-[11px] text-ink-4 cursor-pointer">
            <input
              type="checkbox"
              checked={showIntermediaries}
              onChange={(e) => setShowIntermediaries(e.target.checked)}
              className="rounded border-white/20 accent-teal"
            />
            Intermediaries
          </label>
          <span className="text-[11px] text-ink-4">
            {filtered.length} of {suppliers.length}
          </span>
        </div>

        {/* Supplier list */}
        <div className="space-y-2">
          {visible.map((supplier: any, i: number) => (
            <SupplierCard
              key={`${supplier.name}-${i}`}
              supplier={supplier}
              verification={verificationMap.get(supplier.name)}
            />
          ))}
        </div>

        {/* Show more */}
        {filtered.length > 12 && (
          <div className="mt-6 flex items-center justify-center gap-3">
            {visibleCount < filtered.length && (
              <button
                onClick={() => setVisibleCount((c) => Math.min(c + 12, filtered.length))}
                className="px-4 py-2 text-[12px] text-teal border border-teal/20 rounded-lg
                           hover:bg-teal/10 transition-colors"
              >
                Show more ({filtered.length - visibleCount} remaining)
              </button>
            )}
            {visibleCount > 12 && (
              <button
                onClick={() => setVisibleCount(12)}
                className="px-4 py-2 text-[12px] text-ink-4 hover:text-ink-3 transition-colors"
              >
                Show less
              </button>
            )}
          </div>
        )}

        {filtered.length === 0 && (
          <div className="text-center py-12">
            <p className="text-ink-4 text-[13px]">No suppliers match your filters.</p>
            <button
              onClick={() => {
                setSearchQuery('')
                setFilterCountry('all')
                setShowIntermediaries(true)
              }}
              className="mt-2 text-[12px] text-teal hover:underline"
            >
              Clear filters
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
