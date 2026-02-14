'use client'

import type { SupplierProfileCompanyDetails } from '@/types/supplierProfile'

interface Props {
  company: SupplierProfileCompanyDetails
  description: string | null
}

export default function ProfileCapabilities({ company, description }: Props) {
  const cards: { title: string; content: string | null }[] = []

  if (company.categories.length > 0) {
    cards.push({ title: 'Product range', content: company.categories.join(', ') })
  }

  if (company.certifications.length > 0) {
    cards.push({ title: 'Certifications', content: company.certifications.join(', ') })
  }

  if (description) {
    // Truncate long descriptions to keep it card-sized
    const truncated = description.length > 200 ? description.slice(0, 200) + '...' : description
    cards.push({ title: 'About', content: truncated })
  }

  if (company.source && company.source !== 'unknown') {
    cards.push({ title: 'Source', content: formatSource(company.source) })
  }

  if (cards.length === 0) {
    return (
      <div className="text-[13px] text-ink-4 py-4">
        Capabilities not yet assessed for this supplier.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {cards.map((card) => (
        <div key={card.title} className="bg-surface border border-black/[.06] rounded-xl px-5 py-4">
          <div className="text-[12px] font-semibold mb-1.5">{card.title}</div>
          <div className="text-[12px] text-ink-3 leading-relaxed">{card.content}</div>
        </div>
      ))}
    </div>
  )
}

function formatSource(source: string): string {
  const map: Record<string, string> = {
    google_places: 'Discovered via Google Places',
    marketplace_alibaba: 'Found on Alibaba',
    marketplace_etsy: 'Found on Etsy',
    thomasnet: 'Listed on ThomasNet',
    importyeti: 'Found via ImportYeti',
    firecrawl: 'Discovered via web search',
  }
  return map[source] || source.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
