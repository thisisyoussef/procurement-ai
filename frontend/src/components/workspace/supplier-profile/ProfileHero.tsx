'use client'

import { Send, MessageSquare } from 'lucide-react'
import type { SupplierProfileResponse } from '@/types/supplierProfile'

interface Props {
  profile: SupplierProfileResponse
}

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() || '')
    .join('')
}

export default function ProfileHero({ profile }: Props) {
  const { hero_stats, company } = profile
  const location = [company.city, company.country].filter(Boolean).join(', ')

  return (
    <div className="pt-8 pb-8 border-b border-black/[.06] mb-12 animate-fin" style={{ animationDelay: '0.05s' }}>
      {/* Top row: identity + actions */}
      <div className="flex items-start justify-between gap-8 mb-7 flex-col sm:flex-row">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-surface-2 flex items-center justify-center text-[22px] font-extrabold text-ink-4 shrink-0">
            {getInitials(profile.name)}
          </div>
          <div>
            <h1 className="font-heading text-[clamp(28px,3.5vw,40px)] font-normal tracking-tight leading-[1.05] mb-1">
              {profile.name}
            </h1>
            {location && (
              <div className="flex items-center gap-1.5 text-[13px] text-ink-3">
                <span className="w-[5px] h-[5px] rounded-full bg-teal opacity-40" />
                {location}
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-2 shrink-0 pt-1">
          <button className="px-5 py-2.5 rounded-[10px] text-[12px] font-semibold bg-teal text-white shadow-[0_4px_12px_rgba(0,201,167,.12)] hover:shadow-[0_6px_20px_rgba(0,201,167,.2)] hover:-translate-y-px transition-all flex items-center gap-2">
            <Send size={13} />
            Request samples
          </button>
          <button className="px-5 py-2.5 rounded-[10px] text-[12px] font-semibold bg-surface text-ink-3 border border-black/[.06] hover:border-black/[.12] transition-all flex items-center gap-2">
            <MessageSquare size={13} />
            Message
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex gap-10 flex-wrap">
        {hero_stats.unit_price && (
          <StatItem
            value={hero_stats.unit_price.startsWith('$') ? hero_stats.unit_price : `$${hero_stats.unit_price}`}
            label="Per unit quote"
            accent
            badge={hero_stats.unit_price_source === 'quoted' ? 'Quoted' : undefined}
          />
        )}
        {hero_stats.moq && (
          <StatItem value={hero_stats.moq} label="Minimum order" />
        )}
        {hero_stats.lead_time && (
          <StatItem value={hero_stats.lead_time} label="Lead time" />
        )}
        {hero_stats.google_rating != null && (
          <StatItem
            value={hero_stats.google_rating.toFixed(1)}
            label={hero_stats.google_review_count ? `${hero_stats.google_review_count} reviews` : 'Avg rating'}
          />
        )}
        {hero_stats.response_time_hours != null && (
          <StatItem
            value={hero_stats.response_time_hours < 1
              ? `${Math.round(hero_stats.response_time_hours * 60)}m`
              : `${hero_stats.response_time_hours}h`}
            label="Response time"
          />
        )}
      </div>
    </div>
  )
}

function StatItem({ value, label, accent, badge }: {
  value: string
  label: string
  accent?: boolean
  badge?: string
}) {
  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2">
        <span className={`font-heading text-[28px] tracking-tight leading-none ${accent ? 'text-teal' : ''}`}>
          {value}
        </span>
        {badge && (
          <span className="text-[8px] font-bold uppercase tracking-wider text-teal bg-teal/10 px-1.5 py-0.5 rounded-full">
            {badge}
          </span>
        )}
      </div>
      <span className="text-[10.5px] text-ink-4 mt-1 tracking-wide">{label}</span>
    </div>
  )
}
