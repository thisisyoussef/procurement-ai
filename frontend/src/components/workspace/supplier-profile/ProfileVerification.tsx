'use client'

import type {
  SupplierProfileVerification,
  SupplierProfileCompanyDetails,
  SupplierProfileHeroStats,
} from '@/types/supplierProfile'

interface Props {
  verification: SupplierProfileVerification
  company: SupplierProfileCompanyDetails
  heroStats: SupplierProfileHeroStats
}

export default function ProfileVerification({ verification, company, heroStats }: Props) {
  const { composite_score, risk_level, checks, summary } = verification

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {/* Business Verification */}
      <div className="bg-surface border border-black/[.06] rounded-[14px] px-6 py-5">
        <div className="flex items-center gap-2 text-[13px] font-semibold text-ink mb-3">
          <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0" />
          Business verification
        </div>
        <div className="flex flex-col gap-2">
          <VeriRow label="Verification score" value={`${Math.round(composite_score)}/100`} />
          <VeriRow label="Risk level" value={
            <RiskBadge level={risk_level} />
          } />
          {checks.map((check) => (
            <VeriRow
              key={check.check_type}
              label={formatCheckType(check.check_type)}
              value={<CheckStatus status={check.status} score={check.score} />}
            />
          ))}
        </div>
      </div>

      {/* Reputation */}
      <div className="bg-surface border border-black/[.06] rounded-[14px] px-6 py-5">
        <div className="flex items-center gap-2 text-[13px] font-semibold text-ink mb-3">
          <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0" />
          Reputation
        </div>
        <div className="flex flex-col gap-2">
          {heroStats.google_rating != null && (
            <VeriRow
              label="Average rating"
              value={`${heroStats.google_rating.toFixed(1)}${heroStats.google_review_count ? ` across ${heroStats.google_review_count} reviews` : ''}`}
            />
          )}
          {company.source && company.source !== 'unknown' && (
            <VeriRow label="Source" value={formatSource(company.source)} />
          )}
          {company.certifications.length > 0 && (
            <VeriRow label="Certifications" value={company.certifications.join(', ')} />
          )}
          {company.is_intermediary && (
            <VeriRow label="Type" value="Intermediary / Trading company" />
          )}
          {summary && (
            <div className="mt-2 pt-2 border-t border-black/[.03]">
              <p className="text-[12px] text-ink-3 leading-relaxed">{summary}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function VeriRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center py-1.5 text-[12.5px] border-b border-black/[.03] last:border-b-0">
      <span className="text-ink-3">{label}</span>
      <span className="text-ink-2 font-medium text-right">{value}</span>
    </div>
  )
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    low: 'bg-teal/10 text-teal',
    medium: 'bg-warm/10 text-warm',
    high: 'bg-red-100 text-red-600',
  }
  const cls = colors[level] || 'bg-ink-4/10 text-ink-4'
  return (
    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${cls}`}>
      {level}
    </span>
  )
}

function CheckStatus({ status, score }: { status: string; score: number }) {
  if (status === 'passed') {
    return <span className="text-teal font-semibold">Verified</span>
  }
  if (status === 'failed') {
    return <span className="text-red-500 font-semibold">Failed</span>
  }
  return <span className="text-ink-4">Not available</span>
}

function formatCheckType(type: string): string {
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatSource(source: string): string {
  const map: Record<string, string> = {
    google_places: 'Google Places',
    marketplace_alibaba: 'Alibaba',
    marketplace_etsy: 'Etsy',
    thomasnet: 'ThomasNet',
    importyeti: 'ImportYeti',
    firecrawl: 'Web Discovery',
  }
  return map[source] || source.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
