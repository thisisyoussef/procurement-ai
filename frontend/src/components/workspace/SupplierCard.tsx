'use client'

import StarRating from '@/components/StarRating'

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

export default function SupplierCard({
  supplier,
  verification,
}: SupplierCardProps) {
  const sourceLabel = getSourceLabel(supplier.source)
  const riskColor =
    verification?.risk_level === 'low'
      ? 'text-green-400 bg-green-400/10 border-green-400/20'
      : verification?.risk_level === 'medium'
      ? 'text-amber-400 bg-amber-400/10 border-amber-400/20'
      : verification?.risk_level === 'high'
      ? 'text-red-400 bg-red-400/10 border-red-400/20'
      : ''

  return (
    <div className="glass-card p-4 hover:border-teal/30 transition-all group">
      {/* Header row */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-workspace-text truncate group-hover:text-teal transition-colors">
            {supplier.name}
          </h3>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {supplier.city && (
              <span className="text-[11px] text-workspace-muted">
                {supplier.city}
                {supplier.country ? `, ${supplier.country}` : ''}
              </span>
            )}
            {supplier.is_intermediary && (
              <span className="text-[9px] px-1.5 py-0.5 bg-amber-400/10 text-amber-400 rounded border border-amber-400/20">
                intermediary
              </span>
            )}
          </div>
        </div>

        {/* Relevance score */}
        <div className="text-right ml-3 shrink-0">
          <span className="text-lg font-bold text-workspace-text">
            {Math.round(supplier.relevance_score)}
          </span>
          <p className="text-[9px] text-workspace-muted">relevance</p>
        </div>
      </div>

      {/* Description */}
      {supplier.description && (
        <p className="text-xs text-workspace-muted leading-relaxed mb-3 line-clamp-2">
          {supplier.description}
        </p>
      )}

      {/* Badges row */}
      <div className="flex items-center gap-1.5 flex-wrap mb-3">
        {verification && (
          <span
            className={`text-[10px] px-2 py-0.5 rounded-full border ${riskColor}`}
          >
            {verification.risk_level} risk · {Math.round(verification.composite_score)}
          </span>
        )}
        {sourceLabel && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-workspace-hover text-workspace-muted border border-workspace-border">
            {sourceLabel}
          </span>
        )}
        {supplier.language_discovered &&
          supplier.language_discovered !== 'en' && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
              {supplier.language_discovered}
            </span>
          )}
      </div>

      {/* Rating */}
      {supplier.google_rating && (
        <div className="flex items-center gap-2 mb-3">
          <StarRating
            score={supplier.google_rating}
            showNumber={true}
            size="sm"
          />
          {supplier.google_review_count && (
            <span className="text-[10px] text-workspace-muted">
              ({supplier.google_review_count})
            </span>
          )}
        </div>
      )}

      {/* Certifications */}
      {supplier.certifications.length > 0 && (
        <div className="flex gap-1 flex-wrap mb-3">
          {supplier.certifications.slice(0, 3).map((cert) => (
            <span
              key={cert}
              className="text-[9px] px-1.5 py-0.5 bg-teal/10 text-teal rounded border border-teal/20"
            >
              {cert}
            </span>
          ))}
          {supplier.certifications.length > 3 && (
            <span className="text-[9px] text-workspace-muted">
              +{supplier.certifications.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Footer links */}
      <div className="flex items-center gap-3 text-[11px]">
        {supplier.website && (
          <a
            href={supplier.website}
            target="_blank"
            rel="noopener noreferrer"
            className="text-teal hover:text-teal-300 transition-colors"
          >
            Website →
          </a>
        )}
        {supplier.product_page_url && (
          <a
            href={supplier.product_page_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-teal hover:text-teal-300 transition-colors font-medium"
          >
            Product →
          </a>
        )}
        {supplier.estimated_shipping_cost && (
          <span className="text-workspace-muted">
            Ship: {supplier.estimated_shipping_cost}
          </span>
        )}
      </div>
    </div>
  )
}
