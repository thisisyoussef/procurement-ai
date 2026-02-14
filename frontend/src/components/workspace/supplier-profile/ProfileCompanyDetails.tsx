'use client'

import { ExternalLink } from 'lucide-react'
import type { SupplierProfileCompanyDetails, SupplierProfileQuote } from '@/types/supplierProfile'

interface Props {
  company: SupplierProfileCompanyDetails
  quote: SupplierProfileQuote | null
}

export default function ProfileCompanyDetails({ company, quote }: Props) {
  const location = [company.city, company.country].filter(Boolean).join(', ')

  const leftCol = [
    { label: 'Location', value: location || null },
    { label: 'Languages', value: company.language },
    { label: 'Preferred contact', value: company.preferred_contact_method !== 'email' ? company.preferred_contact_method : null },
    { label: 'Payment terms', value: quote?.payment_terms || null },
  ].filter((r) => r.value)

  const rightCol = [
    { label: 'Shipping', value: quote?.shipping_terms || null },
    { label: 'Lead time', value: quote?.lead_time || null },
    {
      label: 'Email',
      value: company.email,
      link: company.email ? `mailto:${company.email}` : undefined,
    },
    { label: 'Phone', value: company.phone },
    {
      label: 'Website',
      value: company.website ? formatDomain(company.website) : null,
      link: company.website || undefined,
      external: true,
    },
  ].filter((r) => r.value)

  if (leftCol.length === 0 && rightCol.length === 0) {
    return (
      <div className="text-[13px] text-ink-4 py-4">No company details available yet.</div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-0">
      {/* Left column */}
      <div className="flex flex-col sm:pr-8 sm:border-r sm:border-black/[.06]">
        {leftCol.map((row) => (
          <InfoRow key={row.label} {...row} />
        ))}
      </div>

      {/* Right column */}
      <div className="flex flex-col sm:pl-8">
        {rightCol.map((row) => (
          <InfoRow key={row.label} {...row} />
        ))}
      </div>
    </div>
  )
}

function InfoRow({ label, value, link, external }: {
  label: string
  value: string | null
  link?: string
  external?: boolean
}) {
  if (!value) return null

  return (
    <div className="flex justify-between py-3 text-[13px] border-b border-black/[.06] last:border-b-0">
      <span className="text-ink-3">{label}</span>
      {link ? (
        <a
          href={link}
          target={external ? '_blank' : undefined}
          rel={external ? 'noopener noreferrer' : undefined}
          className="text-ink-2 font-medium text-right hover:text-teal transition-colors flex items-center gap-1"
        >
          {value}
          {external && <ExternalLink size={11} className="text-ink-4" />}
        </a>
      ) : (
        <span className="text-ink-2 font-medium text-right">{value}</span>
      )}
    </div>
  )
}

function formatDomain(url: string): string {
  try {
    const parsed = new URL(url.startsWith('http') ? url : `https://${url}`)
    return parsed.hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}
