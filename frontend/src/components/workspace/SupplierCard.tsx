'use client'

import { useState } from 'react'

interface Supplier {
  name: string
  website: string | null
  product_page_url?: string | null
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
}

interface Verification {
  supplier_name: string
  composite_score: number
  risk_level: string
  recommendation: string
  preferred_contact_method?: string
}

interface SupplierCardProps {
  supplier: Supplier
  verification?: Verification
  dark?: boolean
  onViewProfile?: () => void
}

function getRiskDot(risk: string): string {
  if (risk === 'low') return 'bg-teal'
  if (risk === 'medium') return 'bg-warm'
  if (risk === 'high') return 'bg-red-400'
  return 'bg-ink-4/30'
}

function getSourceLabel(source: string): string | null {
  if (source.startsWith('marketplace_etsy')) return 'Etsy'
  if (source.startsWith('marketplace_alibaba')) return 'Alibaba'
  if (source.startsWith('marketplace_amazon')) return 'Amazon'
  if (source === 'google_places') return 'Google'
  if (source.includes('regional')) return 'Regional'
  if (source.startsWith('marketplace_'))
    return source.replace('marketplace_', '')
  return null
}

function getInitials(name: string): string {
  return name
    .split(/[\s&]+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
}

export default function SupplierCard({
  supplier,
  verification,
  dark = false,
  onViewProfile,
}: SupplierCardProps) {
  const [expanded, setExpanded] = useState(false)
  const sourceLabel = getSourceLabel(supplier.source)
  const score = verification?.composite_score ?? supplier.relevance_score

  const bg = dark ? 'bg-search-surface' : 'bg-white'
  const border = dark ? 'border-white/[0.06]' : 'border-surface-3'
  const textPrimary = dark ? 'text-white' : 'text-ink'
  const textSecondary = dark ? 'text-white/60' : 'text-ink-3'
  const textMuted = dark ? 'text-white/40' : 'text-ink-4'

  return (
    <div
      onClick={() => setExpanded(!expanded)}
      className={`${bg} border ${border} rounded-xl cursor-pointer transition-all hover:shadow-sm`}
    >
      {/* ── Collapsed Row ─────────────────────── */}
      <div className="flex items-center gap-4 px-5 py-4">
        {/* Avatar */}
        <div
          className={`w-9 h-9 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 ${
            dark ? 'bg-white/10 text-white' : 'bg-surface-2 text-ink-3'
          }`}
        >
          {getInitials(supplier.name)}
        </div>

        {/* Name + location */}
        <div className="flex-1 min-w-0">
          <p className={`text-[13px] font-heading ${textPrimary} truncate`}>
            {supplier.name}
          </p>
          {supplier.city && (
            <p className={`text-[10px] ${textMuted}`}>
              {supplier.city}{supplier.country ? `, ${supplier.country}` : ''}
            </p>
          )}
        </div>

        {/* Risk dot */}
        {verification && (
          <span
            className={`status-dot ${getRiskDot(verification.risk_level)}`}
            title={`${verification.risk_level} risk`}
          />
        )}

        {/* Score */}
        <div className="text-right shrink-0">
          <span className={`text-[18px] font-heading ${textPrimary}`}>
            {Math.round(score)}
          </span>
          <p className={`text-[9px] ${textMuted}`}>score</p>
        </div>
      </div>

      {/* ── Expanded Detail ───────────────────── */}
      {expanded && (
        <div className={`px-5 pb-5 pt-0 border-t ${border} animate-fin`}>
          <div className="pt-4 space-y-4">
            {/* Description */}
            {supplier.description && (
              <p className={`text-[12px] leading-relaxed ${textSecondary}`}>
                {supplier.description}
              </p>
            )}

            {/* Specs grid */}
            <div className="grid grid-cols-2 gap-x-8 gap-y-2">
              {sourceLabel && (
                <div>
                  <p className={`text-[9px] uppercase tracking-wider ${textMuted}`}>Source</p>
                  <p className={`text-[12px] ${textSecondary}`}>{sourceLabel}</p>
                </div>
              )}
              {supplier.google_rating && (
                <div>
                  <p className={`text-[9px] uppercase tracking-wider ${textMuted}`}>Google Rating</p>
                  <p className={`text-[12px] ${textSecondary}`}>
                    {supplier.google_rating}/5
                    {supplier.google_review_count ? ` (${supplier.google_review_count} reviews)` : ''}
                  </p>
                </div>
              )}
              {supplier.estimated_shipping_cost && (
                <div>
                  <p className={`text-[9px] uppercase tracking-wider ${textMuted}`}>Est. Shipping</p>
                  <p className={`text-[12px] ${textSecondary}`}>{supplier.estimated_shipping_cost}</p>
                </div>
              )}
              {supplier.is_intermediary && (
                <div>
                  <p className={`text-[9px] uppercase tracking-wider ${textMuted}`}>Type</p>
                  <p className={`text-[12px] ${textSecondary}`}>Intermediary</p>
                </div>
              )}
              {supplier.language_discovered && supplier.language_discovered !== 'en' && (
                <div>
                  <p className={`text-[9px] uppercase tracking-wider ${textMuted}`}>Language</p>
                  <p className={`text-[12px] ${textSecondary}`}>{supplier.language_discovered}</p>
                </div>
              )}
            </div>

            {/* Score bar */}
            {verification && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <p className={`text-[9px] uppercase tracking-wider ${textMuted}`}>Composite Score</p>
                  <p className={`text-[11px] font-semibold ${textPrimary}`}>{Math.round(verification.composite_score)}/100</p>
                </div>
                <div className={`score-bar ${dark ? '!bg-white/10' : ''}`}>
                  <div
                    className={`score-bar-fill ${dark ? '!bg-teal' : ''}`}
                    style={{ width: `${Math.min(verification.composite_score, 100)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Certifications */}
            {supplier.certifications.length > 0 && (
              <div>
                <p className={`text-[9px] uppercase tracking-wider ${textMuted} mb-1.5`}>Certifications</p>
                <div className="flex gap-1.5 flex-wrap">
                  {supplier.certifications.map((cert) => (
                    <span
                      key={cert}
                      className={`text-[10px] px-2 py-0.5 rounded-full ${
                        dark
                          ? 'bg-teal/10 text-teal border border-teal/20'
                          : 'bg-teal/5 text-teal border border-teal/15'
                      }`}
                    >
                      {cert}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Contact links */}
            <div className={`flex items-center gap-4 pt-1 text-[11px]`}>
              {onViewProfile && (
                <button
                  onClick={(e) => { e.stopPropagation(); onViewProfile() }}
                  className="text-teal hover:underline font-medium"
                >
                  View profile
                </button>
              )}
              {supplier.website && (
                <a
                  href={supplier.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-teal hover:underline"
                >
                  Website
                </a>
              )}
              {supplier.product_page_url && (
                <a
                  href={supplier.product_page_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-teal hover:underline"
                >
                  Product Page
                </a>
              )}
              {supplier.email && (
                <a
                  href={`mailto:${supplier.email}`}
                  onClick={(e) => e.stopPropagation()}
                  className="text-teal hover:underline"
                >
                  Email
                </a>
              )}
              {supplier.phone && (
                <span className={textSecondary}>{supplier.phone}</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
