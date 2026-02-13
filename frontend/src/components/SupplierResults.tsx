'use client'

import { useState, useMemo } from 'react'
import StarRating from './StarRating'

interface Supplier {
  name: string
  website: string | null
  product_page_url: string | null
  email: string | null
  phone: string | null
  city: string | null
  country: string | null
  description: string | null
  categories: string[]
  certifications: string[]
  source: string
  relevance_score: number
  estimated_shipping_cost: string | null
  google_rating: number | null
  google_review_count: number | null
  is_intermediary: boolean
  language_discovered: string | null
  filtered_reason?: string | null
  enrichment?: {
    sources_tried: string[]
    sources_succeeded: string[]
    best_email: string | null
    best_phone: string | null
    enrichment_confidence: number
  } | null
}

interface Verification {
  supplier_name: string
  composite_score: number
  risk_level: string
  recommendation: string
  summary: string
  preferred_contact_method?: string
  contact_notes?: string | null
}

interface SupplierResultsProps {
  discovery: {
    suppliers: Supplier[]
    filtered_suppliers?: Supplier[]
    sources_searched: string[]
    sources_failed: string[]
    total_raw_results: number
    deduplicated_count: number
    regional_results: Record<string, number>
    intermediaries_resolved: number
  }
  verifications: {
    verifications: Verification[]
  } | null
}

function getRiskBadge(risk: string) {
  const styles: Record<string, string> = {
    low: 'bg-green-50 text-green-700 border-green-200',
    medium: 'bg-amber-50 text-amber-700 border-amber-200',
    high: 'bg-red-50 text-red-700 border-red-200',
  }
  return styles[risk] || 'bg-slate-50 text-slate-600 border-slate-200'
}

function getSourceBadge(source: string): { label: string; className: string } | null {
  if (source.startsWith('marketplace_etsy')) return { label: 'Etsy', className: 'bg-cyan-50 text-cyan-700 border-cyan-200' }
  if (source.startsWith('marketplace_alibaba')) return { label: 'Alibaba', className: 'bg-orange-50 text-orange-700 border-orange-200' }
  if (source.startsWith('marketplace_amazon')) return { label: 'Amazon', className: 'bg-yellow-50 text-yellow-700 border-yellow-200' }
  if (source === 'google_places') return { label: 'Google', className: 'bg-slate-50 text-slate-600 border-slate-200' }
  if (source.includes('_regional_') || source.includes('regional')) return { label: 'Regional', className: 'bg-violet-50 text-violet-600 border-violet-200' }
  if (source.startsWith('marketplace_')) return { label: source.replace('marketplace_', ''), className: 'bg-teal-50 text-teal-700 border-teal-200' }
  return null
}

function getFilteredReasonBadge(reason: string): { label: string; className: string } {
  switch (reason) {
    case 'retail_store':
      return { label: 'Retail Store', className: 'bg-amber-50 text-amber-700 border-amber-200' }
    case 'wrong_product_type':
      return { label: 'Wrong Product', className: 'bg-red-50 text-red-700 border-red-200' }
    case 'low_relevance':
      return { label: 'Low Relevance', className: 'bg-slate-50 text-slate-500 border-slate-200' }
    default:
      return { label: reason, className: 'bg-slate-50 text-slate-500 border-slate-200' }
  }
}

