'use client'

import { useState, useMemo } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import SupplierCard from '../SupplierCard'
import { m } from '@/lib/motion'
import { staggerContainer, cardEntrance } from '@/lib/motion/variants'
import StageAnimationRouter from '@/components/animation/StageAnimationRouter'

type SortKey = 'relevance' | 'rating' | 'verification' | 'name'

export default function SearchPhase() {
  const { status, loading, restartCurrentProject, setActivePhase } = useWorkspace()
  const searchParams = useSearchParams()
  const router = useRouter()

  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortKey>('relevance')
  const [filterCountry, setFilterCountry] = useState('all')
  const [showIntermediaries, setShowIntermediaries] = useState(true)
  const [visibleCount, setVisibleCount] = useState(12)
  const [restarting, setRestarting] = useState(false)

  const discoveryResults = status?.discovery_results
  const suppliers = discoveryResults?.suppliers || []
  const filteredSuppliers = discoveryResults?.filtered_suppliers || []
  const verifications = status?.verification_results?.verifications || []
  const currentStage = status?.current_stage || 'idle'
  const productType = status?.parsed_requirements?.product_type || 'your product'
  const totalRawResults = discoveryResults?.total_raw_results || 0
  const deduplicatedCount = discoveryResults?.deduplicated_count || suppliers.length

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

  // ─── Searching / discovering / verifying state ───────
  if (!discoveryResults) {
    if (loading) return <StageAnimationRouter />
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <p className="text-ink-4 text-[13px]">
          No supplier results yet. Start a project in the Brief phase.
        </p>
      </div>
    )
  }

  if (suppliers.length === 0) {
    const allFiltered = filteredSuppliers.length > 0
    const hasPipelineError = Boolean(status?.error)
    const canRestart = !restarting && currentStage !== 'discovering'

    return (
      <div className="bg-white min-h-[80vh] px-6 py-8">
        <div className="max-w-3xl mx-auto space-y-5">
          <div>
            <h2 className="text-xl font-heading text-ink">Discovered Suppliers</h2>
            <div className="flex gap-3 text-[11px] text-ink-4 mt-1">
              <span>{totalRawResults} raw</span>
              <span>{deduplicatedCount} unique</span>
              <span>{suppliers.length} active</span>
            </div>
          </div>

          {hasPipelineError && (
            <div className="card border-l-[3px] border-l-red-400 px-5 py-4">
              <p className="text-[12px] font-medium text-ink-2">Pipeline stopped before shortlist generation.</p>
              <p className="text-[11px] text-ink-3 mt-1">{status?.error}</p>
            </div>
          )}

          <div className="card p-6">
            <p className="text-[13px] text-ink-2 font-medium">
              No viable suppliers are available yet for {productType}.
            </p>
            <p className="text-[11px] text-ink-4 mt-2 leading-relaxed">
              {allFiltered
                ? `${filteredSuppliers.length} candidates were found but filtered out as low-quality or off-category.`
                : totalRawResults > 0
                  ? 'Raw candidates were found, but none passed deduplication and verification readiness.'
                  : 'No candidate suppliers were found from the current search strategy.'}
            </p>

            <div className="flex flex-wrap items-center gap-3 mt-4">
              <button
                onClick={async () => {
                  setRestarting(true)
                  try {
                    await restartCurrentProject({ fromStage: 'discovering' })
                  } finally {
                    setRestarting(false)
                  }
                }}
                disabled={!canRestart}
                className="px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {restarting ? 'Restarting…' : 'Restart supplier search'}
              </button>
              <button
                onClick={() => setActivePhase('brief')}
                className="px-4 py-2 border border-surface-3 rounded-lg text-[12px] text-ink-3 hover:bg-surface-2 transition-colors"
              >
                Refine brief
              </button>
            </div>
          </div>
        </div>
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
              <span>{totalRawResults} raw</span>
              <span>{deduplicatedCount} unique</span>
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
        <m.div
          className="space-y-2"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {visible.map((supplier: any, i: number) => {
            const originalIndex = suppliers.indexOf(supplier)
            return (
              <m.div key={`${supplier.name}-${i}`} variants={cardEntrance}>
                <SupplierCard
                  supplier={supplier}
                  verification={verificationMap.get(supplier.name)}
                  onViewProfile={originalIndex >= 0 ? () => {
                    const params = new URLSearchParams(searchParams.toString())
                    params.set('supplierIndex', String(originalIndex))
                    router.push(`/product?${params.toString()}`)
                  } : undefined}
                />
              </m.div>
            )
          })}
        </m.div>

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
