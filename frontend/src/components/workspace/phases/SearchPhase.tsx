'use client'

import { useState, useMemo } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import SupplierCard from '../SupplierCard'

type SortKey = 'relevance' | 'rating' | 'verification' | 'name'

export default function SearchPhase() {
  const { status, loading } = useWorkspace()

  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortKey>('relevance')
  const [filterCountry, setFilterCountry] = useState('all')
  const [showIntermediaries, setShowIntermediaries] = useState(true)
  const [visibleCount, setVisibleCount] = useState(12)

  const suppliers = status?.discovery_results?.suppliers || []
  const verifications = status?.verification_results?.verifications || []

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

  // Loading state
  if (!status?.discovery_results) {
    return (
      <div className="text-center py-16">
        {loading ? (
          <div className="inline-flex items-center gap-3 px-6 py-3 glass-card">
            <span className="w-2 h-2 rounded-full bg-teal animate-pulse" />
            <span className="text-sm text-workspace-text">
              {status?.current_stage === 'discovering'
                ? 'Discovering suppliers...'
                : status?.current_stage === 'verifying'
                ? 'Verifying suppliers...'
                : 'Working...'}
            </span>
          </div>
        ) : (
          <p className="text-workspace-muted text-sm">
            No supplier results yet. Start a project in the Brief phase.
          </p>
        )}
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-heading text-workspace-text">
            Discovered Suppliers
          </h2>
          <div className="flex gap-3 text-xs text-workspace-muted mt-1">
            <span>{status.discovery_results.total_raw_results} raw</span>
            <span>{status.discovery_results.deduplicated_count} unique</span>
            <span>{suppliers.length} active</span>
          </div>
        </div>

        {/* Still verifying indicator */}
        {(status.current_stage === 'discovering' ||
          status.current_stage === 'verifying') && (
          <div className="flex items-center gap-2 px-3 py-1.5 glass-card text-xs text-teal">
            <span className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse" />
            {status.current_stage === 'discovering'
              ? 'Finding more...'
              : 'Verifying...'}
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 mb-5 p-3 glass-card">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search suppliers..."
          className="flex-1 min-w-[180px] bg-workspace-bg border border-workspace-border rounded-lg px-3 py-1.5 text-sm
                     text-workspace-text placeholder:text-workspace-muted/50
                     focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal/50"
        />
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortKey)}
          className="bg-workspace-bg border border-workspace-border rounded-lg px-3 py-1.5 text-sm text-workspace-muted
                     focus:outline-none focus:ring-2 focus:ring-teal/30"
        >
          <option value="relevance">Relevance</option>
          <option value="rating">Rating</option>
          <option value="verification">Verification</option>
          <option value="name">Name</option>
        </select>
        <select
          value={filterCountry}
          onChange={(e) => setFilterCountry(e.target.value)}
          className="bg-workspace-bg border border-workspace-border rounded-lg px-3 py-1.5 text-sm text-workspace-muted
                     focus:outline-none focus:ring-2 focus:ring-teal/30"
        >
          <option value="all">All countries</option>
          {countries.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-[11px] text-workspace-muted cursor-pointer">
          <input
            type="checkbox"
            checked={showIntermediaries}
            onChange={(e) => setShowIntermediaries(e.target.checked)}
            className="rounded border-workspace-border accent-teal"
          />
          Intermediaries
        </label>
        <span className="text-[11px] text-workspace-muted">
          {filtered.length} of {suppliers.length}
        </span>
      </div>

      {/* Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {visible.map((supplier: any, i: number) => (
          <SupplierCard
            key={`${supplier.name}-${i}`}
            supplier={supplier}
            verification={verificationMap.get(supplier.name)}
          />
        ))}
      </div>

      {/* Show more / less */}
      {filtered.length > 12 && (
        <div className="mt-6 flex items-center justify-center gap-3">
          {visibleCount < filtered.length && (
            <button
              onClick={() => setVisibleCount((c) => Math.min(c + 12, filtered.length))}
              className="px-4 py-2 text-sm text-teal bg-teal/10 rounded-lg
                         hover:bg-teal/20 transition-colors font-medium border border-teal/20"
            >
              Show more ({filtered.length - visibleCount} remaining)
            </button>
          )}
          {visibleCount > 12 && (
            <button
              onClick={() => setVisibleCount(12)}
              className="px-4 py-2 text-sm text-workspace-muted hover:text-workspace-text transition-colors"
            >
              Show less
            </button>
          )}
        </div>
      )}

      {filtered.length === 0 && (
        <div className="text-center py-12 text-workspace-muted">
          <p>No suppliers match your filters.</p>
          <button
            onClick={() => {
              setSearchQuery('')
              setFilterCountry('all')
              setShowIntermediaries(true)
            }}
            className="mt-2 text-sm text-teal hover:text-teal-300"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  )
}