function ContactBadge({ method, notes }: { method: string; notes?: string | null }) {
  if (method === 'email') return null // Default, no badge needed
  const config: Record<string, { icon: string; label: string; className: string }> = {
    phone: { icon: '\u{1F4DE}', label: 'Best: Phone', className: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
    website_form: { icon: '\u{1F310}', label: 'Best: Web Form', className: 'bg-teal-50 text-teal-700 border-teal-200' },
  }
  const c = config[method]
  if (!c) return null
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full border ${c.className} cursor-help`}
      title={notes || undefined}
    >
      {c.icon} {c.label}
    </span>
  )
}

type SortKey = 'relevance' | 'rating' | 'verification' | 'name'
type FilterCountry = string | 'all'
type ViewTab = 'active' | 'filtered'

export default function SupplierResults({ discovery, verifications }: SupplierResultsProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortKey>('relevance')
  const [filterCountry, setFilterCountry] = useState<FilterCountry>('all')
  const [showIntermediaries, setShowIntermediaries] = useState(true)
  const [expandedCount, setExpandedCount] = useState(10)
  const [activeTab, setActiveTab] = useState<ViewTab>('active')

  const filteredList = discovery.filtered_suppliers || []

  const verificationMap = useMemo(() => {
    const map = new Map<string, Verification>()
    if (verifications?.verifications) {
      for (const v of verifications.verifications) {
        map.set(v.supplier_name, v)
      }
    }
    return map
  }, [verifications])

  // Get unique countries for filter dropdown
  const countries = useMemo(() => {
    const set = new Set<string>()
    for (const s of discovery.suppliers) {
      if (s.country) set.add(s.country)
    }
    return Array.from(set).sort()
  }, [discovery.suppliers])

  // Filter and sort suppliers
  const filteredSuppliers = useMemo(() => {
    const sourceList = activeTab === 'active' ? discovery.suppliers : filteredList
    let list = [...sourceList]

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      list = list.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.description?.toLowerCase().includes(q) ||
          s.categories.some((c) => c.toLowerCase().includes(q)) ||
          s.city?.toLowerCase().includes(q) ||
          s.country?.toLowerCase().includes(q) ||
          s.certifications.some((c) => c.toLowerCase().includes(q))
      )
    }

    // Country filter
    if (filterCountry !== 'all') {
      list = list.filter((s) => s.country === filterCountry)
    }

    // Intermediary filter (only for active tab)
    if (activeTab === 'active' && !showIntermediaries) {
      list = list.filter((s) => !s.is_intermediary)
    }

    // Sort
    list.sort((a, b) => {
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
  }, [discovery.suppliers, filteredList, activeTab, searchQuery, filterCountry, showIntermediaries, sortBy, verificationMap])

  const visibleSuppliers = filteredSuppliers.slice(0, expandedCount)
  const hasMore = filteredSuppliers.length > expandedCount

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">
          Discovered Suppliers
        </h2>
        <div className="flex gap-3 text-xs text-slate-500">
          <span>{discovery.total_raw_results} raw results</span>
          <span>{discovery.deduplicated_count} unique suppliers</span>
          {discovery.intermediaries_resolved > 0 && (
            <span className="text-amber-600">
              {discovery.intermediaries_resolved} intermediaries resolved
            </span>
          )}
        </div>
      </div>

      {/* Tab Buttons */}
      {filteredList.length > 0 && (
        <div className="flex gap-1 mb-4 border-b border-slate-200">
          <button
            onClick={() => { setActiveTab('active'); setExpandedCount(10) }}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'active'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            Active ({discovery.suppliers.length})
          </button>
          <button
            onClick={() => { setActiveTab('filtered'); setExpandedCount(10) }}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'filtered'
                ? 'border-amber-600 text-amber-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            Filtered ({filteredList.length})
          </button>
        </div>
      )}

      {/* Filtered tab explanation */}
      {activeTab === 'filtered' && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          These suppliers were filtered out due to low relevance, being retail-focused, or mismatched product types.
          They are shown here for transparency &mdash; you can review them in case any were incorrectly categorized.
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-slate-50 rounded-lg border border-slate-100">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search suppliers by name, category, location..."
            className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm
                       text-slate-900 placeholder:text-slate-400
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Sort */}
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortKey)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm text-slate-700
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="relevance">Sort: Relevance</option>
          <option value="rating">Sort: Rating</option>
          <option value="verification">Sort: Verification</option>
          <option value="name">Sort: Name</option>
        </select>

        {/* Country filter */}
        <select
          value={filterCountry}
          onChange={(e) => setFilterCountry(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm text-slate-700
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All countries</option>
          {countries.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        {/* Intermediary toggle */}
        {activeTab === 'active' && (
          <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer whitespace-nowrap">
            <input
              type="checkbox"
              checked={showIntermediaries}
              onChange={(e) => setShowIntermediaries(e.target.checked)}
              className="rounded border-slate-300"
            />
            Show intermediaries
          </label>
        )}

        {/* Count */}
        <span className="text-xs text-slate-500 whitespace-nowrap">
          {filteredSuppliers.length} of {activeTab === 'active' ? discovery.suppliers.length : filteredList.length}
        </span>
      </div>

      {/* Supplier List */}
      <div className="space-y-3">
        {visibleSuppliers.map((supplier, i) => {
          const v = verificationMap.get(supplier.name)
          const sourceBadge = getSourceBadge(supplier.source)
          return (
            <div
              key={`${supplier.name}-${i}`}
              className={`border rounded-lg p-4 hover:border-slate-300 transition-colors ${
                activeTab === 'filtered'
                  ? 'border-amber-100 bg-amber-50/20 opacity-80'
                  : supplier.is_intermediary
                  ? 'border-amber-200 bg-amber-50/30'
                  : 'border-slate-100'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-medium text-slate-900">{supplier.name}</h3>
                    {/* Filtered reason badge */}
                    {supplier.filtered_reason && (() => {
                      const badge = getFilteredReasonBadge(supplier.filtered_reason)
                      return (
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${badge.className}`}>
                          {badge.label}
                        </span>
                      )
                    })()}
                    {supplier.is_intermediary && (
                      <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full border border-amber-200">
                        intermediary
                      </span>
                    )}
                    {supplier.language_discovered && supplier.language_discovered !== 'en' && (
                      <span className="text-xs px-2 py-0.5 bg-purple-50 text-purple-600 rounded-full">
                        {supplier.language_discovered}
                      </span>
                    )}
                    {/* Source badge */}
                    {sourceBadge && (
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${sourceBadge.className}`}>
                        {sourceBadge.label}
                      </span>
                    )}
                    {v && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full border ${getRiskBadge(v.risk_level)}`}
                      >
                        {v.risk_level} risk &middot; {Math.round(v.composite_score)}/100
                      </span>
                    )}
                    {/* Contact method badge */}
                    {v?.preferred_contact_method && (
                      <ContactBadge method={v.preferred_contact_method} notes={v.contact_notes} />
                    )}
                    {/* Enrichment indicator */}
                    {supplier.enrichment && supplier.enrichment.sources_succeeded.length > 0 && (
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200"
                        title={`Contact found via: ${supplier.enrichment.sources_succeeded.join(', ')}`}
                      >
                        Contact enriched ({supplier.enrichment.sources_succeeded.length} source{supplier.enrichment.sources_succeeded.length > 1 ? 's' : ''})
                      </span>
                    )}
                  </div>

                  <p className="text-sm text-slate-600 mt-1">
                    {supplier.description?.slice(0, 180) || 'No description available'}
                    {supplier.description && supplier.description.length > 180 ? '...' : ''}
                  </p>

                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-500 flex-wrap">
                    {supplier.city && (
                      <span>
                        {supplier.city}
                        {supplier.country ? `, ${supplier.country}` : ''}
                      </span>
                    )}
                    {supplier.google_rating && (
                      <span className="flex items-center gap-1">
                        <StarRating score={supplier.google_rating} showNumber={true} size="sm" />
                        <span className="text-xs text-slate-400">
                          ({supplier.google_review_count} reviews)
                        </span>
                      </span>
                    )}
                    {supplier.estimated_shipping_cost && (
                      <span className="text-emerald-600 font-medium">
                        Shipping: {supplier.estimated_shipping_cost}
                      </span>
                    )}
                    {supplier.website && (
                      <a
                        href={supplier.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        Website
                      </a>
                    )}
                    {supplier.product_page_url && (
                      <a
                        href={supplier.product_page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline font-medium"
                      >
                        Product Page &rarr;
                      </a>
                    )}
                  </div>

                  {supplier.certifications.length > 0 && (
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {supplier.certifications.slice(0, 5).map((cert) => (
                        <span
                          key={cert}
                          className="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded"
                        >
                          {cert}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="text-right ml-4 shrink-0">
                  <div className="text-2xl font-bold text-slate-900">
                    {Math.round(supplier.relevance_score)}
                  </div>
                  <div className="text-xs text-slate-500">relevance</div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Show More / Show Less */}
      {filteredSuppliers.length > 10 && (
        <div className="mt-4 flex items-center justify-center gap-3">
          {hasMore && (
            <button
              onClick={() => setExpandedCount((c) => Math.min(c + 20, filteredSuppliers.length))}
              className="px-4 py-2 text-sm text-blue-600 bg-blue-50 rounded-lg
                         hover:bg-blue-100 transition-colors font-medium"
            >
              Show more ({filteredSuppliers.length - expandedCount} remaining)
            </button>
          )}
          {expandedCount > 10 && (
            <button
              onClick={() => setExpandedCount(10)}
              className="px-4 py-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
            >
              Show less
            </button>
          )}
          {!hasMore && filteredSuppliers.length > 10 && (
            <span className="text-xs text-slate-400">
              Showing all {filteredSuppliers.length} suppliers
            </span>
          )}
        </div>
      )}

      {filteredSuppliers.length === 0 && (
        <div className="text-center py-8 text-slate-400">
          <p>{activeTab === 'filtered' ? 'No filtered suppliers.' : 'No suppliers match your filters.'}</p>
          {activeTab === 'active' && (
            <button
              onClick={() => {
                setSearchQuery('')
                setFilterCountry('all')
                setShowIntermediaries(true)
              }}
              className="mt-2 text-sm text-blue-600 hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>
      )}
    </div>
  )
}
